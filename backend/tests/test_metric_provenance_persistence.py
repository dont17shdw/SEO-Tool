"""Verify explicit current-metric sources in isolated PostgreSQL schemas using synthetic files.
使用合成文件及隔离的 PostgreSQL 模式验证当前指标的明确来源。
"""

import io
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from gsc_helpers import csv_file
from gsc_helpers import gsc_engine as postgres_import_engine  # noqa: F401
from openpyxl import Workbook
from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.imports.gsc.parser import parse_gsc_pages
from app.imports.gsc.persistence import GSC_FIELDS, persist_gsc_pages
from app.models import ImportRun, PageMetricProvenance, PagePerformanceSnapshot, WebsitePage

URL = "https://example.com/page"
SNAPSHOT_FIELDS = {
    "clicks_28d": "clicks",
    "impressions_28d": "impressions",
    "ctr": "ctr",
    "average_position": "average_position",
}


def links(session, page_id):
    return dict(
        session.execute(
            select(PageMetricProvenance.metric_name, PageMetricProvenance.snapshot_id).where(
                PageMetricProvenance.page_id == page_id
            )
        ).all()
    )


def snapshot_for_run(session, run_id):
    return session.scalars(
        select(PagePerformanceSnapshot).where(PagePerformanceSnapshot.import_run_id == run_id)
    ).one()


def apply(session, content, filename="pages.csv"):
    return persist_gsc_pages(session, parse_gsc_pages(content, filename))


def dated_file(clicks: int, period_start: date) -> bytes:
    workbook = Workbook()
    pages = workbook.active
    pages.title = "Pages"
    pages.append(["Page", "Clicks", "Impressions", "CTR", "Position"])
    pages.append([URL, clicks, 100, "10%", 5])
    chart = workbook.create_sheet("Chart")
    chart.append(["Date"])
    chart.append([period_start])
    chart.append([period_start + timedelta(days=27)])
    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()


def test_new_page_records_four_explicit_metric_sources(gsc_engine):
    with Session(gsc_engine) as session:
        result = apply(session, csv_file([URL, 10, 100, "10%", 5]))
        snapshot = snapshot_for_run(session, result.import_run_id)
        page = session.get(WebsitePage, snapshot.page_id)
        assert links(session, page.id) == dict.fromkeys(GSC_FIELDS, snapshot.id)
        for metric, source_field in SNAPSHOT_FIELDS.items():
            assert getattr(page, metric) == getattr(snapshot, source_field)


@pytest.mark.parametrize(
    ("values", "expected_metrics"),
    [
        ([0, "", "0%", ""], {"clicks_28d", "ctr"}),
        (["", 250, "", "4.5"], {"impressions_28d", "average_position"}),
        (["", "", "", ""], set()),
    ],
)
def test_partial_or_blank_new_pages_only_record_supplied_sources(
    gsc_engine, values, expected_metrics
):
    with Session(gsc_engine) as session:
        result = apply(session, csv_file([URL, *values]))
        snapshot = snapshot_for_run(session, result.import_run_id)
        assert links(session, snapshot.page_id) == dict.fromkeys(expected_metrics, snapshot.id)
        page = session.get(WebsitePage, snapshot.page_id)
        assert all(getattr(page, field) is None for field in set(GSC_FIELDS) - expected_metrics)


def test_nonblank_update_moves_just_its_metric_source_and_preserves_blank_sources(gsc_engine):
    with Session(gsc_engine) as session:
        first = apply(session, csv_file([URL, 10, 100, "10%", 5]))
        second = apply(session, csv_file([URL, 20, "", "", ""]))
        first_snapshot = snapshot_for_run(session, first.import_run_id)
        second_snapshot = snapshot_for_run(session, second.import_run_id)
        page = session.get(WebsitePage, second_snapshot.page_id)
        assert page.clicks_28d == 20
        assert page.impressions_28d == 100
        assert page.ctr == Decimal("0.1")
        assert page.average_position == Decimal("5")
        expected = dict.fromkeys(GSC_FIELDS, first_snapshot.id)
        expected["clicks_28d"] = second_snapshot.id
        assert links(session, page.id) == expected
        assert second_snapshot.impressions is None
        assert second_snapshot.ctr is None
        assert second_snapshot.average_position is None
        assert second.updated_count == 1


def test_same_values_refresh_all_sources_without_counting_a_current_page_update(gsc_engine):
    content = csv_file([URL, 10, 100, "10%", 5])
    with Session(gsc_engine) as session:
        first = apply(session, content)
        first_snapshot = snapshot_for_run(session, first.import_run_id)
        page = session.get(WebsitePage, first_snapshot.page_id)
        original_updated_at = page.updated_at
        session.commit()
        second = apply(session, b"\n" + content)
        second_snapshot = snapshot_for_run(session, second.import_run_id)
        session.refresh(page)
        assert second_snapshot.id != first_snapshot.id
        assert links(session, page.id) == dict.fromkeys(GSC_FIELDS, second_snapshot.id)
        assert (second.created_count, second.updated_count, second.skipped_count) == (0, 0, 1)
        assert page.updated_at == original_updated_at


def test_same_value_partial_refresh_moves_only_the_explicitly_observed_source(gsc_engine):
    with Session(gsc_engine) as session:
        first = apply(session, csv_file([URL, 10, 100, "10%", 5]))
        second = apply(session, csv_file([URL, "", "", "10%", ""]))
        first_snapshot = snapshot_for_run(session, first.import_run_id)
        second_snapshot = snapshot_for_run(session, second.import_run_id)
        expected = dict.fromkeys(GSC_FIELDS, first_snapshot.id)
        expected["ctr"] = second_snapshot.id
        assert links(session, first_snapshot.page_id) == expected
        assert (second.updated_count, second.skipped_count) == (0, 1)


def test_blank_upload_preserves_all_existing_sources(gsc_engine):
    with Session(gsc_engine) as session:
        first = apply(session, csv_file([URL, 10, 100, "10%", 5]))
        second = apply(session, csv_file([URL, "", "", "", ""]))
        first_snapshot = snapshot_for_run(session, first.import_run_id)
        second_snapshot = snapshot_for_run(session, second.import_run_id)
        assert links(session, first_snapshot.page_id) == dict.fromkeys(
            GSC_FIELDS, first_snapshot.id
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(PageMetricProvenance)
                .where(PageMetricProvenance.snapshot_id == second_snapshot.id)
            )
            == 0
        )
        assert second.skipped_count == 1


def test_blank_upload_keeps_legacy_value_sources_unknown(gsc_engine):
    with Session(gsc_engine) as session:
        session.add(WebsitePage(url=URL, clicks_28d=10, impressions_28d=100))
        session.commit()
        result = apply(session, csv_file([URL, "", "", "", ""]))
        snapshot = snapshot_for_run(session, result.import_run_id)
        page = session.get(WebsitePage, snapshot.page_id)
        assert page.clicks_28d == 10
        assert page.impressions_28d == 100
        assert links(session, page.id) == {}


def test_explicit_same_value_can_establish_one_legacy_source_without_inferring_others(gsc_engine):
    with Session(gsc_engine) as session:
        session.add(WebsitePage(url=URL, clicks_28d=10, impressions_28d=100))
        session.commit()
        result = apply(session, csv_file([URL, 10, "", "", ""]))
        snapshot = snapshot_for_run(session, result.import_run_id)
        assert links(session, snapshot.page_id) == {"clicks_28d": snapshot.id}
        assert result.skipped_count == 1


def test_zero_updates_values_and_their_provenance(gsc_engine):
    with Session(gsc_engine) as session:
        apply(session, csv_file([URL, 10, 100, "10%", 5]))
        result = apply(session, csv_file([URL, 0, 0, "0%", 0]))
        snapshot = snapshot_for_run(session, result.import_run_id)
        page = session.get(WebsitePage, snapshot.page_id)
        assert all(getattr(page, field) == 0 for field in GSC_FIELDS)
        assert links(session, page.id) == dict.fromkeys(GSC_FIELDS, snapshot.id)


def test_identical_old_file_retry_preserves_newer_current_values_and_sources(gsc_engine):
    old_content = csv_file([URL, 10, 100, "10%", 5])
    with Session(gsc_engine) as session:
        first = apply(session, old_content)
        second = apply(session, csv_file([URL, 20, 200, "20%", 4]))
        duplicate = apply(session, old_content, "renamed.csv")
        snapshot = snapshot_for_run(session, second.import_run_id)
        page = session.get(WebsitePage, snapshot.page_id)
        assert duplicate.already_processed
        assert duplicate.import_run_id == first.import_run_id
        assert page.clicks_28d == 20
        assert links(session, page.id) == dict.fromkeys(GSC_FIELDS, snapshot.id)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 2
        assert session.scalar(select(func.count()).select_from(PagePerformanceSnapshot)) == 2
        assert session.scalar(select(func.count()).select_from(PageMetricProvenance)) == 4


def test_out_of_order_report_updates_sources_by_apply_order(gsc_engine):
    with Session(gsc_engine) as session:
        newer = apply(session, dated_file(20, date(2026, 2, 1)), "newer.xlsx")
        older = apply(session, dated_file(10, date(2026, 1, 1)), "older.xlsx")
        newer_snapshot = snapshot_for_run(session, newer.import_run_id)
        older_snapshot = snapshot_for_run(session, older.import_run_id)
        assert older_snapshot.period_end < newer_snapshot.period_end
        assert session.get(WebsitePage, older_snapshot.page_id).clicks_28d == 10
        assert links(session, older_snapshot.page_id) == dict.fromkeys(
            GSC_FIELDS, older_snapshot.id
        )


def test_provenance_failure_after_successful_link_writes_rolls_back_every_import_target(
    gsc_engine, monkeypatch
):
    baseline_content = csv_file([URL, 10, 100, "10%", 5])
    changed_content = csv_file(
        [URL, 20, 200, "20%", 4], ["https://example.com/new", 5, 50, "10%", 8]
    )
    with Session(gsc_engine) as session:
        first = apply(session, baseline_content)
        first_snapshot = snapshot_for_run(session, first.import_run_id)
        original_page_id = first_snapshot.page_id
        original_sources = links(session, first_snapshot.page_id)
        session.commit()
        original_execute = session.execute
        provenance_writes = 0

        def fail_after_link_writes(statement, *args, **kwargs):
            nonlocal provenance_writes
            result = original_execute(statement, *args, **kwargs)
            if (
                getattr(statement, "is_insert", False)
                and statement.table.name == "page_metric_provenance"
            ):
                provenance_writes += 1
                if provenance_writes == 2:
                    raise SQLAlchemyError("Synthetic failure after provenance writes")
            return result

        monkeypatch.setattr("app.imports.gsc.persistence.PROVENANCE_BATCH_SIZE", 1)
        monkeypatch.setattr(session, "execute", fail_after_link_writes)
        with pytest.raises(SQLAlchemyError):
            apply(session, changed_content)
        assert provenance_writes == 2
        assert not session.in_transaction()

    with Session(gsc_engine) as verification:
        assert verification.scalar(select(func.count()).select_from(ImportRun)) == 1
        assert verification.scalar(select(func.count()).select_from(PagePerformanceSnapshot)) == 1
        assert verification.scalar(select(func.count()).select_from(WebsitePage)) == 1
        assert verification.scalar(select(func.count()).select_from(PageMetricProvenance)) == 4
        page = verification.get(WebsitePage, original_page_id)
        assert (page.clicks_28d, page.impressions_28d, page.ctr, page.average_position) == (
            10,
            100,
            Decimal("0.1"),
            Decimal("5"),
        )
        assert links(verification, page.id) == original_sources
        verification.commit()
        retry = apply(verification, changed_content)
        assert not retry.already_processed
        assert (retry.created_count, retry.updated_count) == (1, 1)


def test_concurrent_distinct_files_keep_current_values_and_sources_consistent(gsc_engine):
    files = [
        parse_gsc_pages(csv_file([URL, 10, 100, "10%", 5]), "first.csv"),
        parse_gsc_pages(csv_file([URL, 20, 200, "20%", 4]), "second.csv"),
    ]
    barrier = Barrier(2, timeout=10)

    def import_once(parsed):
        with Session(gsc_engine) as session:
            barrier.wait()
            return persist_gsc_pages(session, parsed)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(import_once, files, timeout=20))
    assert sum(result.created_count for result in results) == 1
    assert sum(result.updated_count for result in results) == 1
    with Session(gsc_engine) as session:
        page = session.scalars(select(WebsitePage)).one()
        sources = links(session, page.id)
        assert len(sources) == 4
        assert len(set(sources.values())) == 1
        snapshot = session.get(PagePerformanceSnapshot, sources["clicks_28d"])
        assert snapshot.page_id == page.id
        for metric, source_field in SNAPSHOT_FIELDS.items():
            assert getattr(page, metric) == getattr(snapshot, source_field)


def test_many_pages_keep_provenance_associated_with_their_own_source_rows(gsc_engine):
    rows = [[f"https://example.com/page-{number}", number, 1000, "10%", 5] for number in range(251)]
    with Session(gsc_engine) as session:
        result = apply(session, csv_file(*rows))
        assert result.created_count == 251
        assert session.scalar(select(func.count()).select_from(PageMetricProvenance)) == 1004
        joined = session.execute(
            select(PageMetricProvenance, PagePerformanceSnapshot, WebsitePage)
            .join(
                PagePerformanceSnapshot,
                PagePerformanceSnapshot.id == PageMetricProvenance.snapshot_id,
            )
            .join(WebsitePage, WebsitePage.id == PageMetricProvenance.page_id)
        ).all()
        assert all(link.page_id == snapshot.page_id == page.id for link, snapshot, page in joined)
        assert all(
            getattr(page, link.metric_name) == getattr(snapshot, SNAPSHOT_FIELDS[link.metric_name])
            for link, snapshot, page in joined
        )


@pytest.mark.parametrize("metric", ["clicks", "clicks_7d", "backlinks", "", "CTR"])
def test_database_rejects_unsupported_metric_names(gsc_engine, metric):
    with Session(gsc_engine) as session:
        result = apply(session, csv_file([URL, 10, 100, "10%", 5]))
        snapshot = snapshot_for_run(session, result.import_run_id)
        with pytest.raises(IntegrityError) as error:
            session.execute(
                insert(PageMetricProvenance).values(
                    page_id=snapshot.page_id, metric_name=metric, snapshot_id=snapshot.id
                )
            )
        assert error.value.orig.sqlstate == "23514"


@pytest.mark.parametrize("invalid_field", ["page_id", "snapshot_id"])
def test_database_rejects_missing_provenance_references(gsc_engine, invalid_field):
    with Session(gsc_engine) as session:
        result = apply(session, csv_file([URL, "", "", "", ""]))
        snapshot = snapshot_for_run(session, result.import_run_id)
        fields = dict(page_id=snapshot.page_id, metric_name="clicks_28d", snapshot_id=snapshot.id)
        fields[invalid_field] = uuid4()
        with pytest.raises(IntegrityError) as error:
            session.execute(insert(PageMetricProvenance).values(**fields))
        assert error.value.orig.sqlstate == "23503"


def test_database_allows_only_one_current_link_per_page_metric(gsc_engine):
    with Session(gsc_engine) as session:
        result = apply(session, csv_file([URL, 10, 100, "10%", 5]))
        snapshot = snapshot_for_run(session, result.import_run_id)
        with pytest.raises(IntegrityError) as error:
            session.execute(
                insert(PageMetricProvenance).values(
                    page_id=snapshot.page_id, metric_name="clicks_28d", snapshot_id=snapshot.id
                )
            )
        assert error.value.orig.sqlstate == "23505"


def test_database_restricts_deleting_a_snapshot_that_supplies_current_metrics(gsc_engine):
    with Session(gsc_engine) as session:
        result = apply(session, csv_file([URL, 10, 100, "10%", 5]))
        snapshot = snapshot_for_run(session, result.import_run_id)
        session.delete(snapshot)
        with pytest.raises(IntegrityError) as error:
            session.flush()
        assert error.value.orig.sqlstate == "23503"
