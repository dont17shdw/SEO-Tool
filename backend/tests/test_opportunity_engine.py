from dataclasses import FrozenInstanceError, asdict, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext
from uuid import UUID

import pytest

from app.analysis.current_provenance import analyse_current_provenance
from app.analysis.data_quality import analyse_page_quality
from app.analysis.opportunity_engine import (
    DEFAULT_RULE_CONFIG,
    OpportunityRuleConfig,
    analyse_page_opportunities,
)
from app.analysis.performance_comparison import PerformanceObservation, compare_performance

PAGE_ID = UUID(int=100)
SITE_ID = UUID(int=200)
PAGE_URL = "https://example.com/product/"
KNOWN_SCOPE = {
    "property_id": "sc-domain:example.com",
    "search_type": "web",
    "filters": [],
    "filters_complete": True,
}


def observation(number=1, offset=0, **changes):
    start = date(2026, 1, 1) + timedelta(days=offset)
    values = {
        "id": UUID(int=number),
        "page_id": PAGE_ID,
        "source": "gsc",
        "source_type": "pages_performance",
        "reporting_window": "latest_28_days",
        "period_start": start,
        "period_end": start + timedelta(days=27),
        "imported_at": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=number),
        "clicks": 20,
        "impressions": 100,
        "ctr": Decimal("0.03"),
        "average_position": Decimal("4"),
        "report_scope": KNOWN_SCOPE,
        "coverage_status": "complete",
        "observed_date_count": 28,
        "dates_consecutive": True,
    }
    return PerformanceObservation(**(values | changes))


def analyse(records, config=DEFAULT_RULE_CONFIG):
    outcome = compare_performance(records)
    quality = analyse_page_quality(records, outcome, {item.id: item.id for item in records})
    result = analyse_page_opportunities(
        page_id=PAGE_ID,
        site_id=SITE_ID,
        url=PAGE_URL,
        observations=records,
        outcome=outcome,
        quality=quality,
        config=config,
    )
    return result, outcome, quality


def types(result):
    return {item.opportunity_type for item in result.candidates}


def test_ready_compatible_complete_evidence_is_eligible_with_valid_empty_result():
    result, outcome, quality = analyse([observation(), observation(2, 28)])
    assert result.eligible is True
    assert result.evidence_readiness == "ready"
    assert result.gate_reasons == ()
    assert result.gate_observations == ()
    assert result.candidates == ()
    assert result.comparison is outcome.comparison
    assert quality.readiness == "ready"


@pytest.mark.parametrize("records", [[], [observation()]])
def test_insufficient_history_creates_no_candidates(records):
    result, _, quality = analyse(records)
    assert result.eligible is False
    assert result.evidence_readiness == quality.readiness == "insufficient"
    assert result.gate_reasons == ("insufficient_history",)
    assert result.gate_observations[0].code == "insufficient_history"
    assert result.candidates == ()


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"report_scope": None}, "unknown_report_scope"),
        (
            {"coverage_status": "partial", "observed_date_count": 3, "dates_consecutive": False},
            "incomplete_date_coverage",
        ),
        (
            {
                "coverage_status": "unknown",
                "observed_date_count": None,
                "dates_consecutive": None,
            },
            "unknown_date_coverage",
        ),
    ],
)
def test_selected_scope_and_coverage_caveats_block_all_candidates(side, changes, reason):
    previous, current = observation(), observation(2, 28, clicks=12)
    if side == "previous":
        previous = replace(previous, **changes)
    else:
        current = replace(current, **changes)
    result, _, quality = analyse([previous, current])
    assert result.eligible is False
    assert result.evidence_readiness == quality.readiness == "limited"
    assert reason in result.gate_reasons
    assert reason in {item.code for item in result.gate_observations}
    assert result.candidates == ()


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize("metric", ["clicks", "impressions", "ctr", "average_position"])
def test_any_selected_missing_metric_keeps_existing_conservative_readiness_gate(side, metric):
    previous = observation()
    current = observation(2, 28, clicks=12, average_position=Decimal("7"))
    if side == "previous":
        previous = replace(previous, **{metric: None})
    else:
        current = replace(current, **{metric: None})
    result, _, quality = analyse([previous, current])
    assert quality.readiness == "limited"
    assert result.eligible is False
    assert "missing_metrics" in result.gate_reasons
    assert result.candidates == ()


@pytest.mark.parametrize("metric", ["clicks", "impressions"])
def test_zero_previous_count_baseline_blocks_every_rule_via_existing_readiness(metric):
    previous = observation(**{metric: 0})
    current = observation(2, 28, average_position=Decimal("7"))
    result, _, _ = analyse([previous, current])
    assert result.eligible is False
    assert "zero_percentage_baseline" in result.gate_reasons
    assert result.candidates == ()


def test_overlap_and_selected_out_of_order_caveats_block_via_existing_readiness():
    for records, reason in (
        ([observation(), observation(2, 7, clicks=12)], "overlapping_comparison_periods"),
        ([observation(3), observation(2, 28, clicks=12)], "out_of_order_import"),
    ):
        result, _, quality = analyse(records)
        assert result.evidence_readiness == quality.readiness == "limited"
        assert result.eligible is False
        assert reason in result.gate_reasons
        assert result.candidates == ()


def test_explicit_incompatible_scope_creates_no_selected_comparison_or_candidates():
    current = observation(2, 28, report_scope=KNOWN_SCOPE | {"search_type": "image"}, clicks=12)
    result, outcome, _ = analyse([observation(), current])
    assert outcome.comparison is None
    assert outcome.scope_conflicts
    assert result.eligible is False
    assert result.candidates == ()


def test_historical_warnings_outside_selected_pair_do_not_block_ready_candidates():
    previous, current = observation(), observation(2, 28, clicks=12)
    legacy = observation(
        3,
        56,
        period_start=None,
        period_end=None,
        report_scope=None,
        coverage_status="unknown",
        observed_date_count=None,
        dates_consecutive=None,
        clicks=None,
    )
    result, _, quality = analyse([legacy, current, previous])
    assert quality.readiness == "ready"
    assert {"unknown_report_scope", "unknown_date_coverage", "missing_metrics"} <= {
        item.code for item in quality.observations
    }
    assert result.eligible is True
    assert result.gate_reasons == ()
    assert types(result) == {"traffic_decline"}


def test_same_period_revisions_preserve_ready_selected_candidate():
    old = observation(clicks=30)
    revision = observation(2, clicks=20)
    current = observation(3, 28, clicks=12)
    result, _, quality = analyse([old, revision, current])
    assert "same_period_revisions" in {item.code for item in quality.observations}
    assert result.eligible is True
    candidate = result.candidates[0]
    assert candidate.previous_snapshot_id == revision.id
    assert candidate.evidence["previous"]["clicks"] == 20


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [(15, 12, True), (5, 3, False), (16, 13, False), (4, 1, False), (20, 24, False)],
)
def test_traffic_decline_boundaries(previous, current, expected):
    result, _, _ = analyse([observation(clicks=previous), observation(2, 28, clicks=current)])
    assert ("traffic_decline" in types(result)) is expected


@pytest.mark.parametrize(
    ("current_ctr", "position", "impressions", "expected"),
    [
        ("0.025", "4.5", 90, True),
        ("0.025001", "4.5", 90, False),
        ("0.025", "4.5001", 90, False),
        ("0.025", "7", 100, False),
        ("0.025", "4", 89, False),
        ("0.025", "4", 49, False),
        ("0.030", "4", 100, False),
        ("0.035", "4", 100, False),
        ("0.025", "3", 100, True),
    ],
)
def test_ctr_opportunity_boundaries(current_ctr, position, impressions, expected):
    result, _, _ = analyse(
        [
            observation(),
            observation(
                2,
                28,
                ctr=Decimal(current_ctr),
                average_position=Decimal(position),
                impressions=impressions,
            ),
        ]
    )
    assert ("ctr_opportunity" in types(result)) is expected


def test_ctr_previous_impression_volume_minimum_is_required():
    result, _, _ = analyse([observation(impressions=49), observation(2, 28, ctr=Decimal("0.02"))])
    assert "ctr_opportunity" not in types(result)


@pytest.mark.parametrize(
    ("position", "previous_impressions", "current_impressions", "expected"),
    [
        ("6", 50, 50, True),
        ("5.9999", 100, 100, False),
        ("1", 100, 100, False),
        ("6", 49, 100, False),
        ("6", 100, 49, False),
        ("6", 100, 0, False),
    ],
)
def test_ranking_decline_boundaries(position, previous_impressions, current_impressions, expected):
    result, _, _ = analyse(
        [
            observation(impressions=previous_impressions),
            observation(
                2,
                28,
                impressions=current_impressions,
                average_position=Decimal(position),
            ),
        ]
    )
    assert ("ranking_decline" in types(result)) is expected


@pytest.mark.parametrize(
    ("previous_impressions", "current_impressions", "current_clicks", "ctr", "expected"),
    [
        (100, 125, 21, "0.027", True),
        (100000, 124999, 21, "0.027", False),
        (100, 125, 22, "0.027", False),
        (100, 125, 23, "0.027", False),
        (100, 125, 21, "0.027001", False),
        (100, 125, 21, "0.03", False),
        (49, 100, 21, "0.027", False),
    ],
)
def test_impression_growth_gap_boundaries(
    previous_impressions, current_impressions, current_clicks, ctr, expected
):
    result, _, _ = analyse(
        [
            observation(impressions=previous_impressions),
            observation(
                2,
                28,
                impressions=current_impressions,
                clicks=current_clicks,
                ctr=Decimal(ctr),
            ),
        ]
    )
    assert ("impression_growth_gap" in types(result)) is expected


def test_one_page_emits_multiple_unique_neutrally_ordered_candidates():
    result, _, _ = analyse(
        [observation(), observation(2, 28, clicks=12, average_position=Decimal("7"))]
    )
    assert types(result) == {"traffic_decline", "ranking_decline"}
    assert [item.opportunity_type for item in result.candidates] == [
        "ranking_decline",
        "traffic_decline",
    ]
    assert len(
        {
            (
                item.page_id,
                item.previous_snapshot_id,
                item.current_snapshot_id,
                item.opportunity_type,
            )
            for item in result.candidates
        }
    ) == len(result.candidates)


def test_three_independent_rules_can_emit_without_suppression():
    result, _, _ = analyse(
        [observation(), observation(2, 28, clicks=12, impressions=125, ctr=Decimal("0.02"))]
    )
    assert types(result) == {"traffic_decline", "ctr_opportunity", "impression_growth_gap"}


def test_traffic_and_ctr_exact_ratio_predicates_do_not_accept_rounded_boundary():
    traffic, outcome, _ = analyse(
        [observation(clicks=1_000_000_000), observation(2, 28, clicks=800_000_001)]
    )
    assert outcome.comparison.clicks.percentage_change == Decimal("-20.000000")
    assert "traffic_decline" not in types(traffic)
    ctr, outcome, _ = analyse(
        [
            observation(impressions=1_000_000_000),
            observation(2, 28, impressions=899_999_999, ctr=Decimal("0.02")),
        ]
    )
    assert outcome.comparison.impressions.percentage_change == Decimal("-10.000000")
    assert "ctr_opportunity" not in types(ctr)


def test_growth_exact_ratio_does_not_round_below_25_percent_into_a_candidate():
    result, outcome, _ = analyse(
        [
            observation(impressions=1_000_000_000),
            observation(2, 28, impressions=1_249_999_999, ctr=Decimal("0.02")),
        ]
    )
    assert outcome.comparison.impressions.percentage_change == Decimal("25.000000")
    assert "impression_growth_gap" not in types(result)


def test_growth_strict_click_boundary_uses_exact_ratio_even_when_display_rounds_to_ten():
    result, outcome, _ = analyse(
        [
            observation(clicks=1_000_000_000),
            observation(2, 28, clicks=1_099_999_999, impressions=125, ctr=Decimal("0.02")),
        ]
    )
    assert outcome.comparison.clicks.percentage_change == Decimal("10.000000")
    assert "impression_growth_gap" in types(result)


def test_rules_remain_exact_under_a_small_external_decimal_context_and_bigint_counts():
    records = [
        observation(clicks=9_000_000_000_000_000_000),
        observation(2, 28, clicks=7_200_000_000_000_000_000),
    ]
    normal, _, _ = analyse(records)
    with localcontext() as context:
        context.prec = 2
        limited_context, _, _ = analyse(records)
    assert normal == limited_context
    assert types(normal) == {"traffic_decline"}


def test_central_config_is_immutable_and_custom_thresholds_are_exposed():
    with pytest.raises(FrozenInstanceError):
        DEFAULT_RULE_CONFIG.traffic_minimum_previous_clicks = 6
    config = replace(OpportunityRuleConfig(), traffic_minimum_previous_clicks=10)
    result, _, _ = analyse([observation(clicks=5), observation(2, 28, clicks=0)], config)
    assert "traffic_decline" not in types(result)
    result, _, _ = analyse([observation(clicks=15), observation(2, 28, clicks=12)], config)
    assert result.candidates[0].evidence["thresholds"]["minimum_previous_clicks"] == 10


def test_candidate_exposes_relevant_metrics_ids_periods_and_factual_bilingual_message():
    previous, current = observation(), observation(2, 28, clicks=12)
    result, _, _ = analyse([previous, current])
    candidate = result.candidates[0]
    assert candidate.page_id == PAGE_ID
    assert candidate.site_id == SITE_ID
    assert candidate.url == PAGE_URL
    assert candidate.previous_snapshot_id == previous.id
    assert candidate.current_snapshot_id == current.id
    assert candidate.previous_period_start == previous.period_start
    assert candidate.current_period_end == current.period_end
    assert candidate.evidence_readiness == "ready"
    assert candidate.scope_compatibility == "compatible"
    assert candidate.reason_code == "clicks_decline_threshold_met"
    assert "Clicks decreased from 20 to 12" in candidate.message
    assert "点击次数" in candidate.message
    assert candidate.evidence == {
        "previous": {"clicks": 20},
        "current": {"clicks": 12},
        "changes": {"clicks_absolute_change": -8, "clicks_percentage_change": Decimal("-40")},
        "thresholds": {
            "minimum_previous_clicks": 5,
            "maximum_clicks_absolute_change": -3,
            "maximum_clicks_percentage_change": Decimal("-20"),
        },
    }
    assert (
        not {
            "opportunity_score",
            "priority",
            "recommended_action",
            "confidence",
            "expected_impact",
            "estimated_effort",
            "risk_level",
            "severity",
        }
        & asdict(candidate).keys()
    )
    with pytest.raises(FrozenInstanceError):
        candidate.opportunity_type = "ranking_decline"


def test_engine_preserves_supplied_comparison_quality_and_independent_unknown_provenance():
    records = [observation(), observation(2, 28, clicks=12)]
    outcome = compare_performance(records)
    quality = analyse_page_quality(records, outcome, {item.id: item.id for item in records})
    before = (asdict(outcome), asdict(quality), [asdict(item) for item in records])
    provenance = analyse_current_provenance(
        PAGE_ID,
        {
            "clicks_28d": 999,
            "impressions_28d": 999,
            "ctr": Decimal("0.9"),
            "average_position": Decimal("99"),
        },
        records,
        {item.id: item.id for item in records},
        [],
    )
    assert provenance.unknown_provenance_count == 4
    result = analyse_page_opportunities(
        page_id=PAGE_ID,
        site_id=None,
        url=PAGE_URL,
        observations=records,
        outcome=outcome,
        quality=quality,
    )
    assert result.eligible is True
    assert result.candidates[0].site_id is None
    assert result.candidates[0].evidence["current"]["clicks"] == 12
    assert before == (asdict(outcome), asdict(quality), [asdict(item) for item in records])


def test_missing_specific_rule_inputs_never_create_a_candidate_even_with_invalid_ready_input():
    records = [observation(), observation(2, 28, clicks=12)]
    outcome = compare_performance(records)
    quality = analyse_page_quality(records, outcome, {item.id: item.id for item in records})
    malformed = [replace(item, clicks=None) for item in records]
    result = analyse_page_opportunities(
        page_id=PAGE_ID,
        site_id=SITE_ID,
        url=PAGE_URL,
        observations=malformed,
        outcome=outcome,
        quality=quality,
    )
    assert "traffic_decline" not in types(result)


def test_engine_has_no_database_ai_or_external_service_imports():
    import ast
    import inspect

    from app.analysis import opportunity_engine

    tree = ast.parse(inspect.getsource(opportunity_engine))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add(node.module or "")
    assert not any(
        name.startswith(("sqlalchemy", "httpx", "requests", "openai", "app.ai", "app.models"))
        for name in modules
    )
