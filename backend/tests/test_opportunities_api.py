"""Validate read-only candidate APIs using synthetic, isolated PostgreSQL evidence.
使用合成的隔离 PostgreSQL 证据验证只读候选 API。
"""

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
from app.models import (
    ImportRun,
    PageMetricProvenance,
    PagePerformanceSnapshot,
    SEOOpportunity,
    Site,
    WebsitePage,
)
from app.normalization.report_scope import canonical_scope_key

KNOWN_SCOPE = {
    "property_id": "sc-domain:example.com",
    "search_type": "web",
    "filters": [],
    "filters_complete": True,
}


@pytest.fixture
def opportunities_client(gsc_engine, isolated_settings):
    application = create_app()

    def override_session():
        with Session(gsc_engine) as session:
            yield session

    application.dependency_overrides[get_session] = override_session
    with TestClient(application) as client:
        yield client


def seed_page_history(
    engine,
    definitions,
    *,
    url="https://example.com/page",
    page_id=None,
    site_id=None,
    report_scope=KNOWN_SCOPE,
):
    """Seed independent synthetic pages without parser or candidate-engine dependencies.
    不依赖解析器或候选引擎，填充相互独立的合成页面。
    """
    page_id = page_id or uuid4()
    snapshot_ids = []
    with Session(engine) as session:
        website_page = WebsitePage(id=page_id, site_id=site_id, url=url)
        session.add(website_page)
        session.flush()
        for number, fields in enumerate(definitions):
            start = fields.get("period_start", date(2026, 1, 1) + timedelta(days=28 * number))
            end = fields.get("period_end", start + timedelta(days=27) if start else None)
            scope = fields.get("report_scope", report_scope)
            run_id, snapshot_id = uuid4(), uuid4()
            run = ImportRun(
                id=run_id,
                site_id=site_id,
                source="gsc",
                source_type="pages_performance",
                reporting_window="latest_28_days",
                file_hash=hashlib.sha256(str(run_id).encode()).hexdigest(),
                filename=f"synthetic-{number}.xlsx",
                period_start=start,
                period_end=end,
                imported_at=fields.get(
                    "imported_at", datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=number)
                ),
                total_rows=1,
                created_count=1,
                status="completed",
                report_scope=scope,
                scope_fingerprint=canonical_scope_key(scope),
                coverage_status=fields.get("coverage_status", "complete" if start else "unknown"),
                observed_date_count=fields.get("observed_date_count", 28 if start else None),
                dates_consecutive=fields.get("dates_consecutive", True if start else None),
            )
            session.add(run)
            session.flush()
            metrics = {
                "clicks": fields.get("clicks", 20),
                "impressions": fields.get("impressions", 500),
                "ctr": fields.get("ctr", Decimal("0.04")),
                "average_position": fields.get("average_position", Decimal("8")),
            }
            session.add(
                PagePerformanceSnapshot(
                    id=snapshot_id,
                    import_run_id=run_id,
                    page_id=page_id,
                    url=url,
                    period_start=start,
                    period_end=end,
                    **metrics,
                )
            )
            for metric, value in metrics.items():
                page_field = {"clicks": "clicks_28d", "impressions": "impressions_28d"}.get(
                    metric, metric
                )
                setattr(website_page, page_field, value)
            snapshot_ids.append(snapshot_id)
        session.commit()
    return page_id, snapshot_ids


def database_state(engine):
    with engine.connect() as connection:
        return {
            model.__tablename__: connection.execute(
                select(model.__table__).order_by(*model.__table__.primary_key.columns)
            ).all()
            for model in (
                Site,
                WebsitePage,
                ImportRun,
                PagePerformanceSnapshot,
                PageMetricProvenance,
                SEOOpportunity,
            )
        }


def test_page_candidates_expose_selected_metrics_and_multiple_signals(
    opportunities_client, gsc_engine
):
    page_id, snapshots = seed_page_history(
        gsc_engine, [{}, {"clicks": 12, "average_position": Decimal("10")}]
    )
    response = opportunities_client.get(f"/api/v1/pages/{page_id}/opportunities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["eligible"] is True
    assert payload["evidence_readiness"] == "ready"
    assert payload["gate_reasons"] == payload["gate_observations"] == []
    assert payload["page_id"] == str(page_id)
    assert payload["comparison"]["previous_snapshot_id"] == str(snapshots[0])
    assert payload["comparison"]["current_snapshot_id"] == str(snapshots[1])
    candidates = {item["opportunity_type"]: item for item in payload["candidates"]}
    assert set(candidates) == {"traffic_decline", "ranking_decline"}
    traffic = candidates["traffic_decline"]
    assert traffic["previous_snapshot_id"] == str(snapshots[0])
    assert traffic["current_snapshot_id"] == str(snapshots[1])
    assert traffic["evidence"]["previous"] == {"clicks": 20}
    assert traffic["evidence"]["current"] == {"clicks": 12}
    assert traffic["evidence"]["changes"] == {
        "clicks_absolute_change": -8,
        "clicks_percentage_change": "-40.000000",
    }
    assert traffic["evidence"]["thresholds"]["minimum_previous_clicks"] == 5
    assert traffic["scope_compatibility"] == "compatible"
    assert " / " in traffic["message"]
    forbidden = {
        "opportunity_score",
        "priority",
        "severity",
        "recommended_action",
        "confidence",
        "expected_impact",
        "estimated_effort",
        "risk_level",
    }
    assert all(forbidden.isdisjoint(candidate) for candidate in candidates.values())


@pytest.mark.parametrize(
    ("definitions", "reason"),
    [
        ([], "insufficient_history"),
        ([{}], "insufficient_history"),
        ([{"report_scope": None}, {"report_scope": None}], "unknown_report_scope"),
        (
            [
                {},
                {
                    "coverage_status": "partial",
                    "observed_date_count": 3,
                    "dates_consecutive": False,
                },
            ],
            "incomplete_date_coverage",
        ),
        (
            [
                {},
                {
                    "coverage_status": "unknown",
                    "observed_date_count": None,
                    "dates_consecutive": None,
                },
            ],
            "unknown_date_coverage",
        ),
        ([{}, {"clicks": 12, "ctr": None}], "missing_metrics"),
        ([{}, {"period_start": date(2026, 1, 8), "clicks": 12}], "overlapping_comparison_periods"),
        ([{"clicks": 0}, {"clicks": 12}], "zero_percentage_baseline"),
        (
            [{"period_start": date(2026, 2, 1)}, {"period_start": date(2026, 1, 1), "clicks": 12}],
            "out_of_order_import",
        ),
    ],
)
def test_ineligible_page_reuses_existing_quality_reasons(
    opportunities_client, gsc_engine, definitions, reason
):
    page_id, _ = seed_page_history(gsc_engine, definitions)
    payload = opportunities_client.get(f"/api/v1/pages/{page_id}/opportunities").json()
    quality = opportunities_client.get(f"/api/v1/pages/{page_id}/quality").json()
    assert payload["eligible"] is False
    assert payload["candidates"] == []
    assert payload["evidence_readiness"] == quality["readiness"]
    assert reason in payload["gate_reasons"]
    assert set(payload["gate_reasons"]).issubset(quality["readiness_reasons"])
    assert any(item["code"] == reason for item in payload["gate_observations"])
    assert all(item in quality["observations"] for item in payload["gate_observations"])


def test_ready_page_with_no_threshold_met_is_an_eligible_empty_result(
    opportunities_client, gsc_engine
):
    page_id, _ = seed_page_history(gsc_engine, [{}, {}])
    payload = opportunities_client.get(f"/api/v1/pages/{page_id}/opportunities").json()
    assert payload["eligible"] is True
    assert payload["candidates"] == []
    assert payload["gate_reasons"] == payload["gate_observations"] == []


def test_global_pagination_counts_candidates_and_uses_neutral_stable_order(
    opportunities_client, gsc_engine
):
    seed_page_history(gsc_engine, [{}, {}], url="https://example.com/a-no-signals")
    seed_page_history(gsc_engine, [], url="https://example.com/b-insufficient")
    earlier_page, _ = seed_page_history(
        gsc_engine,
        [{}, {"clicks": 12, "average_position": Decimal("10")}],
        url="https://example.com/c-two-signals",
    )
    later_page, _ = seed_page_history(
        gsc_engine, [{}, {"clicks": 5}], url="https://example.com/z-one-signal"
    )
    all_items = opportunities_client.get("/api/v1/opportunities").json()
    assert all_items["total"] == 3
    assert [item["page_id"] for item in all_items["items"]] == [
        str(earlier_page),
        str(earlier_page),
        str(later_page),
    ]
    assert [item["opportunity_type"] for item in all_items["items"]] == [
        "ranking_decline",
        "traffic_decline",
        "traffic_decline",
    ]
    flattened = []
    for number in range(1, 4):
        page = opportunities_client.get(f"/api/v1/opportunities?page={number}&page_size=1").json()
        assert page["total"] == page["total_pages"] == 3
        assert page["page"] == number
        flattened.extend(page["items"])
    assert flattened == all_items["items"]
    assert (
        opportunities_client.get("/api/v1/opportunities?page=4&page_size=1").json()["items"] == []
    )
    assert opportunities_client.get("/api/v1/opportunities").json() == all_items


def test_global_site_filter_and_equal_url_tie_follow_page_ownership(
    opportunities_client, gsc_engine
):
    site_ids = [uuid4(), uuid4()]
    identifiers = ["sc-domain:example.com", "https://example.com/"]
    with Session(gsc_engine) as session:
        for site_id, identifier in zip(site_ids, identifiers, strict=True):
            session.add(Site(id=site_id, identifier=identifier, display_name=identifier))
        session.commit()
    page_ids = [UUID(int=20), UUID(int=10)]
    for site_id, page_id, identifier in zip(site_ids, page_ids, identifiers, strict=True):
        seed_page_history(
            gsc_engine,
            [{}, {"clicks": 12}],
            site_id=site_id,
            page_id=page_id,
            report_scope=KNOWN_SCOPE | {"property_id": identifier},
        )
    all_items = opportunities_client.get("/api/v1/opportunities").json()["items"]
    assert [item["page_id"] for item in all_items] == [str(item) for item in sorted(page_ids)]
    for site_id, page_id in zip(site_ids, page_ids, strict=True):
        payload = opportunities_client.get(f"/api/v1/opportunities?site_id={site_id}").json()
        assert payload["total"] == 1
        assert payload["items"][0]["site_id"] == str(site_id)
        assert payload["items"][0]["page_id"] == str(page_id)
    assert opportunities_client.get(f"/api/v1/opportunities?site_id={uuid4()}").json()["total"] == 0


def test_empty_global_list_and_missing_page(opportunities_client):
    assert opportunities_client.get("/api/v1/opportunities").json() == {
        "items": [],
        "page": 1,
        "page_size": 50,
        "total": 0,
        "total_pages": 0,
    }
    missing = opportunities_client.get(f"/api/v1/pages/{uuid4()}/opportunities")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "page_not_found"
    assert opportunities_client.get("/api/v1/pages/invalid/opportunities").status_code == 422


@pytest.mark.parametrize("query", ["page=0", "page_size=0", "page_size=101", "site_id=invalid"])
def test_global_query_bounds_without_database_reads(isolated_settings, query):
    application = create_app()

    def override_session():
        return None

    application.dependency_overrides[get_session] = override_session
    with TestClient(application) as client:
        assert client.get(f"/api/v1/opportunities?{query}").status_code == 422


@pytest.mark.parametrize(
    "endpoint", ["/api/v1/opportunities", f"/api/v1/pages/{UUID(int=1)}/opportunities"]
)
def test_opportunity_database_errors_are_generic(isolated_settings, endpoint):
    application = create_app()

    class UnavailableSession:
        def get(self, *args, **kwargs):
            raise SQLAlchemyError("private database hostname")

        def scalars(self, *args, **kwargs):
            raise SQLAlchemyError("private database hostname")

    application.dependency_overrides[get_session] = lambda: UnavailableSession()
    with TestClient(application) as client:
        response = client.get(endpoint)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "database_unavailable"
    assert "private database hostname" not in response.text


def test_history_query_failure_does_not_expose_database_details(
    opportunities_client, gsc_engine, monkeypatch
):
    page_id, _ = seed_page_history(gsc_engine, [])

    def fail_history_query(*args, **kwargs):
        raise SQLAlchemyError("private snapshot SQL")

    monkeypatch.setattr(Session, "execute", fail_history_query)
    response = opportunities_client.get(f"/api/v1/pages/{page_id}/opportunities")
    assert response.status_code == 503
    assert "private snapshot SQL" not in response.text


def test_embedded_analysis_preserves_comparison_quality_provenance_and_ignores_current_state(
    opportunities_client, gsc_engine
):
    page_id, snapshots = seed_page_history(gsc_engine, [{}, {"clicks": 12}])
    with Session(gsc_engine) as session:
        website_page = session.get(WebsitePage, page_id)
        website_page.clicks_28d = 999
        session.add(
            PageMetricProvenance(page_id=page_id, metric_name="ctr", snapshot_id=snapshots[1])
        )
        session.commit()
    endpoint = f"/api/v1/pages/{page_id}"
    quality_before = opportunities_client.get(endpoint + "/quality").json()
    provenance_before = opportunities_client.get(endpoint + "/provenance").json()
    standalone = opportunities_client.get(endpoint + "/opportunities").json()
    first = opportunities_client.get(endpoint + "/performance?page_size=1").json()
    second = opportunities_client.get(endpoint + "/performance?page=2&page_size=1").json()
    assert first["opportunities"] == second["opportunities"] == standalone
    assert first["comparison"] == second["comparison"] == standalone["comparison"]
    assert first["quality"] == second["quality"] == quality_before
    assert first["provenance"] == second["provenance"] == provenance_before
    assert first["current_page"]["clicks_28d"] == 999
    assert standalone["candidates"][0]["evidence"]["current"]["clicks"] == 12


@pytest.mark.parametrize(("path", "expected_reads"), [("opportunities", 2), ("performance", 3)])
def test_page_reuses_one_comparison_and_quality_analysis(
    opportunities_client, gsc_engine, monkeypatch, path, expected_reads
):
    from app.api.v1 import history

    page_id, _ = seed_page_history(gsc_engine, [{}, {"clicks": 12}])
    original_compare = history.compare_performance
    original_quality = history.analyse_page_quality
    counts = {"comparison": 0, "quality": 0}
    statements = []

    def count_comparisons(observations):
        counts["comparison"] += 1
        return original_compare(observations)

    def count_quality(*args, **kwargs):
        counts["quality"] += 1
        return original_quality(*args, **kwargs)

    def record_statement(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    monkeypatch.setattr(history, "compare_performance", count_comparisons)
    monkeypatch.setattr(history, "analyse_page_quality", count_quality)
    event.listen(gsc_engine, "before_cursor_execute", record_statement)
    try:
        response = opportunities_client.get(f"/api/v1/pages/{page_id}/{path}")
    finally:
        event.remove(gsc_engine, "before_cursor_execute", record_statement)
    assert response.status_code == 200
    assert counts == {"comparison": 1, "quality": 1}
    assert len(statements) == expected_reads


def test_global_loader_uses_two_reads_instead_of_per_page_queries(opportunities_client, gsc_engine):
    for number in range(5):
        seed_page_history(gsc_engine, [{}, {"clicks": 12}], url=f"https://example.com/{number}")
    statements = []

    def record_statement(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(gsc_engine, "before_cursor_execute", record_statement)
    try:
        response = opportunities_client.get("/api/v1/opportunities?page_size=2")
    finally:
        event.remove(gsc_engine, "before_cursor_execute", record_statement)
    assert response.status_code == 200
    assert response.json()["total"] == 5
    assert len(statements) == 2


def test_get_operations_preserve_all_tables_and_never_access_external_services(
    opportunities_client, gsc_engine, monkeypatch
):
    page_id, snapshots = seed_page_history(gsc_engine, [{}, {"clicks": 12}])
    with Session(gsc_engine) as session:
        session.add(
            SEOOpportunity(
                page_id=page_id,
                opportunity_type="synthetic_existing_record",
                recommended_action="Reserved stored fixture",
                reason="Must remain untouched by runtime candidates",
            )
        )
        session.add(
            PageMetricProvenance(page_id=page_id, metric_name="ctr", snapshot_id=snapshots[1])
        )
        session.commit()
    before = database_state(gsc_engine)
    statements = []

    def record_statement(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    def prevent_external_connections(*args, **kwargs):
        raise AssertionError("Opportunity candidates must not call external services or AI")

    monkeypatch.setattr(socket.socket, "connect", prevent_external_connections)
    monkeypatch.setattr(socket.socket, "connect_ex", prevent_external_connections)
    event.listen(gsc_engine, "before_cursor_execute", record_statement)
    try:
        paths = [
            f"/api/v1/pages/{page_id}/opportunities",
            f"/api/v1/pages/{page_id}/performance",
            "/api/v1/opportunities",
            "/api/v1/opportunities?page=2&page_size=1",
        ]
        for path in paths:
            assert opportunities_client.get(path).status_code == 200
    finally:
        event.remove(gsc_engine, "before_cursor_execute", record_statement)
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    assert database_state(gsc_engine) == before
    assert len(before["seo_opportunities"]) == 1
