"""Verify scoped import ownership and atomicity in isolated PostgreSQL schemas.
在隔离的 PostgreSQL 模式中验证带范围导入的归属与原子性。
"""

import io
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, timedelta
from threading import Barrier

import pytest
from gsc_helpers import csv_file
from gsc_helpers import gsc_engine as postgres_import_engine  # noqa: F401
from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.imports.gsc.parser import parse_gsc_pages
from app.imports.gsc.persistence import GSC_FIELDS, persist_gsc_pages
from app.models import (
    ImportRun,
    PageMetricProvenance,
    PagePerformanceSnapshot,
    SEOOpportunity,
    Site,
    WebsitePage,
)
from app.normalization.report_scope import UNKNOWN_SCOPE_FINGERPRINT, ScopeDeclaration

URL = "https://example.com/page"
CONTENT = csv_file([URL, 10, 100, "10%", 5])


def declared_scope(property_id="sc-domain:example.com", filters=None):
    return ScopeDeclaration(
        property_id=property_id, search_type="web", filters=[] if filters is None else filters
    )


def parsed(content=CONTENT, scope=None, filename="pages.csv"):
    return parse_gsc_pages(content, filename, scope=scope)


def sources(session, page_id):
    return dict(
        session.execute(
            select(PageMetricProvenance.metric_name, PageMetricProvenance.snapshot_id).where(
                PageMetricProvenance.page_id == page_id
            )
        ).all()
    )


def snapshot(session, run_id):
    return session.scalars(
        select(PagePerformanceSnapshot).where(PagePerformanceSnapshot.import_run_id == run_id)
    ).one()


def count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def test_equivalent_canonical_scope_deduplicates_same_file_and_keeps_original_evidence(gsc_engine):
    first = parsed(
        scope=ScopeDeclaration(
            property_id=" sc-domain:EXAMPLE.COM ",
            search_type=" Web ",
            filters=[
                {"dimension": "device", "operator": "equals", "value": " Mobile "},
                {"dimension": "country", "operator": "equals", "value": " usa "},
            ],
        ),
        filename="original.csv",
    )
    second = parsed(
        scope=declared_scope(
            filters=[
                {"dimension": "country", "operator": "equals", "value": "USA"},
                {"dimension": "device", "operator": "equals", "value": "mobile"},
            ]
        ),
        filename="renamed.csv",
    )
    assert first.preview.file_hash == second.preview.file_hash
    assert first.preview.report_scope.fingerprint == second.preview.report_scope.fingerprint
    with Session(gsc_engine) as session:
        original = persist_gsc_pages(session, first)
        duplicate = persist_gsc_pages(session, second)
        assert duplicate.already_processed
        assert duplicate.import_run_id == original.import_run_id
        assert count(session, Site) == count(session, ImportRun) == count(session, WebsitePage) == 1
        assert count(session, PagePerformanceSnapshot) == 1
        assert count(session, PageMetricProvenance) == 4
        run = session.get(ImportRun, original.import_run_id)
        assert run.filename == "original.csv"
        assert run.report_scope == first.preview.report_scope.model_dump(mode="json")
        assert run.file_hash == first.preview.file_hash
        assert run.scope_fingerprint == first.preview.report_scope.fingerprint


def test_evidence_origin_is_retained_but_does_not_change_canonical_duplicate_identity(gsc_engine):
    first = parsed(scope=declared_scope())
    observed = first.preview.report_scope.model_copy(
        update={
            "workbook_observed": first.preview.report_scope.user_declared,
            "user_declared": ScopeDeclaration(),
            "issues": ["synthetic_source_evidence"],
        }
    )
    second = replace(first, preview=first.preview.model_copy(update={"report_scope": observed}))
    assert observed.fingerprint == first.preview.report_scope.fingerprint
    with Session(gsc_engine) as session:
        original = persist_gsc_pages(session, first)
        duplicate = persist_gsc_pages(session, second)
        assert duplicate.already_processed and duplicate.import_run_id == original.import_run_id
        run = session.get(ImportRun, original.import_run_id)
        assert run.report_scope["user_declared"]["property_id"] == "sc-domain:example.com"
        assert run.report_scope["workbook_observed"]["property_id"] is None
        assert run.report_scope["issues"] == []


def test_same_bytes_different_filters_create_runs_refresh_sources_and_retry_preserves_latest(
    gsc_engine,
):
    mobile = parsed(
        scope=declared_scope(
            filters=[{"dimension": "device", "operator": "equals", "value": "mobile"}]
        )
    )
    desktop = parsed(
        scope=declared_scope(
            filters=[{"dimension": "device", "operator": "equals", "value": "desktop"}]
        )
    )
    with Session(gsc_engine) as session:
        first = persist_gsc_pages(session, mobile)
        second = persist_gsc_pages(session, desktop)
        assert first.import_run_id != second.import_run_id
        assert not second.already_processed
        assert (second.created_count, second.updated_count, second.skipped_count) == (0, 0, 1)
        latest = snapshot(session, second.import_run_id)
        page_id = latest.page_id
        assert sources(session, page_id) == dict.fromkeys(GSC_FIELDS, latest.id)
        assert count(session, Site) == count(session, WebsitePage) == 1
        assert count(session, ImportRun) == count(session, PagePerformanceSnapshot) == 2
        assert count(session, SEOOpportunity) == 0
        session.commit()
        duplicate = persist_gsc_pages(session, mobile)
        assert duplicate.already_processed and duplicate.import_run_id == first.import_run_id
        assert sources(session, page_id) == dict.fromkeys(GSC_FIELDS, latest.id)
        assert session.get(WebsitePage, page_id).clicks_28d == 10


def test_same_bytes_different_properties_keep_same_url_in_separate_site_namespaces(gsc_engine):
    with Session(gsc_engine) as session:
        first = persist_gsc_pages(session, parsed(scope=declared_scope()))
        second = persist_gsc_pages(
            session, parsed(scope=declared_scope(property_id="sc-domain:another.example"))
        )
        assert not second.already_processed and second.created_count == 1
        first_snapshot = snapshot(session, first.import_run_id)
        second_snapshot = snapshot(session, second.import_run_id)
        assert first_snapshot.page_id != second_snapshot.page_id
        first_run = session.get(ImportRun, first.import_run_id)
        second_run = session.get(ImportRun, second.import_run_id)
        assert first_run.site_id != second_run.site_id
        for run, observation in ((first_run, first_snapshot), (second_run, second_snapshot)):
            page = session.get(WebsitePage, observation.page_id)
            assert page.url == URL and page.site_id == run.site_id
            assert sources(session, page.id) == dict.fromkeys(GSC_FIELDS, observation.id)
        assert count(session, Site) == count(session, WebsitePage) == count(session, ImportRun) == 2


def test_unknown_ownership_is_never_claimed_by_a_later_explicit_property(gsc_engine):
    with Session(gsc_engine) as session:
        unknown = persist_gsc_pages(session, parsed())
        unknown_snapshot = snapshot(session, unknown.import_run_id)
        legacy_page_id = unknown_snapshot.page_id
        legacy_sources = sources(session, legacy_page_id)
        session.commit()
        known = persist_gsc_pages(session, parsed(scope=declared_scope()))
        known_snapshot = snapshot(session, known.import_run_id)
        assert known.created_count == 1 and not known.already_processed
        assert known_snapshot.page_id != legacy_page_id
        legacy = session.get(WebsitePage, legacy_page_id)
        assert legacy.site_id is None and legacy.clicks_28d == 10
        assert sources(session, legacy_page_id) == legacy_sources
        assert session.get(ImportRun, unknown.import_run_id).site_id is None
        assert count(session, Site) == 1
        assert count(session, WebsitePage) == 2


def test_absent_property_scope_stays_unknown_despite_url_filename_and_prior_import(gsc_engine):
    with Session(gsc_engine) as session:
        persist_gsc_pages(session, parsed(scope=declared_scope()))
        unknown = persist_gsc_pages(session, parsed(filename="sc-domain-example.com.csv"))
        run = session.get(ImportRun, unknown.import_run_id)
        page = session.get(WebsitePage, snapshot(session, unknown.import_run_id).page_id)
        assert run.site_id is None and page.site_id is None
        assert run.scope_fingerprint == UNKNOWN_SCOPE_FINGERPRINT
        assert run.report_scope["property_id"] is None
        assert run.report_scope["status"] == "unknown"
        assert run.observed_date_count is None and run.dates_consecutive is None
        assert run.coverage_status == "unknown"
        assert count(session, Site) == 1


def test_legacy_null_scope_duplicate_stays_unknown_and_explicit_scope_creates_separate_history(
    gsc_engine,
):
    unknown_report = parsed()
    with Session(gsc_engine) as session:
        legacy_page = WebsitePage(url=URL, clicks_28d=77)
        legacy_run = ImportRun(
            file_hash=unknown_report.preview.file_hash,
            filename="legacy.csv",
            total_rows=1,
            created_count=1,
        )
        session.add_all([legacy_page, legacy_run])
        session.commit()
        legacy_page_id, legacy_run_id = legacy_page.id, legacy_run.id
        session.commit()
        duplicate = persist_gsc_pages(session, unknown_report)
        assert duplicate.already_processed and duplicate.import_run_id == legacy_run_id
        assert session.get(ImportRun, legacy_run_id).report_scope is None
        assert session.get(WebsitePage, legacy_page_id).clicks_28d == 77
        assert sources(session, legacy_page_id) == {}
        assert count(session, Site) == count(session, PagePerformanceSnapshot) == 0
        session.commit()
        known = persist_gsc_pages(session, parsed(scope=declared_scope()))
        assert not known.already_processed and known.created_count == 1
        assert known.import_run_id != legacy_run_id
        assert session.get(ImportRun, legacy_run_id).report_scope is None
        assert session.get(WebsitePage, legacy_page_id).site_id is None
        assert session.get(WebsitePage, legacy_page_id).clicks_28d == 77
        assert count(session, WebsitePage) == count(session, ImportRun) == 2


def workbook(dates):
    """Produce daily evidence explicitly; endpoints do not stand in for missing dates.
    明确生成每日证据；端点不能代替缺失日期。
    """
    book = Workbook()
    pages = book.active
    pages.title = "Pages"
    pages.append(["Page", "Clicks", "Impressions", "CTR", "Position"])
    pages.append([URL, 10, 100, "10%", 5])
    chart = book.create_sheet("Chart")
    chart.append(["Date"])
    for day in dates:
        chart.append([day])
    buffer = io.BytesIO()
    book.save(buffer)
    book.close()
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("offsets", "expected_count", "expected_consecutive", "status"),
    [
        (list(range(28)), 28, True, "complete"),
        ([0, 9, 27], 3, False, "partial"),
        ([0, 0, 1, 1, 27], 3, False, "partial"),
    ],
)
def test_import_run_stores_observed_coverage_without_duplicating_it_into_snapshots(
    gsc_engine, offsets, expected_count, expected_consecutive, status
):
    dates = [date(2026, 9, 1) + timedelta(days=offset) for offset in offsets]
    report = parsed(workbook(dates), declared_scope(), filename="coverage.xlsx")
    with Session(gsc_engine) as session:
        result = persist_gsc_pages(session, report)
        run = session.get(ImportRun, result.import_run_id)
        assert (run.period_start, run.period_end) == (date(2026, 9, 1), date(2026, 9, 28))
        assert run.observed_date_count == expected_count
        assert run.dates_consecutive is expected_consecutive
        assert run.coverage_status == status
        assert run.report_scope == report.preview.report_scope.model_dump(mode="json")
        observed = snapshot(session, result.import_run_id)
        assert observed.period_start == run.period_start and observed.period_end == run.period_end
        assert not hasattr(observed, "report_scope")
        assert not hasattr(observed, "observed_date_count")


@pytest.mark.parametrize("different_filters", [False, True])
def test_concurrent_same_property_imports_reserve_one_site_and_correct_scoped_runs(
    gsc_engine, different_filters
):
    filters = [{"dimension": "device", "operator": "equals", "value": "mobile"}]
    reports = [parsed(scope=declared_scope(filters=filters))]
    second_filters = (
        [{"dimension": "device", "operator": "equals", "value": "desktop"}]
        if different_filters
        else filters
    )
    reports.append(parsed(scope=declared_scope(filters=second_filters)))
    barrier = Barrier(2, timeout=10)

    def apply(report):
        with Session(gsc_engine) as session:
            barrier.wait()
            return persist_gsc_pages(session, report)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(apply, reports, timeout=20))
    assert sum(result.created_count for result in results) == 1
    assert sum(result.already_processed for result in results) == (0 if different_filters else 1)
    with Session(gsc_engine) as session:
        assert count(session, Site) == count(session, WebsitePage) == 1
        expected_runs = 2 if different_filters else 1
        assert count(session, ImportRun) == count(session, PagePerformanceSnapshot) == expected_runs
        page = session.scalars(select(WebsitePage)).one()
        links = sources(session, page.id)
        assert len(links) == 4 and len(set(links.values())) == 1
        current = session.get(PagePerformanceSnapshot, links["clicks_28d"])
        assert current.page_id == page.id and page.clicks_28d == current.clicks == 10


def test_failure_after_actual_source_writes_rolls_back_new_site_and_all_import_targets(
    gsc_engine, monkeypatch
):
    report = parsed(scope=declared_scope())
    with Session(gsc_engine) as session:
        execute = session.execute
        writes = 0

        def fail_after_links(statement, *args, **kwargs):
            nonlocal writes
            result = execute(statement, *args, **kwargs)
            if (
                getattr(statement, "is_insert", False)
                and statement.table.name == "page_metric_provenance"
            ):
                writes += 1
                if writes == 2:
                    raise SQLAlchemyError(
                        "Synthetic failure after actual site and provenance writes"
                    )
            return result

        monkeypatch.setattr("app.imports.gsc.persistence.PROVENANCE_BATCH_SIZE", 1)
        monkeypatch.setattr(session, "execute", fail_after_links)
        with pytest.raises(SQLAlchemyError):
            persist_gsc_pages(session, report)
        assert writes == 2 and not session.in_transaction()

    with Session(gsc_engine) as verification:
        for model in (
            Site,
            ImportRun,
            WebsitePage,
            PagePerformanceSnapshot,
            PageMetricProvenance,
            SEOOpportunity,
        ):
            assert count(verification, model) == 0
        verification.commit()
        retry = persist_gsc_pages(verification, report)
        assert retry.created_count == 1 and not retry.already_processed
        assert count(verification, Site) == count(verification, ImportRun) == 1
        assert count(verification, PageMetricProvenance) == 4


def test_scoped_blanks_zero_and_out_of_order_apply_preserve_phase5_source_meaning(gsc_engine):
    scope = declared_scope()
    newer_dates = [date(2026, 9, 1) + timedelta(days=day) for day in range(28)]
    older_dates = [date(2026, 8, 1) + timedelta(days=day) for day in range(28)]
    newer_content = workbook(newer_dates)
    with Session(gsc_engine) as session:
        newer = persist_gsc_pages(session, parsed(newer_content, scope, "newer.xlsx"))
        older = persist_gsc_pages(session, parsed(workbook(older_dates), scope, "older.xlsx"))
        older_snapshot = snapshot(session, older.import_run_id)
        page_id = older_snapshot.page_id
        assert older.skipped_count == 1
        assert sources(session, page_id) == dict.fromkeys(GSC_FIELDS, older_snapshot.id)
        session.commit()
        blank = persist_gsc_pages(session, parsed(csv_file([URL, "", "", "", ""]), scope))
        assert blank.skipped_count == 1
        assert sources(session, page_id) == dict.fromkeys(GSC_FIELDS, older_snapshot.id)
        session.commit()
        zero = persist_gsc_pages(session, parsed(csv_file([URL, 0, "", "", ""]), scope))
        zero_snapshot = snapshot(session, zero.import_run_id)
        expected = dict.fromkeys(GSC_FIELDS, older_snapshot.id)
        expected["clicks_28d"] = zero_snapshot.id
        assert sources(session, page_id) == expected
        assert session.get(WebsitePage, page_id).clicks_28d == 0
        session.commit()
        retry = persist_gsc_pages(session, parsed(newer_content, scope, "renamed.xlsx"))
        assert retry.already_processed and retry.import_run_id == newer.import_run_id
        assert sources(session, page_id) == expected
        assert session.get(WebsitePage, page_id).clicks_28d == 0
