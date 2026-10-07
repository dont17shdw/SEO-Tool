import hashlib
import socket
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from gsc_helpers import gsc_engine as postgres_import_engine  # noqa: F401
from sqlalchemy import event, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.main import create_app
from app.models import ImportRun, PagePerformanceSnapshot, SEOOpportunity, WebsitePage


@pytest.fixture
def quality_client(gsc_engine, isolated_settings):
    application = create_app()

    def override_session():
        with Session(gsc_engine) as session:
            yield session

    application.dependency_overrides[get_session] = override_session
    with TestClient(application) as client:
        yield client


def seed_history(engine, definitions):
    """Seed synthetic persisted evidence independently of import parsing.
    独立于导入解析，填充合成的已持久化证据。
    """
    page_id = uuid4()
    run_ids, snapshot_ids = [], []
    with Session(engine) as session:
        page = WebsitePage(
            id=page_id,
            url="https://example.com/page",
            clicks_28d=20,
            impressions_28d=500,
            ctr=Decimal("0.025"),
            average_position=Decimal("8"),
        )
        session.add(page)
        session.flush()
        for number, fields in enumerate(definitions, start=1):
            start = fields.get("period_start", date(2026, 1, 1) + timedelta(days=28 * (number - 1)))
            end = fields.get("period_end", start + timedelta(days=27) if start else None)
            imported_at = fields.get(
                "imported_at", datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=number)
            )
            run_id, snapshot_id = UUID(int=1000 + number), UUID(int=number)
            run = ImportRun(
                id=run_id,
                source=fields.get("source", "gsc"),
                source_type=fields.get("source_type", "pages_performance"),
                reporting_window=fields.get("reporting_window", "latest_28_days"),
                file_hash=hashlib.sha256(f"{page_id}:{number}".encode()).hexdigest(),
                filename=f"synthetic-{number}.xlsx",
                period_start=start,
                period_end=end,
                imported_at=imported_at,
                total_rows=1,
                created_count=1,
                status="completed",
            )
            session.add(run)
            session.flush()
            metrics = {
                "clicks": fields.get("clicks", 20),
                "impressions": fields.get("impressions", 500),
                "ctr": fields.get("ctr", Decimal("0.025")),
                "average_position": fields.get("average_position", Decimal("8")),
            }
            session.add(
                PagePerformanceSnapshot(
                    id=snapshot_id,
                    import_run_id=run_id,
                    page_id=page_id,
                    url=page.url,
                    period_start=start,
                    period_end=end,
                    **metrics,
                )
            )
            for metric, value in metrics.items():
                if value is not None:
                    page_field = {"clicks": "clicks_28d", "impressions": "impressions_28d"}.get(
                        metric, metric
                    )
                    setattr(page, page_field, value)
            run_ids.append(run_id)
            snapshot_ids.append(snapshot_id)
        session.commit()
    return page_id, run_ids, snapshot_ids


def quality_codes(response):
    return {observation["code"]: observation for observation in response["observations"]}


def test_page_without_history_is_insufficient(quality_client, gsc_engine):
    page_id, _, _ = seed_history(gsc_engine, [])
    response = quality_client.get(f"/api/v1/pages/{page_id}/quality")
    assert response.status_code == 200
    quality = response.json()
    assert quality["page_id"] == str(page_id)
    assert quality["readiness"] == "insufficient"
    assert quality["comparison_exists"] is False
    assert quality["selected_snapshot_ids"] == []
    assert quality["counts"]["total_snapshots"] == 0
    assert "insufficient_history" in quality["readiness_reasons"]
    assert quality_codes(quality)["insufficient_history"]["severity"] == "blocking"


def test_one_exact_period_is_insufficient(quality_client, gsc_engine):
    page_id, _, _ = seed_history(gsc_engine, [{}])
    quality = quality_client.get(f"/api/v1/pages/{page_id}/quality").json()
    assert quality["readiness"] == "insufficient"
    assert quality["counts"]["exact_date_snapshots"] == 1
    assert quality["counts"]["compatible_exact_periods"] == 1


def test_two_complete_nonoverlapping_periods_are_ready_and_embedded_quality_matches(
    quality_client, gsc_engine
):
    page_id, _, snapshots = seed_history(gsc_engine, [{}, {}])
    dedicated = quality_client.get(f"/api/v1/pages/{page_id}/quality").json()
    performance = quality_client.get(f"/api/v1/pages/{page_id}/performance").json()
    assert performance["quality"] == dedicated
    assert dedicated["readiness"] == "ready"
    assert dedicated["comparison_exists"] is True
    assert dedicated["selected_snapshot_ids"] == [str(identifier) for identifier in snapshots]
    assert dedicated["readiness_reasons"] == []
    assert dedicated["counts"]["total_snapshots"] == 2
    assert dedicated["counts"]["distinct_exact_periods"] == 2
    assert dedicated["counts"]["compatible_exact_periods"] == 2


@pytest.mark.parametrize(
    ("definitions", "expected_code"),
    [
        ([{}, {"period_start": date(2026, 1, 8)}], "overlapping_comparison_periods"),
        ([{"ctr": None}, {}], "missing_metrics"),
        ([{"clicks": 0}, {}], "zero_percentage_baseline"),
        ([{"impressions": 0}, {}], "zero_percentage_baseline"),
        (
            [
                {"period_start": date(2026, 2, 1)},
                {"period_start": date(2026, 1, 1)},
            ],
            "out_of_order_import",
        ),
    ],
)
def test_selected_pair_caveats_limit_readiness_and_name_affected_evidence(
    quality_client, gsc_engine, definitions, expected_code
):
    page_id, runs, snapshots = seed_history(gsc_engine, definitions)
    quality = quality_client.get(f"/api/v1/pages/{page_id}/quality").json()
    assert quality["readiness"] == "limited"
    assert quality["comparison_exists"] is True
    assert expected_code in quality["readiness_reasons"]
    observation = quality_codes(quality)[expected_code]
    assert observation["scope"] == "page"
    assert observation["severity"] == "warning"
    assert observation["evidence"]
    assert set(observation["snapshot_ids"]).issubset({str(identifier) for identifier in snapshots})
    assert set(observation["import_run_ids"]).issubset({str(identifier) for identifier in runs})
    assert " / " in observation["message"] or "。" in observation["message"]


def test_unknown_history_and_revision_facts_do_not_downgrade_complete_selected_pair(
    quality_client, gsc_engine
):
    page_id, _, _ = seed_history(
        gsc_engine,
        [
            {"period_start": None},
            {"period_start": date(2026, 1, 1)},
            {"period_start": date(2026, 1, 1)},
            {"period_start": date(2026, 2, 1)},
        ],
    )
    quality = quality_client.get(f"/api/v1/pages/{page_id}/quality").json()
    assert quality["readiness"] == "ready"
    assert "unknown_reporting_dates" in quality_codes(quality)
    assert quality_codes(quality)["same_period_revisions"]["severity"] == "info"
    assert quality["counts"]["unknown_date_snapshots"] == 1
    assert quality["counts"]["revision_periods"] == 1


def test_quality_uses_entire_history_independently_of_snapshot_pagination(
    quality_client, gsc_engine
):
    page_id, _, snapshots = seed_history(gsc_engine, [{}, {}, {}])
    endpoint = f"/api/v1/pages/{page_id}/performance"
    first = quality_client.get(endpoint + "?page=1&page_size=1").json()
    last = quality_client.get(endpoint + "?page=3&page_size=1").json()
    past_end = quality_client.get(endpoint + "?page=100&page_size=1").json()
    dedicated = quality_client.get(f"/api/v1/pages/{page_id}/quality").json()
    assert first["quality"] == last["quality"] == past_end["quality"] == dedicated
    assert dedicated["counts"]["total_snapshots"] == 3
    assert dedicated["selected_snapshot_ids"] == [str(identifier) for identifier in snapshots[-2:]]


def test_equal_import_timestamps_do_not_prove_out_of_order(quality_client, gsc_engine):
    same_time = datetime(2026, 1, 1, tzinfo=UTC)
    page_id, runs, _ = seed_history(
        gsc_engine,
        [
            {"period_start": date(2026, 2, 1), "imported_at": same_time},
            {"period_start": date(2026, 1, 1), "imported_at": same_time},
        ],
    )
    quality = quality_client.get(f"/api/v1/pages/{page_id}/quality").json()
    assert quality["readiness"] == "ready"
    assert "out_of_order_import" not in quality_codes(quality)
    import_quality = quality_client.get(f"/api/v1/imports/{runs[-1]}/quality").json()
    assert "out_of_order_import" not in quality_codes(import_quality)


def test_import_quality_context_contains_revisions_overlap_and_chronology(
    quality_client, gsc_engine
):
    _, runs, _ = seed_history(
        gsc_engine,
        [
            {"period_start": date(2026, 2, 1)},
            {"period_start": date(2026, 1, 1)},
            {"period_start": date(2026, 1, 1)},
            {"period_start": date(2026, 1, 8)},
        ],
    )
    response = quality_client.get(f"/api/v1/imports/{runs[2]}/quality")
    assert response.status_code == 200
    quality = response.json()
    assert quality["import_run_id"] == str(runs[2])
    codes = quality_codes(quality)
    assert {"same_period_revisions", "overlapping_reporting_periods", "out_of_order_import"} <= (
        codes.keys()
    )
    assert all(item["scope"] == "import" for item in codes.values())
    assert quality["counts"]["total_imports"] == 4
    assert quality["counts"]["same_period_revision_imports"] == 1
    assert quality["counts"]["overlapping_imports"] == 1
    assert quality["counts"]["earlier_imported_newer_periods"] == 1


def test_import_quality_unknown_dates_and_source_context_filtering(quality_client, gsc_engine):
    _, runs, _ = seed_history(
        gsc_engine,
        [{"period_start": None}, {"source": "other_source"}, {"source_type": "other_type"}],
    )
    quality = quality_client.get(f"/api/v1/imports/{runs[0]}/quality").json()
    assert "unknown_reporting_dates" in quality_codes(quality)
    assert quality["counts"]["total_imports"] == 1
    assert quality["counts"]["unknown_date_imports"] == 1


@pytest.mark.parametrize("resource", ["pages", "imports"])
def test_quality_missing_resource_and_invalid_uuid(quality_client, resource):
    missing = quality_client.get(f"/api/v1/{resource}/{uuid4()}/quality")
    assert missing.status_code == 404
    expected = "page_not_found" if resource == "pages" else "import_not_found"
    assert missing.json()["detail"]["code"] == expected
    assert quality_client.get(f"/api/v1/{resource}/invalid/quality").status_code == 422


@pytest.mark.parametrize("resource", ["pages", "imports"])
def test_quality_database_failure_is_generic(isolated_settings, resource):
    application = create_app()

    class UnavailableSession:
        def get(self, *args, **kwargs):
            raise SQLAlchemyError("private database hostname")

    application.dependency_overrides[get_session] = lambda: UnavailableSession()
    with TestClient(application) as client:
        response = client.get(f"/api/v1/{resource}/{uuid4()}/quality")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "database_unavailable"
    assert "private database hostname" not in response.text


def database_state(engine):
    with engine.connect() as connection:
        return {
            model.__tablename__: connection.execute(
                select(model.__table__).order_by(model.__table__.c.id)
            ).all()
            for model in (WebsitePage, ImportRun, PagePerformanceSnapshot, SEOOpportunity)
        }


def test_quality_reads_preserve_database_and_do_not_call_external_ai(
    quality_client, gsc_engine, monkeypatch
):
    page_id, runs, _ = seed_history(gsc_engine, [{}, {}])
    with Session(gsc_engine) as session:
        session.add(
            SEOOpportunity(
                page_id=page_id,
                opportunity_type="synthetic_existing_record",
                recommended_action="Synthetic stored text",
                reason="Read-only preservation fixture",
            )
        )
        session.commit()
    before = database_state(gsc_engine)
    statements = []

    def record_statement(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    def prevent_external_connections(*args, **kwargs):
        raise AssertionError("Runtime evidence analysis must not access external services")

    # Existing database connections are available; block new Python network connections.
    # 已有数据库连接可用；阻止新的 Python 网络连接。
    monkeypatch.setattr(socket.socket, "connect", prevent_external_connections)
    monkeypatch.setattr(socket.socket, "connect_ex", prevent_external_connections)
    event.listen(gsc_engine, "before_cursor_execute", record_statement)
    try:
        assert quality_client.get(f"/api/v1/pages/{page_id}/quality").status_code == 200
        assert quality_client.get(f"/api/v1/pages/{page_id}/performance").status_code == 200
        for run_id in runs:
            assert quality_client.get(f"/api/v1/imports/{run_id}/quality").status_code == 200
    finally:
        event.remove(gsc_engine, "before_cursor_execute", record_statement)
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    assert database_state(gsc_engine) == before
    assert len(before["seo_opportunities"]) == 1


def test_performance_reuses_one_history_query_and_one_comparison(
    quality_client, gsc_engine, monkeypatch
):
    page_id, _, _ = seed_history(gsc_engine, [{}, {}])
    from app.api.v1 import history

    original_compare = history.compare_performance
    comparisons = 0
    statements = []

    def count_comparisons(observations):
        nonlocal comparisons
        comparisons += 1
        return original_compare(observations)

    def record_statement(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    monkeypatch.setattr(history, "compare_performance", count_comparisons)
    event.listen(gsc_engine, "before_cursor_execute", record_statement)
    try:
        response = quality_client.get(f"/api/v1/pages/{page_id}/performance")
    finally:
        event.remove(gsc_engine, "before_cursor_execute", record_statement)
    assert response.status_code == 200
    assert comparisons == 1
    assert len(statements) == 3
