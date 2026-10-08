"""Verify current metric provenance through read-only HTTP boundaries and real PostgreSQL.
通过只读 HTTP 边界及真实 PostgreSQL 验证当前指标来源追踪。
"""

import socket
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gsc_helpers import csv_file
from gsc_helpers import gsc_engine as postgres_import_engine  # noqa: F401
from sqlalchemy import event, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from test_quality_api import seed_history

from app.db.session import get_session
from app.imports.gsc.parser import parse_gsc_pages
from app.imports.gsc.persistence import persist_gsc_pages
from app.main import create_app
from app.models import (
    ImportRun,
    PageMetricProvenance,
    PagePerformanceSnapshot,
    SEOOpportunity,
    WebsitePage,
)

METRICS = ("clicks_28d", "impressions_28d", "ctr", "average_position")


@pytest.fixture
def provenance_client(gsc_engine, isolated_settings):
    application = create_app()

    def override_session():
        with Session(gsc_engine) as session:
            yield session

    application.dependency_overrides[get_session] = override_session
    with TestClient(application) as client:
        yield client


def source_links(engine, page_id, sources):
    with Session(engine) as session, session.begin():
        session.add_all(
            PageMetricProvenance(page_id=page_id, metric_name=metric, snapshot_id=snapshot_id)
            for metric, snapshot_id in sources.items()
        )


def read_provenance(client, page_id):
    response = client.get(f"/api/v1/pages/{page_id}/provenance")
    assert response.status_code == 200, response.text
    return response.json()


def metric_map(payload):
    return {item["metric_name"]: item for item in payload["metrics"]}


def database_state(engine):
    """Capture all persisted values to prove GET requests preserve every table.
    捕获所有持久化值，证明 GET 请求保留每个表。
    """
    with engine.connect() as connection:
        return {
            model.__tablename__: sorted(
                (dict(row) for row in connection.execute(select(model.__table__)).mappings()),
                key=repr,
            )
            for model in (
                WebsitePage,
                ImportRun,
                PagePerformanceSnapshot,
                PageMetricProvenance,
                SEOOpportunity,
            )
        }


def test_successful_import_exposes_four_known_sources_and_nullable_report_dates(
    provenance_client, gsc_engine
):
    parsed = parse_gsc_pages(csv_file(["https://example.com/page", 0, 100, "1.5%", 8]), "new.csv")
    with Session(gsc_engine) as session:
        result = persist_gsc_pages(session, parsed)
        page = session.scalars(select(WebsitePage)).one()
        page_id = page.id
    payload = read_provenance(provenance_client, page_id)
    assert [item["metric_name"] for item in payload["metrics"]] == list(METRICS)
    assert payload["known_provenance_count"] == 4
    assert payload["unknown_provenance_count"] == payload["unavailable_metric_count"] == 0
    assert payload["all_known_metrics_share_one_snapshot"] is True
    assert payload["observations"] == []
    assert len(payload["distinct_snapshot_ids"]) == 1
    assert all(item["status"] == "known" for item in payload["metrics"])
    assert all(item["import_run_id"] == str(result.import_run_id) for item in payload["metrics"])
    assert all(item["period_start"] is item["period_end"] is None for item in payload["metrics"])
    assert all(item["imported_at"] is not None for item in payload["metrics"])
    assert metric_map(payload)["clicks_28d"]["current_value"] == 0
    assert Decimal(metric_map(payload)["ctr"]["current_value"]) == Decimal("0.015")


def test_legacy_equal_snapshots_remain_unknown_with_visibly_uncertain_comparison(
    provenance_client, gsc_engine
):
    page_id, _, _ = seed_history(
        gsc_engine,
        [
            {
                "report_scope": None,
                "coverage_status": "unknown",
                "observed_date_count": None,
                "dates_consecutive": None,
            },
            {
                "report_scope": None,
                "coverage_status": "unknown",
                "observed_date_count": None,
                "dates_consecutive": None,
            },
        ],
    )
    payload = read_provenance(provenance_client, page_id)
    assert payload["unknown_provenance_count"] == 4
    assert payload["known_provenance_count"] == payload["unavailable_metric_count"] == 0
    assert payload["all_known_metrics_share_one_snapshot"] is None
    assert payload["distinct_snapshot_ids"] == []
    assert [item["code"] for item in payload["observations"]] == [
        "unknown_current_metric_provenance"
    ]
    assert payload["observations"][0]["severity"] == "warning"
    assert all(item["snapshot_id"] is item["import_run_id"] is None for item in payload["metrics"])
    history = provenance_client.get(f"/api/v1/pages/{page_id}/performance").json()
    assert history["provenance"] == payload
    assert history["comparison"]["scope_compatibility"] == "unknown"
    assert history["quality"]["readiness"] == "limited"
    assert history["quality"]["readiness_reasons"] == [
        "unknown_report_scope",
        "unknown_date_coverage",
    ]


def test_null_current_metrics_are_unavailable_not_unknown(provenance_client, gsc_engine):
    with Session(gsc_engine) as session:
        page = WebsitePage(url="https://example.com/empty")
        session.add(page)
        session.commit()
        page_id = page.id
    payload = read_provenance(provenance_client, page_id)
    assert payload["unavailable_metric_count"] == 4
    assert payload["known_provenance_count"] == payload["unknown_provenance_count"] == 0
    assert payload["observations"] == []
    assert payload["all_known_metrics_share_one_snapshot"] is None
    assert all(item["status"] == "unavailable" for item in payload["metrics"])


def test_mixed_recorded_sources_are_factual_and_preserve_exact_phase4_quality(
    provenance_client, gsc_engine
):
    page_id, runs, snapshots = seed_history(gsc_engine, [{}, {}])
    before = provenance_client.get(f"/api/v1/pages/{page_id}/performance").json()
    source_links(gsc_engine, page_id, dict.fromkeys(METRICS, snapshots[0]) | {"ctr": snapshots[1]})
    after = provenance_client.get(f"/api/v1/pages/{page_id}/performance").json()
    assert after["quality"] == before["quality"]
    assert after["comparison"] == before["comparison"]
    payload = after["provenance"]
    assert payload == read_provenance(provenance_client, page_id)
    assert payload["known_provenance_count"] == 4
    assert payload["all_known_metrics_share_one_snapshot"] is False
    assert payload["distinct_snapshot_ids"] == [str(item) for item in snapshots]
    observation = payload["observations"][0]
    assert observation["code"] == "current_state_not_single_snapshot"
    assert observation["severity"] == "info"
    assert observation["snapshot_ids"] == [str(item) for item in snapshots]
    assert observation["import_run_ids"] == [str(item) for item in runs]


def test_one_known_source_with_unknown_metrics_does_not_claim_mixed_state(
    provenance_client, gsc_engine
):
    page_id, _, snapshots = seed_history(gsc_engine, [{}])
    source_links(gsc_engine, page_id, {"clicks_28d": snapshots[0]})
    payload = read_provenance(provenance_client, page_id)
    assert payload["known_provenance_count"] == 1
    assert payload["unknown_provenance_count"] == 3
    assert payload["all_known_metrics_share_one_snapshot"] is True
    assert [item["code"] for item in payload["observations"]] == [
        "unknown_current_metric_provenance"
    ]
    assert payload["observations"][0]["evidence"]["metric_names"] == list(METRICS[1:])


def test_cross_page_recorded_link_is_never_exposed_as_known(provenance_client, gsc_engine):
    other_id, _, snapshots = seed_history(gsc_engine, [{}])
    with Session(gsc_engine) as session:
        page = WebsitePage(url="https://example.com/other", clicks_28d=20)
        session.add(page)
        session.commit()
        page_id = page.id
    assert other_id != page_id
    source_links(gsc_engine, page_id, {"clicks_28d": snapshots[0]})
    metric = metric_map(read_provenance(provenance_client, page_id))["clicks_28d"]
    assert metric["status"] == "unknown"
    assert metric["snapshot_id"] is metric["import_run_id"] is metric["imported_at"] is None


@pytest.mark.parametrize("current_value", [None, 999])
def test_inconsistent_or_null_current_metric_does_not_expose_stale_metadata(
    provenance_client, gsc_engine, current_value
):
    page_id, _, snapshots = seed_history(gsc_engine, [{}])
    source_links(gsc_engine, page_id, {"clicks_28d": snapshots[0]})
    with Session(gsc_engine) as session, session.begin():
        session.get(WebsitePage, page_id).clicks_28d = current_value
    metric = metric_map(read_provenance(provenance_client, page_id))["clicks_28d"]
    assert metric["status"] == ("unavailable" if current_value is None else "unknown")
    assert metric["snapshot_id"] is metric["import_run_id"] is None


def test_embedded_and_dedicated_provenance_are_pagination_independent(
    provenance_client, gsc_engine
):
    page_id, _, snapshots = seed_history(gsc_engine, [{}, {}, {}])
    source_links(gsc_engine, page_id, dict.fromkeys(METRICS, snapshots[1]))
    expected = read_provenance(provenance_client, page_id)
    for page_number in (1, 3, 100):
        response = provenance_client.get(
            f"/api/v1/pages/{page_id}/performance?page={page_number}&page_size=1"
        )
        assert response.status_code == 200
        assert response.json()["provenance"] == expected


@pytest.mark.parametrize("page_id, expected_status", [(str(uuid4()), 404), ("invalid", 422)])
def test_provenance_not_found_and_invalid_uuid(provenance_client, page_id, expected_status):
    response = provenance_client.get(f"/api/v1/pages/{page_id}/provenance")
    assert response.status_code == expected_status
    if expected_status == 404:
        assert response.json()["detail"]["code"] == "page_not_found"


@pytest.mark.parametrize("method", ["get", "execute", "scalars"])
def test_database_failures_return_generic_503_at_every_load_step(
    provenance_client, gsc_engine, monkeypatch, method
):
    page_id, _, _ = seed_history(gsc_engine, [{}])

    def fail_database(*args, **kwargs):
        raise SQLAlchemyError("synthetic private SQL connection details")

    monkeypatch.setattr(Session, method, fail_database)
    response = provenance_client.get(f"/api/v1/pages/{page_id}/provenance")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "database_unavailable"
    assert "synthetic private" not in response.text


def test_provenance_gets_are_read_only_and_call_no_external_services(
    provenance_client, gsc_engine, monkeypatch
):
    page_id, _, snapshots = seed_history(gsc_engine, [{}, {}])
    source_links(gsc_engine, page_id, dict.fromkeys(METRICS, snapshots[0]))
    with Session(gsc_engine) as session, session.begin():
        session.add(
            SEOOpportunity(
                page_id=page_id,
                opportunity_type="synthetic_existing",
                recommended_action="Synthetic existing content",
                reason="Read-only preservation fixture",
            )
        )
    before = database_state(gsc_engine)
    statements = []

    def record_statement(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    def prevent_external_connections(*args, **kwargs):
        raise AssertionError("Provenance analysis must not call external services")

    monkeypatch.setattr(socket.socket, "connect", prevent_external_connections)
    monkeypatch.setattr(socket.socket, "connect_ex", prevent_external_connections)
    event.listen(gsc_engine, "before_cursor_execute", record_statement)
    try:
        for suffix in ("provenance", "performance", "quality"):
            assert provenance_client.get(f"/api/v1/pages/{page_id}/{suffix}").status_code == 200
    finally:
        event.remove(gsc_engine, "before_cursor_execute", record_statement)
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    assert database_state(gsc_engine) == before
    assert len(before["seo_opportunities"]) == 1


def test_performance_loads_links_once_and_quality_does_not_load_them(provenance_client, gsc_engine):
    page_id, _, _ = seed_history(gsc_engine, [{}, {}])
    statements = []

    def record_statement(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(gsc_engine, "before_cursor_execute", record_statement)
    try:
        assert provenance_client.get(f"/api/v1/pages/{page_id}/performance").status_code == 200
        assert len(statements) == 3
        assert sum("page_metric_provenance" in statement for statement in statements) == 1
        statements.clear()
        assert provenance_client.get(f"/api/v1/pages/{page_id}/quality").status_code == 200
        assert len(statements) == 2
        assert not any("page_metric_provenance" in statement for statement in statements)
    finally:
        event.remove(gsc_engine, "before_cursor_execute", record_statement)
