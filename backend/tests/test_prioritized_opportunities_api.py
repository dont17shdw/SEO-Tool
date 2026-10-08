"""Verify transparent read-only prioritization and unchanged neutral detection contracts.
验证透明只读优先级及不变的中立检测契约。
"""

import socket
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from gsc_helpers import gsc_engine as postgres_import_engine  # noqa: F401
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from test_opportunities_api import (
    KNOWN_SCOPE,
    database_state,
    seed_page_history,
)
from test_opportunities_api import (
    opportunities_client as _shared_client_fixture,
)

from app.analysis.data_quality import CODE_ORDER
from app.api.v1 import history
from app.db.session import get_session
from app.main import create_app
from app.models import PageMetricProvenance, SEOOpportunity, Site

ENDPOINT = "/api/v1/opportunities/prioritized"
prioritized_client = _shared_client_fixture
PRIORITY_FIELDS = {
    "priority_tier",
    "priority_rule_version",
    "priority_reason_code",
    "priority_message",
    "priority_inputs",
    "priority_thresholds",
}


def seed_traffic(engine, previous, current, **kwargs):
    return seed_page_history(engine, [{"clicks": previous}, {"clicks": current}], **kwargs)


def test_prioritized_tiers_preserve_exact_original_candidates(prioritized_client, gsc_engine):
    for name, previous, current in [("z-high", 20, 10), ("a-medium", 10, 5), ("b-low", 5, 2)]:
        seed_traffic(gsc_engine, previous, current, url=f"https://example.com/{name}")
    neutral_before = prioritized_client.get("/api/v1/opportunities").json()
    response = prioritized_client.get(ENDPOINT)
    assert response.status_code == 200
    payload = response.json()
    assert [item["priority_tier"] for item in payload["items"]] == ["high", "medium", "low"]
    assert [item["url"] for item in payload["items"]] == [
        "https://example.com/z-high",
        "https://example.com/a-medium",
        "https://example.com/b-low",
    ]
    original = {
        (item["page_id"], item["opportunity_type"]): item for item in neutral_before["items"]
    }
    for item in payload["items"]:
        stripped = {key: value for key, value in item.items() if key not in PRIORITY_FIELDS}
        assert stripped == original[(item["page_id"], item["opportunity_type"])]
        assert item["priority_rule_version"] == "priority-v1"
        assert " / " in item["priority_message"]
        assert set(item["priority_thresholds"]) == {"high", "medium"}
        assert isinstance(item["priority_inputs"]["clicks_percentage_change_numerator"], str)
        assert isinstance(item["priority_inputs"]["clicks_percentage_change_denominator"], str)
    assert prioritized_client.get("/api/v1/opportunities").json() == neutral_before
    assert payload["summary"] == {
        "analyzed_pages": 3,
        "eligible_pages": 3,
        "ineligible_pages": 0,
        "pages_with_candidates": 3,
        "ready_pages_without_candidates": 0,
        "detected_candidates": 3,
        "gate_reason_counts": dict.fromkeys(CODE_ORDER, 0),
    }


@pytest.mark.parametrize(
    ("opportunity_type", "tier", "previous", "current"),
    [
        (
            "ctr_opportunity",
            "high",
            {"impressions": 1000, "clicks": 100, "ctr": "0.1"},
            {"impressions": 1000, "clicks": 80, "ctr": "0.08"},
        ),
        (
            "ctr_opportunity",
            "medium",
            {"impressions": 200, "clicks": 20, "ctr": "0.1"},
            {"impressions": 200, "clicks": 18, "ctr": "0.09"},
        ),
        (
            "ctr_opportunity",
            "low",
            {"impressions": 100, "clicks": 10, "ctr": "0.1"},
            {"impressions": 100, "clicks": 9, "ctr": "0.09"},
        ),
        (
            "ranking_decline",
            "high",
            {"impressions": 500, "average_position": "5"},
            {"impressions": 500, "average_position": "9"},
        ),
        (
            "ranking_decline",
            "medium",
            {"impressions": 150, "average_position": "5"},
            {"impressions": 150, "average_position": "8"},
        ),
        (
            "ranking_decline",
            "low",
            {"impressions": 50, "average_position": "5"},
            {"impressions": 50, "average_position": "7"},
        ),
        (
            "impression_growth_gap",
            "high",
            {"impressions": 500, "clicks": 100, "ctr": "0.2"},
            {"impressions": 1000, "clicks": 100, "ctr": "0.1"},
        ),
        (
            "impression_growth_gap",
            "medium",
            {"impressions": 200, "clicks": 20, "ctr": "0.1"},
            {"impressions": 300, "clicks": 20, "ctr": "0.066667"},
        ),
        (
            "impression_growth_gap",
            "low",
            {"impressions": 100, "clicks": 10, "ctr": "0.1"},
            {"impressions": 150, "clicks": 10, "ctr": "0.066667"},
        ),
    ],
)
def test_all_signal_families_expose_each_tier_and_exact_inputs(
    prioritized_client, gsc_engine, opportunity_type, tier, previous, current
):
    definitions = [
        {key: Decimal(value) if isinstance(value, str) else value for key, value in fields.items()}
        for fields in (previous, current)
    ]
    seed_page_history(gsc_engine, definitions)
    payload = prioritized_client.get(ENDPOINT).json()
    candidate = next(
        item for item in payload["items"] if item["opportunity_type"] == opportunity_type
    )
    assert candidate["priority_tier"] == tier
    inputs = candidate["priority_inputs"]
    input_fields = (
        ("impressions", "average_position")
        if opportunity_type == "ranking_decline"
        else ("impressions", "ctr")
    )
    for side, fields in (("previous", previous), ("current", current)):
        for field in input_fields:
            value = fields[field]
            actual = inputs[f"{side}_{field}"]
            if isinstance(value, str):
                assert Decimal(actual) == Decimal(value)
            else:
                assert actual == value
    if "ctr" in previous:
        assert (
            Decimal(inputs["ctr_percentage_point_change"])
            == (Decimal(current["ctr"]) - Decimal(previous["ctr"])) * 100
        )
    if opportunity_type == "impression_growth_gap":
        assert inputs["impressions_percentage_change_numerator"] == str(
            (current["impressions"] - previous["impressions"]) * 100
        )
        assert inputs["impressions_percentage_change_denominator"] == str(previous["impressions"])


def test_display_rounding_never_promotes_an_actual_below_boundary_ratio(
    prioritized_client, gsc_engine
):
    seed_traffic(gsc_engine, 1_000_000_003, 700_000_003)
    payload = prioritized_client.get(ENDPOINT).json()
    candidate = payload["items"][0]
    assert candidate["evidence"]["changes"]["clicks_percentage_change"] == "-30.000000"
    assert candidate["priority_tier"] == "medium"
    assert candidate["priority_inputs"]["clicks_percentage_change_numerator"] == "-30000000000"
    assert candidate["priority_inputs"]["clicks_percentage_change_denominator"] == "1000000003"


def test_ratio_wire_strings_retain_integers_above_javascript_safe_range(
    prioritized_client, gsc_engine
):
    previous, current = 1_000_000_000_000_000, 1
    seed_traffic(gsc_engine, previous, current)
    candidate = prioritized_client.get(ENDPOINT).json()["items"][0]
    inputs = candidate["priority_inputs"]
    assert inputs["previous_clicks"] == previous
    assert inputs["current_clicks"] == current
    assert inputs["clicks_percentage_change_numerator"] == str((current - previous) * 100)
    assert inputs["clicks_percentage_change_denominator"] == str(previous)
    assert abs(int(inputs["clicks_percentage_change_numerator"])) > 2**53 - 1


def test_candidate_pagination_tier_filters_and_unfiltered_summary(prioritized_client, gsc_engine):
    page_id, _ = seed_page_history(
        gsc_engine,
        [{"clicks": 20}, {"clicks": 10, "average_position": Decimal("12")}],
        url="https://example.com/two-high",
    )
    seed_traffic(gsc_engine, 10, 5, url="https://example.com/medium")
    seed_traffic(gsc_engine, 5, 2, url="https://example.com/low")
    complete = prioritized_client.get(ENDPOINT).json()
    assert complete["total"] == 4
    assert complete["summary"]["pages_with_candidates"] == 3
    assert complete["summary"]["detected_candidates"] == 4
    assert [item["opportunity_type"] for item in complete["items"][:2]] == [
        "ranking_decline",
        "traffic_decline",
    ]
    assert {item["page_id"] for item in complete["items"][:2]} == {str(page_id)}
    paginated = []
    for page in range(1, 5):
        payload = prioritized_client.get(f"{ENDPOINT}?page={page}&page_size=1").json()
        assert payload["total"] == payload["total_pages"] == 4
        assert payload["summary"] == complete["summary"]
        paginated.extend(payload["items"])
    assert paginated == complete["items"]
    assert prioritized_client.get(f"{ENDPOINT}?page=5&page_size=1").json()["items"] == []
    for tier, count in [("high", 2), ("medium", 1), ("low", 1)]:
        payload = prioritized_client.get(f"{ENDPOINT}?priority_tier={tier}&page_size=1").json()
        assert payload["total"] == payload["total_pages"] == count
        assert payload["summary"] == complete["summary"]
        assert all(item["priority_tier"] == tier for item in payload["items"])
    assert prioritized_client.get(ENDPOINT).json() == complete


def test_site_filter_and_equal_url_uuid_ties(prioritized_client, gsc_engine):
    site_ids = [uuid4(), uuid4()]
    identifiers = ["sc-domain:example.com", "https://example.com/"]
    with Session(gsc_engine) as session:
        for site_id, identifier in zip(site_ids, identifiers, strict=True):
            session.add(Site(id=site_id, identifier=identifier, display_name=identifier))
        session.commit()
    page_ids = [UUID(int=20), UUID(int=10)]
    for site_id, page_id, identifier in zip(site_ids, page_ids, identifiers, strict=True):
        seed_traffic(
            gsc_engine,
            20,
            10,
            site_id=site_id,
            page_id=page_id,
            report_scope=KNOWN_SCOPE | {"property_id": identifier},
        )
    global_payload = prioritized_client.get(ENDPOINT).json()
    assert [item["page_id"] for item in global_payload["items"]] == [
        str(item) for item in sorted(page_ids)
    ]
    for site_id, page_id in zip(site_ids, page_ids, strict=True):
        payload = prioritized_client.get(f"{ENDPOINT}?site_id={site_id}&priority_tier=high").json()
        assert payload["total"] == payload["summary"]["analyzed_pages"] == 1
        assert payload["items"][0]["site_id"] == str(site_id)
        assert payload["items"][0]["page_id"] == str(page_id)
    missing_site = prioritized_client.get(f"{ENDPOINT}?site_id={uuid4()}").json()
    assert missing_site["items"] == []
    assert missing_site["summary"]["analyzed_pages"] == 0


def test_empty_result_distinguishes_absent_pages_ready_zero_and_tier_filter(
    prioritized_client, gsc_engine
):
    empty = prioritized_client.get(ENDPOINT).json()
    assert empty["items"] == []
    assert empty["summary"]["analyzed_pages"] == 0
    assert empty["total"] == empty["total_pages"] == 0
    seed_page_history(gsc_engine, [{}, {}])
    ready_zero = prioritized_client.get(ENDPOINT).json()
    assert ready_zero["items"] == []
    assert ready_zero["summary"]["eligible_pages"] == 1
    assert ready_zero["summary"]["ready_pages_without_candidates"] == 1
    assert ready_zero["summary"]["detected_candidates"] == 0
    seed_traffic(gsc_engine, 5, 2, url="https://example.com/low")
    filtered = prioritized_client.get(f"{ENDPOINT}?priority_tier=high").json()
    assert filtered["items"] == []
    assert filtered["total"] == 0
    assert filtered["summary"]["detected_candidates"] == 1
    assert filtered["summary"]["eligible_pages"] == 2


@pytest.mark.parametrize(
    ("definitions", "expected_codes"),
    [
        ([], {"insufficient_history"}),
        ([{}], {"insufficient_history"}),
        ([{"report_scope": None}, {"report_scope": None}], {"unknown_report_scope"}),
        (
            [{}, {"report_scope": KNOWN_SCOPE | {"search_type": "image"}}],
            {"insufficient_history", "incompatible_report_scope"},
        ),
        (
            [
                {},
                {
                    "coverage_status": "partial",
                    "observed_date_count": 3,
                    "dates_consecutive": False,
                },
            ],
            {"incomplete_date_coverage"},
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
            {"unknown_date_coverage"},
        ),
        ([{}, {"period_start": date(2026, 1, 8)}], {"overlapping_comparison_periods"}),
        ([{}, {"ctr": None}], {"missing_metrics"}),
        ([{"clicks": 0}, {}], {"zero_percentage_baseline"}),
        (
            [{"period_start": None}, {"period_start": None}],
            {"insufficient_history", "unknown_reporting_dates", "unknown_date_coverage"},
        ),
    ],
)
def test_ineligible_summary_reuses_original_quality_facts(
    prioritized_client, gsc_engine, definitions, expected_codes
):
    page_id, _ = seed_page_history(gsc_engine, definitions)
    original = prioritized_client.get(f"/api/v1/pages/{page_id}/opportunities").json()
    payload = prioritized_client.get(ENDPOINT).json()
    assert payload["items"] == []
    assert payload["summary"]["analyzed_pages"] == payload["summary"]["ineligible_pages"] == 1
    assert payload["summary"]["eligible_pages"] == 0
    counts = payload["summary"]["gate_reason_counts"]
    assert all(counts[code] == 1 for code in expected_codes)
    assert all(counts[code] == 1 for code in original["gate_reasons"])
    assert all(count <= 1 for count in counts.values())
    assert prioritized_client.get(f"/api/v1/pages/{page_id}/opportunities").json() == original


def test_summary_counts_overlap_without_blocking_ready_historical_caveats(
    prioritized_client, gsc_engine
):
    seed_page_history(
        gsc_engine,
        [
            {
                "report_scope": None,
                "coverage_status": "unknown",
                "observed_date_count": None,
                "dates_consecutive": None,
            },
            {},
            {"clicks": 10},
        ],
        url="https://example.com/ready",
    )
    seed_page_history(gsc_engine, [], url="https://example.com/none")
    seed_page_history(
        gsc_engine,
        [
            {"report_scope": None},
            {
                "report_scope": None,
                "coverage_status": "partial",
                "observed_date_count": 3,
                "dates_consecutive": False,
            },
        ],
        url="https://example.com/limited",
    )
    payload = prioritized_client.get(ENDPOINT).json()
    summary = payload["summary"]
    assert summary["analyzed_pages"] == 3
    assert summary["eligible_pages"] == summary["pages_with_candidates"] == 1
    assert summary["ineligible_pages"] == 2
    assert summary["detected_candidates"] == 1
    assert summary["gate_reason_counts"]["insufficient_history"] == 1
    assert summary["gate_reason_counts"]["unknown_report_scope"] == 1
    assert summary["gate_reason_counts"]["incomplete_date_coverage"] == 1
    assert summary["gate_reason_counts"]["unknown_date_coverage"] == 0


@pytest.mark.parametrize(
    "query",
    ["page=0", "page_size=0", "page_size=101", "site_id=invalid", "priority_tier=urgent"],
)
def test_invalid_query_does_not_read_database(isolated_settings, query):
    application = create_app()
    application.dependency_overrides[get_session] = lambda: None
    with TestClient(application) as client:
        assert client.get(f"{ENDPOINT}?{query}").status_code == 422


def test_database_failure_remains_generic(isolated_settings):
    application = create_app()

    class UnavailableSession:
        def scalars(self, *args, **kwargs):
            raise SQLAlchemyError("private database hostname")

    application.dependency_overrides[get_session] = lambda: UnavailableSession()
    with TestClient(application) as client:
        response = client.get(ENDPOINT)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "database_unavailable"
    assert "private database hostname" not in response.text


def test_grouped_history_reuses_two_reads_and_one_analysis_per_page(
    prioritized_client, gsc_engine, monkeypatch
):
    for number in range(5):
        seed_traffic(gsc_engine, 20, 10, url=f"https://example.com/{number}")
    statements = []
    counts = {"comparison": 0, "quality": 0, "detection": 0}
    original_compare = history.compare_performance
    original_quality = history.analyse_page_quality
    original_detection = history.analyse_page_opportunities

    def count_compare(*args, **kwargs):
        counts["comparison"] += 1
        return original_compare(*args, **kwargs)

    def count_quality(*args, **kwargs):
        counts["quality"] += 1
        return original_quality(*args, **kwargs)

    def count_detection(*args, **kwargs):
        counts["detection"] += 1
        return original_detection(*args, **kwargs)

    def record_statement(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    monkeypatch.setattr(history, "compare_performance", count_compare)
    monkeypatch.setattr(history, "analyse_page_quality", count_quality)
    monkeypatch.setattr(history, "analyse_page_opportunities", count_detection)
    event.listen(gsc_engine, "before_cursor_execute", record_statement)
    try:
        payload = prioritized_client.get(f"{ENDPOINT}?page_size=2").json()
    finally:
        event.remove(gsc_engine, "before_cursor_execute", record_statement)
    assert payload["total"] == 5
    assert len(statements) == 2
    assert counts == {"comparison": 5, "quality": 5, "detection": 5}


def test_read_only_requests_preserve_six_tables_and_never_call_external_services(
    prioritized_client, gsc_engine, monkeypatch
):
    page_id, snapshots = seed_traffic(gsc_engine, 20, 10)
    with Session(gsc_engine) as session:
        session.add(
            SEOOpportunity(
                page_id=page_id,
                opportunity_type="synthetic_existing_record",
                recommended_action="Reserved stored fixture",
                reason="Must remain untouched by prioritization",
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
        raise AssertionError("Runtime priorities must not call external services or AI")

    monkeypatch.setattr(socket.socket, "connect", prevent_external_connections)
    monkeypatch.setattr(socket.socket, "connect_ex", prevent_external_connections)
    event.listen(gsc_engine, "before_cursor_execute", record_statement)
    try:
        for path in [
            ENDPOINT,
            f"{ENDPOINT}?priority_tier=high&page_size=1",
            f"{ENDPOINT}?page=2&page_size=1",
            "/api/v1/opportunities",
            f"/api/v1/pages/{page_id}/opportunities",
        ]:
            assert prioritized_client.get(path).status_code == 200
        assert prioritized_client.post(ENDPOINT).status_code == 405
    finally:
        event.remove(gsc_engine, "before_cursor_execute", record_statement)
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    assert database_state(gsc_engine) == before
    assert len(before["seo_opportunities"]) == 1
