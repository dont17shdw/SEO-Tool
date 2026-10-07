"""Verify atomic GSC history using synthetic data in isolated PostgreSQL schemas.
使用合成数据及隔离的 PostgreSQL 模式验证 GSC 历史的原子持久化。
"""

import io
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from threading import Barrier
from uuid import UUID

import pytest
from gsc_helpers import csv_file
from gsc_helpers import gsc_engine as postgres_import_engine  # noqa: F401
from openpyxl import Workbook
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.imports.gsc.parser import parse_gsc_pages
from app.imports.gsc.persistence import persist_gsc_pages
from app.models import ImportRun, PagePerformanceSnapshot, WebsitePage


def test_invalid_import_is_rejected_before_opening_a_transaction():
    parsed = parse_gsc_pages(
        csv_file(["https://example.com/page", -1, 100, "10%", 5]), "invalid.csv"
    )
    with Session() as session:
        with pytest.raises(ValueError, match="complete, validated import"):
            persist_gsc_pages(session, parsed)
        assert not session.in_transaction()


def test_a_partial_copy_of_validated_rows_cannot_be_persisted():
    parsed = parse_gsc_pages(csv_file(["https://example.com/page", 1, 100, "1%", 5]), "pages.csv")
    with Session() as session:
        with pytest.raises(ValueError, match="complete, validated import"):
            persist_gsc_pages(session, replace(parsed, rows=[]))
        assert not session.in_transaction()


def dated_workbook(clicks: int, period_start: date) -> bytes:
    """Generate page metrics and actual daily date evidence without private exports.
    生成页面指标及实际每日日期证据，不使用私人导出文件。
    """
    workbook = Workbook()
    pages = workbook.active
    pages.title = "Pages"
    pages.append(["Page", "Clicks", "Impressions", "CTR", "Position"])
    pages.append(["https://example.com/history", clicks, 100, "10%", 5])
    chart = workbook.create_sheet("Chart")
    chart.append(["Date", "Clicks", "Impressions", "CTR", "Position"])
    for day in range(28):
        chart.append([period_start + timedelta(days=day), 1, 10, "10%", 5])
    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()


def test_import_run_and_snapshots_preserve_unknown_periods_and_complete_counts(gsc_engine):
    parsed = parse_gsc_pages(
        csv_file(
            ["https://example.com/known", 0, 100, "2.5%", "6.75"],
            ["https://example.com/unknown", "", "", "", ""],
        ),
        "pages.csv",
    )
    with Session(gsc_engine) as session:
        result = persist_gsc_pages(session, parsed)
        assert isinstance(result.import_run_id, UUID)
        assert not result.already_processed
        assert (result.created_count, result.updated_count, result.skipped_count) == (2, 0, 0)
        run = session.get(ImportRun, result.import_run_id)
        assert (run.source, run.source_type, run.reporting_window) == (
            "gsc",
            "pages_performance",
            "latest_28_days",
        )
        assert run.file_hash == parsed.preview.file_hash
        assert run.filename == "pages.csv"
        assert run.status == "completed"
        assert run.total_rows == run.created_count + run.updated_count + run.skipped_count == 2
        assert run.imported_at.utcoffset() == timedelta(0)
        assert run.period_start is None and run.period_end is None
        snapshots = session.scalars(
            select(PagePerformanceSnapshot).order_by(PagePerformanceSnapshot.url)
        ).all()
        assert len(snapshots) == 2
        assert snapshots[0].clicks == 0
        assert snapshots[0].ctr == Decimal("0.025000")
        assert snapshots[1].clicks is None
        assert snapshots[1].impressions is None
        assert snapshots[1].ctr is None
        assert snapshots[1].average_position is None
        assert all(snapshot.import_run_id == run.id for snapshot in snapshots)
        assert all(
            snapshot.period_start is None and snapshot.period_end is None for snapshot in snapshots
        )


def test_source_blanks_stay_null_in_history_while_current_values_are_retained(gsc_engine):
    first = parse_gsc_pages(csv_file(["https://example.com/page", 10, 200, "5%", 8]), "first.csv")
    blanks = parse_gsc_pages(csv_file(["https://example.com/page", 0, "", "", ""]), "second.csv")
    with Session(gsc_engine) as session:
        persist_gsc_pages(session, first)
        result = persist_gsc_pages(session, blanks)
        assert (result.created_count, result.updated_count, result.skipped_count) == (0, 1, 0)
        page = session.scalars(select(WebsitePage)).one()
        snapshot = session.scalars(
            select(PagePerformanceSnapshot).where(
                PagePerformanceSnapshot.import_run_id == result.import_run_id
            )
        ).one()
        assert page.clicks_28d == snapshot.clicks == 0
        assert page.impressions_28d == 200
        assert page.ctr == Decimal("0.05")
        assert page.average_position == Decimal("8")
        assert snapshot.impressions is None
        assert snapshot.ctr is None
        assert snapshot.average_position is None


def test_identical_bytes_with_a_different_filename_do_not_create_more_history(gsc_engine):
    content = csv_file(["https://example.com/page", 10, 100, "10%", 5])
    with Session(gsc_engine) as session:
        first = persist_gsc_pages(session, parse_gsc_pages(content, "original.csv"))
        duplicate = persist_gsc_pages(session, parse_gsc_pages(content, "renamed.csv"))
        assert duplicate.import_run_id == first.import_run_id
        assert duplicate.already_processed
        assert (
            duplicate.created_count,
            duplicate.updated_count,
            duplicate.skipped_count,
            duplicate.error_count,
        ) == (0, 0, 1, 0)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 1
        assert session.scalar(select(func.count()).select_from(PagePerformanceSnapshot)) == 1
        assert session.get(ImportRun, first.import_run_id).filename == "original.csv"


def test_same_filename_with_new_bytes_creates_a_new_run_and_unchanged_snapshot(gsc_engine):
    content = csv_file(["https://example.com/page", 10, 100, "10%", 5])
    with Session(gsc_engine) as session:
        first = persist_gsc_pages(session, parse_gsc_pages(content, "pages.csv"))
        # A blank source line changes the fingerprint while preserving normalized metrics.
        # 来源空行改变指纹，但保留相同的标准化指标。
        second = persist_gsc_pages(session, parse_gsc_pages(b"\n" + content, "pages.csv"))
        assert second.import_run_id != first.import_run_id
        assert not second.already_processed
        assert (second.created_count, second.updated_count, second.skipped_count) == (0, 0, 1)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 2
        assert session.scalar(select(func.count()).select_from(PagePerformanceSnapshot)) == 2


def test_old_identical_file_after_a_newer_import_does_not_restore_old_current_metrics(gsc_engine):
    old_file = parse_gsc_pages(
        csv_file(["https://example.com/page", 10, 100, "10%", 8]), "pages.csv"
    )
    newer_file = parse_gsc_pages(
        csv_file(["https://example.com/page", 20, 200, "10%", 5]), "pages.csv"
    )
    with Session(gsc_engine) as session:
        original = persist_gsc_pages(session, old_file)
        persist_gsc_pages(session, newer_file)
        duplicate = persist_gsc_pages(session, old_file)
        assert duplicate.already_processed
        assert duplicate.import_run_id == original.import_run_id
        page = session.scalars(select(WebsitePage)).one()
        assert (page.clicks_28d, page.impressions_28d, page.average_position) == (
            20,
            200,
            Decimal("5"),
        )
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 2
        assert session.scalar(select(func.count()).select_from(PagePerformanceSnapshot)) == 2


def test_exact_periods_are_preserved_for_multiple_chronological_snapshots(gsc_engine):
    with Session(gsc_engine) as session:
        first = persist_gsc_pages(
            session, parse_gsc_pages(dated_workbook(10, date(2026, 1, 1)), "first.xlsx")
        )
        second = persist_gsc_pages(
            session, parse_gsc_pages(dated_workbook(20, date(2026, 2, 1)), "second.xlsx")
        )
        snapshots = session.scalars(
            select(PagePerformanceSnapshot).order_by(PagePerformanceSnapshot.period_end)
        ).all()
        assert [snapshot.import_run_id for snapshot in snapshots] == [
            first.import_run_id,
            second.import_run_id,
        ]
        assert [snapshot.clicks for snapshot in snapshots] == [10, 20]
        assert [snapshot.period_start for snapshot in snapshots] == [
            date(2026, 1, 1),
            date(2026, 2, 1),
        ]
        assert [snapshot.period_end for snapshot in snapshots] == [
            date(2026, 1, 28),
            date(2026, 2, 28),
        ]
        assert all(
            snapshot.import_run.period_start == snapshot.period_start for snapshot in snapshots
        )
        assert all(snapshot.import_run.period_end == snapshot.period_end for snapshot in snapshots)
        assert session.scalars(select(WebsitePage)).one().clicks_28d == 20


def test_snapshot_failure_rolls_back_every_write_and_allows_clean_retry(gsc_engine):
    parsed = parse_gsc_pages(
        csv_file(
            ["https://example.com/existing", 20, 200, "10%", 5],
            ["https://example.com/new", 30, 300, "10%", 4],
        ),
        "pages.csv",
    )
    with Session(gsc_engine) as session:
        session.add(WebsitePage(url="https://example.com/existing", clicks_28d=10))
        session.commit()

        def fail_snapshot(mapper, connection, target):
            raise SQLAlchemyError("Synthetic snapshot insertion failure")

        event.listen(PagePerformanceSnapshot, "before_insert", fail_snapshot)
        try:
            with pytest.raises(SQLAlchemyError):
                persist_gsc_pages(session, parsed)
        finally:
            event.remove(PagePerformanceSnapshot, "before_insert", fail_snapshot)

        assert not session.in_transaction()
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0
        assert session.scalar(select(func.count()).select_from(PagePerformanceSnapshot)) == 0
        pages = session.scalars(select(WebsitePage)).all()
        assert len(pages) == 1
        assert pages[0].clicks_28d == 10
        session.commit()
        result = persist_gsc_pages(session, parsed)
        assert not result.already_processed
        assert (result.created_count, result.updated_count) == (1, 1)


def test_concurrent_identical_hashes_create_one_successful_run(gsc_engine):
    parsed = parse_gsc_pages(
        csv_file(
            ["https://example.com/first", 10, 100, "10%", 5],
            ["https://example.com/second", 20, 200, "10%", 4],
        ),
        "pages.csv",
    )
    barrier = Barrier(2, timeout=10)

    def apply_once(_):
        with Session(gsc_engine) as session:
            barrier.wait()
            return persist_gsc_pages(session, parsed)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(apply_once, range(2), timeout=20))
    assert len({result.import_run_id for result in results}) == 1
    assert sum(result.already_processed for result in results) == 1
    assert sum(result.created_count for result in results) == 2
    assert sum(result.skipped_count for result in results) == 2
    with Session(gsc_engine) as session:
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 1
        assert session.scalar(select(func.count()).select_from(PagePerformanceSnapshot)) == 2
        assert session.scalar(select(func.count()).select_from(WebsitePage)) == 2


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"file_hash": "invalid"},
        {"total_rows": -1},
        {"created_count": 2},
        {"period_start": date(2026, 2, 1)},
        {"period_start": date(2026, 2, 1), "period_end": date(2026, 1, 1)},
    ],
)
def test_import_run_constraints_reject_inconsistent_history(gsc_engine, invalid_fields):
    fields = dict(file_hash="a" * 64, filename="synthetic.csv", total_rows=1, created_count=1)
    fields.update(invalid_fields)
    with Session(gsc_engine) as session:
        session.add(ImportRun(**fields))
        with pytest.raises(IntegrityError) as error:
            session.flush()
        assert error.value.orig.sqlstate == "23514"


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"clicks": -1},
        {"impressions": -1},
        {"ctr": Decimal("1.000001")},
        {"average_position": Decimal("-0.0001")},
        {"period_end": date(2026, 1, 1)},
    ],
)
def test_snapshot_constraints_reject_invalid_observations(gsc_engine, invalid_fields):
    parsed = parse_gsc_pages(csv_file(["https://example.com/page", 1, 10, "10%", 5]), "pages.csv")
    with Session(gsc_engine) as session:
        persist_gsc_pages(session, parsed)
        snapshot = session.scalars(select(PagePerformanceSnapshot)).one()
        for field, value in invalid_fields.items():
            setattr(snapshot, field, value)
        with pytest.raises(IntegrityError) as error:
            session.flush()
        assert error.value.orig.sqlstate == "23514"


def test_same_run_and_page_cannot_have_two_snapshots(gsc_engine):
    parsed = parse_gsc_pages(csv_file(["https://example.com/page", 1, 10, "10%", 5]), "pages.csv")
    with Session(gsc_engine) as session:
        persist_gsc_pages(session, parsed)
        snapshot = session.scalars(select(PagePerformanceSnapshot)).one()
        session.add(
            PagePerformanceSnapshot(
                import_run_id=snapshot.import_run_id,
                page_id=snapshot.page_id,
                url=snapshot.url,
            )
        )
        with pytest.raises(IntegrityError) as error:
            session.flush()
        assert error.value.orig.sqlstate == "23505"


@pytest.mark.parametrize("parent_type", [ImportRun, WebsitePage])
def test_history_restricts_parent_deletion_instead_of_cascading(gsc_engine, parent_type):
    parsed = parse_gsc_pages(csv_file(["https://example.com/page", 1, 10, "10%", 5]), "pages.csv")
    with Session(gsc_engine) as session:
        persist_gsc_pages(session, parsed)
        parent = session.scalars(select(parent_type)).one()
        session.delete(parent)
        with pytest.raises(IntegrityError) as error:
            session.flush()
        assert error.value.orig.sqlstate == "23503"
