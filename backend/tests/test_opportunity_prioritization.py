"""Check attention tiers using genuine Phase 7 candidates from synthetic ready evidence.
使用合成就绪证据产生的真实第七阶段候选检查关注等级。
"""

import ast
import inspect
from dataclasses import FrozenInstanceError, asdict, replace
from decimal import Decimal, Inexact, localcontext
from itertools import permutations
from uuid import UUID

import pytest
from test_opportunity_engine import analyse, observation

from app.analysis import opportunity_prioritization
from app.analysis.opportunity_prioritization import (
    DEFAULT_PRIORITY_CONFIG,
    prioritize_candidate,
    prioritize_candidates,
)


def candidate(opportunity_type, previous=None, current=None):
    """Run comparison, readiness, and original detection before prioritization.
    在优先级评估之前运行对比、就绪度及原始检测。
    """
    analysed, _, _ = analyse(
        [observation(**(previous or {})), observation(2, 28, **(current or {}))]
    )
    assert analysed.eligible
    return next(item for item in analysed.candidates if item.opportunity_type == opportunity_type)


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [
        (20, 10, "high"),
        (100, 70, "high"),
        (19, 9, "medium"),
        (25, 16, "medium"),
        (100, 71, "medium"),
        (10, 5, "medium"),
        (25, 20, "medium"),
        (9, 4, "low"),
        (15, 11, "low"),
        (5, 1, "low"),
    ],
)
def test_traffic_thresholds_are_inclusive_and_conjunctive(previous, current, expected):
    source = candidate("traffic_decline", {"clicks": previous}, {"clicks": current})
    assert prioritize_candidate(source).priority_tier == expected


@pytest.mark.parametrize(
    ("previous_impressions", "current_impressions", "current_ctr", "expected"),
    [
        (500, 500, "0.02", "high"),
        (499, 500, "0.02", "medium"),
        (500, 499, "0.02", "medium"),
        (500, 500, "0.020001", "medium"),
        (150, 150, "0.023", "medium"),
        (149, 150, "0.023", "low"),
        (150, 149, "0.023", "low"),
        (150, 150, "0.023001", "low"),
        (50, 50, "0.00", "low"),
    ],
)
def test_ctr_volume_and_percentage_point_boundaries(
    previous_impressions, current_impressions, current_ctr, expected
):
    source = candidate(
        "ctr_opportunity",
        {"impressions": previous_impressions},
        {"impressions": current_impressions, "ctr": Decimal(current_ctr)},
    )
    assert prioritize_candidate(source).priority_tier == expected


@pytest.mark.parametrize(
    ("previous_impressions", "current_impressions", "position", "expected"),
    [
        (500, 500, "8", "high"),
        (499, 500, "8", "medium"),
        (500, 499, "8", "medium"),
        (500, 500, "7.9999", "medium"),
        (150, 150, "7", "medium"),
        (149, 150, "7", "low"),
        (150, 149, "7", "low"),
        (150, 150, "6.9999", "low"),
        (50, 50, "100", "low"),
    ],
)
def test_ranking_volume_and_worsening_boundaries(
    previous_impressions, current_impressions, position, expected
):
    source = candidate(
        "ranking_decline",
        {"impressions": previous_impressions},
        {"impressions": current_impressions, "average_position": Decimal(position)},
    )
    assert prioritize_candidate(source).priority_tier == expected


@pytest.mark.parametrize(
    ("previous_impressions", "current_impressions", "current_ctr", "expected"),
    [
        (500, 750, "0.02", "high"),
        (499, 749, "0.02", "medium"),
        (1000, 1499, "0.02", "medium"),
        (500, 750, "0.020001", "medium"),
        (150, 203, "0.025", "medium"),
        (200, 270, "0.025", "medium"),
        (149, 202, "0.025", "low"),
        (200, 269, "0.025", "low"),
        (200, 270, "0.025001", "low"),
        (50, 500, "0.00", "low"),
    ],
)
def test_growth_volume_ratio_and_percentage_point_boundaries(
    previous_impressions, current_impressions, current_ctr, expected
):
    source = candidate(
        "impression_growth_gap",
        {"impressions": previous_impressions},
        {"impressions": current_impressions, "ctr": Decimal(current_ctr)},
    )
    assert prioritize_candidate(source).priority_tier == expected


@pytest.mark.parametrize(
    ("opportunity_type", "previous", "current", "expected", "display_field"),
    [
        (
            "traffic_decline",
            {"clicks": 1_000_000_000},
            {"clicks": 700_000_001},
            "medium",
            "clicks_percentage_change",
        ),
        (
            "impression_growth_gap",
            {"impressions": 1_000_000_000},
            {"impressions": 1_499_999_999, "ctr": Decimal("0.02")},
            "medium",
            "impressions_percentage_change",
        ),
        (
            "impression_growth_gap",
            {"impressions": 1_000_000_000},
            {"impressions": 1_349_999_999, "ctr": Decimal("0.025")},
            "low",
            "impressions_percentage_change",
        ),
    ],
)
def test_rounded_display_percentage_cannot_promote_a_tier(
    opportunity_type, previous, current, expected, display_field
):
    source = candidate(opportunity_type, previous, current)
    displayed = source.evidence["changes"][display_field]
    assert displayed in {Decimal("-30.000000"), Decimal("50.000000"), Decimal("35.000000")}
    prioritized = prioritize_candidate(source)
    assert prioritized.priority_tier == expected
    rounded = replace(
        source,
        evidence=source.evidence
        | {"changes": {key: Decimal("99999") for key in source.evidence["changes"]}},
    )
    assert prioritize_candidate(rounded).priority_tier == expected
    assert prioritize_candidate(rounded).priority_inputs == prioritized.priority_inputs


@pytest.mark.parametrize("opportunity_type", ["traffic_decline", "impression_growth_gap"])
def test_bigint_ratios_use_exact_integer_strings(opportunity_type):
    baseline = 9_000_000_000_000_000_000
    previous = (
        {"clicks": baseline}
        if opportunity_type == "traffic_decline"
        else {"impressions": baseline // 2}
    )
    current = (
        {"clicks": baseline * 7 // 10}
        if opportunity_type == "traffic_decline"
        else {
            "impressions": baseline * 3 // 4,
            "ctr": Decimal("0.02"),
        }
    )
    prioritized = prioritize_candidate(candidate(opportunity_type, previous, current))
    assert prioritized.priority_tier == "high"
    inputs = prioritized.priority_inputs
    metric = "clicks" if opportunity_type == "traffic_decline" else "impressions"
    assert inputs[f"{metric}_percentage_change_numerator"] == str(
        (current[metric] - previous[metric]) * 100
    )
    assert inputs[f"{metric}_percentage_change_denominator"] == str(previous[metric])
    assert isinstance(inputs[f"previous_{metric}"], int)


@pytest.mark.parametrize(
    ("opportunity_type", "previous", "current"),
    [
        ("traffic_decline", {"clicks": 25}, {"clicks": 16}),
        ("ctr_opportunity", {"impressions": 500}, {"impressions": 500, "ctr": Decimal("0.020001")}),
        (
            "ranking_decline",
            {"impressions": 500},
            {"impressions": 500, "average_position": Decimal("7.9999")},
        ),
        (
            "impression_growth_gap",
            {"impressions": 500},
            {"impressions": 750, "ctr": Decimal("0.020001")},
        ),
    ],
)
def test_priority_is_independent_of_external_decimal_precision_and_rounding_traps(
    opportunity_type, previous, current
):
    source = candidate(opportunity_type, previous, current)
    expected = prioritize_candidate(source)
    with localcontext() as context:
        context.prec = 2
        context.traps[Inexact] = True
        assert prioritize_candidate(source) == expected


def test_exact_ctr_and_position_changes_are_from_original_decimals():
    ctr = prioritize_candidate(
        candidate(
            "ctr_opportunity", {"impressions": 150}, {"impressions": 150, "ctr": Decimal("0.023")}
        )
    )
    assert ctr.priority_inputs == {
        "previous_impressions": 150,
        "current_impressions": 150,
        "previous_ctr": Decimal("0.03"),
        "current_ctr": Decimal("0.023"),
        "ctr_percentage_point_change": Decimal("-0.7"),
    }
    position = prioritize_candidate(
        candidate("ranking_decline", current={"average_position": Decimal("7.0001")})
    )
    assert position.priority_inputs["average_position_change"] == Decimal("3.0001")


def test_every_output_retains_all_original_evidence_and_both_threshold_maps():
    source = candidate("traffic_decline", {"clicks": 20}, {"clicks": 10})
    before = asdict(source)
    result = prioritize_candidate(source)
    assert result.candidate is source
    assert asdict(source) == before
    assert result.priority_rule_version == "priority-v1"
    assert result.priority_reason_code == "traffic_decline_high_thresholds_met"
    assert result.priority_thresholds == {
        "high": {
            "minimum_previous_clicks": 20,
            "minimum_click_loss": 10,
            "minimum_click_decline_percentage": Decimal("30"),
        },
        "medium": {
            "minimum_previous_clicks": 10,
            "minimum_click_loss": 5,
            "minimum_click_decline_percentage": Decimal("20"),
        },
    }
    assert "Clicks 20 → 10" in result.priority_message
    assert " / " in result.priority_message
    assert "点击数" in result.priority_message
    assert (
        not {"score", "confidence", "recommended_action", "expected_impact", "estimated_effort"}
        & asdict(result).keys()
    )


def test_low_explanation_discloses_unmet_higher_tiers_without_claiming_healthy_seo():
    result = prioritize_candidate(candidate("traffic_decline", {"clicks": 5}, {"clicks": 1}))
    assert result.priority_tier == "low"
    assert result.priority_reason_code == "traffic_decline_low_higher_tier_thresholds_not_met"
    assert "does not meet every medium-tier threshold" in result.priority_message
    assert set(result.priority_thresholds) == {"high", "medium"}
    assert "healthy" not in result.priority_message.lower()


def test_defaults_and_nested_thresholds_are_frozen_and_output_is_independent():
    with pytest.raises(FrozenInstanceError):
        DEFAULT_PRIORITY_CONFIG.version = "other"
    with pytest.raises(FrozenInstanceError):
        DEFAULT_PRIORITY_CONFIG.traffic_decline_high.minimum_click_loss = 1
    source = candidate("traffic_decline", {"clicks": 20}, {"clicks": 10})
    result = prioritize_candidate(source)
    result.priority_thresholds["high"]["minimum_click_loss"] = 0
    assert prioritize_candidate(source).priority_thresholds["high"]["minimum_click_loss"] == 10
    custom = replace(
        DEFAULT_PRIORITY_CONFIG,
        version="priority-test",
        traffic_decline_high=replace(
            DEFAULT_PRIORITY_CONFIG.traffic_decline_high, minimum_previous_clicks=21
        ),
    )
    customized = prioritize_candidate(source, custom)
    assert customized.priority_tier == "medium"
    assert customized.priority_rule_version == "priority-test"
    assert customized.priority_thresholds["high"]["minimum_previous_clicks"] == 21


def test_multiple_candidates_are_retained_with_tier_url_type_page_id_order():
    analysed, _, _ = analyse(
        [
            observation(impressions=500),
            observation(2, 28, clicks=10, average_position=Decimal("8"), impressions=500),
        ]
    )
    assert {item.opportunity_type for item in analysed.candidates} == {
        "traffic_decline",
        "ranking_decline",
    }
    original = tuple(analysed.candidates)
    high_a = replace(original[0], url="https://example.com/a", page_id=UUID(int=30))
    high_tie = replace(high_a, page_id=UUID(int=10))
    high_z = replace(original[1], url="https://example.com/z")
    low = replace(
        candidate("traffic_decline", {"clicks": 5}, {"clicks": 1}), url="https://example.com/0"
    )
    medium = replace(
        candidate("traffic_decline", {"clicks": 10}, {"clicks": 5}), url="https://example.com/0"
    )
    sources = [high_a, high_tie, high_z, low, medium]
    expected = prioritize_candidates(sources)
    assert [item.candidate for item in expected] == [high_tie, high_a, high_z, medium, low]
    for reordered in permutations(sources):
        assert prioritize_candidates(reordered) == expected
    assert tuple(analysed.candidates) == original
    assert len(expected) == len(sources)


def test_empty_input_and_eligible_no_signal_result_cannot_manufacture_candidates():
    result, _, _ = analyse([observation(), observation(2, 28)])
    assert result.eligible
    assert prioritize_candidates(result.candidates) == ()
    assert prioritize_candidates([]) == ()


def test_missing_or_invalid_input_is_not_inferred_from_descriptive_evidence():
    source = candidate("traffic_decline", {"clicks": 20}, {"clicks": 10})
    for malformed in ({}, {"clicks": -1}, {"clicks": True}, {"clicks": Decimal("20")}):
        invalid = replace(source, evidence=source.evidence | {"previous": malformed})
        with pytest.raises((ValueError, KeyError)):
            prioritize_candidate(invalid)


def test_priority_module_has_no_database_network_ai_or_evidence_gate_imports():
    tree = ast.parse(inspect.getsource(opportunity_prioritization))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add(node.module or "")
    assert not any(
        name.startswith(
            (
                "sqlalchemy",
                "httpx",
                "requests",
                "openai",
                "app.ai",
                "app.models",
                "app.analysis.data_quality",
                "app.analysis.performance_comparison",
            )
        )
        for name in modules
    )
