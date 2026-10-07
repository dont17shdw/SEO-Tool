from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext
from uuid import UUID

import pytest

from app.analysis.performance_comparison import PerformanceObservation, compare_performance


def observation(number=1, offset=0, duration=28, **changes):
    start = date(2026, 1, 1) + timedelta(days=offset)
    values = {
        "id": UUID(int=number),
        "page_id": UUID(int=100),
        "source": "gsc",
        "source_type": "pages_performance",
        "reporting_window": "latest_28_days",
        "period_start": start,
        "period_end": start + timedelta(days=duration - 1),
        "imported_at": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=number),
        "clicks": 20,
        "impressions": 500,
        "ctr": Decimal("0.025"),
        "average_position": Decimal("8"),
    }
    return PerformanceObservation(**(values | changes))


def test_descriptive_changes_use_percent_points_and_numeric_position_difference():
    previous = observation()
    current = observation(
        2,
        28,
        clicks=30,
        impressions=300,
        ctr=Decimal("0.04"),
        average_position=Decimal("4"),
    )
    result = compare_performance([current, previous])
    assert result.unavailable_reason is None
    comparison = result.comparison
    assert comparison.previous_snapshot_id == previous.id
    assert comparison.current_snapshot_id == current.id
    assert comparison.clicks.absolute_change == 10
    assert comparison.clicks.percentage_change == Decimal("50.000000")
    assert comparison.impressions.absolute_change == -200
    assert comparison.impressions.percentage_change == Decimal("-40.000000")
    assert comparison.ctr_percentage_point_change == Decimal("1.5")
    assert comparison.average_position_change == Decimal("-4")
    assert comparison.periods_overlap is False


@pytest.mark.parametrize("field", ["clicks", "impressions", "ctr", "average_position"])
@pytest.mark.parametrize("missing_side", ["previous", "current"])
def test_missing_metrics_do_not_fabricate_changes(field, missing_side):
    previous, current = observation(), observation(2, 28)
    if missing_side == "previous":
        previous = replace(previous, **{field: None})
    else:
        current = replace(current, **{field: None})
    comparison = compare_performance([previous, current]).comparison
    if field in {"clicks", "impressions"}:
        assert getattr(comparison, field).absolute_change is None
        assert getattr(comparison, field).percentage_change is None
    else:
        output = "ctr_percentage_point_change" if field == "ctr" else "average_position_change"
        assert getattr(comparison, output) is None


@pytest.mark.parametrize("current_count", [0, 20])
def test_zero_baseline_has_absolute_change_and_no_infinity(current_count):
    previous = observation(clicks=0, impressions=0)
    current = observation(2, 28, clicks=current_count, impressions=current_count)
    comparison = compare_performance([previous, current]).comparison
    assert comparison.clicks.absolute_change == current_count
    assert comparison.clicks.percentage_change is None
    assert comparison.impressions.absolute_change == current_count
    assert comparison.impressions.percentage_change is None


def test_percentage_rounding_is_deterministic_despite_external_decimal_context():
    previous = observation(clicks=3)
    current = observation(2, 28, clicks=4)
    with localcontext() as context:
        context.prec = 2
        comparison = compare_performance([previous, current]).comparison
    assert comparison.clicks.percentage_change == Decimal("33.333333")


@pytest.mark.parametrize(
    "difference",
    [
        {"page_id": UUID(int=101)},
        {"source": "another_source"},
        {"source_type": "another_type"},
        {"reporting_window": "latest_7_days"},
        {"period_end": date(2026, 2, 24)},
    ],
)
def test_incompatible_snapshots_are_not_compared(difference):
    result = compare_performance([observation(), observation(2, 28, **difference)])
    assert result.comparison is None
    assert result.unavailable_reason


def test_unknown_dates_same_period_and_insufficient_history_are_unavailable():
    for records in (
        [],
        [observation()],
        [observation(), observation(2)],
        [observation(), observation(2, 28, period_start=None, period_end=None)],
        [observation(), observation(2, 28, period_start=None)],
    ):
        outcome = compare_performance(records)
        assert outcome.comparison is None
        assert outcome.unavailable_reason


def test_latest_revision_of_each_distinct_period_is_used():
    old = observation(1, 0, clicks=10)
    revised = observation(4, 0, clicks=15)
    later_period = observation(2, 28, clicks=30)
    comparison = compare_performance([later_period, revised, old]).comparison
    assert comparison.previous_snapshot_id == revised.id
    assert comparison.current_snapshot_id == later_period.id
    assert comparison.clicks.absolute_change == 15


def test_newest_reporting_period_pair_is_independent_of_import_order():
    first_period = observation(4, 0)
    second_period = observation(2, 28)
    third_period = observation(1, 56)
    unknown_newest_import = observation(5, period_start=None, period_end=None)
    comparison = compare_performance(
        [unknown_newest_import, first_period, third_period, second_period]
    ).comparison
    assert comparison.previous_snapshot_id == second_period.id
    assert comparison.current_snapshot_id == third_period.id


def test_older_compatible_pair_remains_available_with_newer_incompatible_observation():
    previous = observation()
    current = observation(2, 28)
    incompatible_newest = observation(3, 56, duration=7)
    comparison = compare_performance([previous, current, incompatible_newest]).comparison
    assert comparison.previous_snapshot_id == previous.id
    assert comparison.current_snapshot_id == current.id


def test_overlapping_exact_periods_are_marked_without_judgment():
    comparison = compare_performance([observation(), observation(2, 7)]).comparison
    assert comparison.periods_overlap is True


def test_same_import_timestamp_revision_tie_uses_stable_id():
    previous = observation(1)
    revision = replace(previous, id=UUID(int=3), clicks=30)
    current = observation(2, 28)
    for records in ([previous, revision, current], [revision, current, previous]):
        comparison = compare_performance(records).comparison
        assert comparison.previous_snapshot_id == revision.id


def report_scope(*, property_id="sc-domain:example.com", search_type="web", filters=None):
    return {
        "property_id": property_id,
        "search_type": search_type,
        "filters": filters or [],
        "filters_complete": True,
    }


def test_known_matching_scope_exposes_compatible_scope_and_observed_coverage():
    scope = report_scope()
    previous = observation(
        report_scope=scope,
        coverage_status="complete",
        observed_date_count=28,
        dates_consecutive=True,
    )
    current = observation(
        2,
        28,
        report_scope=scope,
        coverage_status="partial",
        observed_date_count=3,
        dates_consecutive=False,
    )
    comparison = compare_performance([current, previous]).comparison
    assert comparison.scope_compatibility == "compatible"
    assert comparison.previous_report_scope.property_id == "sc-domain:example.com"
    assert comparison.current_report_scope.search_type == "web"
    assert comparison.previous_coverage_status == "complete"
    assert comparison.current_coverage_status == "partial"
    assert comparison.previous_observed_date_count == 28
    assert comparison.current_observed_date_count == 3
    assert comparison.previous_dates_consecutive is True
    assert comparison.current_dates_consecutive is False


@pytest.mark.parametrize(
    "scope",
    [
        report_scope(property_id="sc-domain:other.example"),
        report_scope(search_type="image"),
        report_scope(filters=[{"dimension": "device", "operator": "equals", "value": "mobile"}]),
        report_scope(filters=[{"dimension": "country", "operator": "equals", "value": "usa"}]),
    ],
)
def test_explicit_scope_conflict_never_forms_a_selected_pair(scope):
    previous = observation(report_scope=report_scope())
    current = observation(2, 28, report_scope=scope)
    outcome = compare_performance([previous, current])
    assert outcome.comparison is None
    assert outcome.unavailable_reason
    assert outcome.scope_conflicts
    assert outcome.scope_conflicts[0].previous_snapshot_id == previous.id
    assert outcome.scope_conflicts[0].current_snapshot_id == current.id


def test_unknown_legacy_scope_stays_descriptive_with_explicit_uncertainty():
    comparison = compare_performance([observation(), observation(2, 28)]).comparison
    assert comparison.scope_compatibility == "unknown"
    assert comparison.previous_report_scope.status == "unknown"
    assert comparison.current_report_scope.status == "unknown"
    assert comparison.previous_coverage_status == comparison.current_coverage_status == "unknown"


def test_incompatible_same_period_revision_does_not_erase_matching_revision():
    first = observation(report_scope=report_scope())
    matching = observation(2, 28, report_scope=report_scope(), clicks=40)
    unrelated_revision = observation(
        3,
        28,
        report_scope=report_scope(search_type="image"),
        clicks=900,
    )
    outcome = compare_performance([unrelated_revision, matching, first])
    assert outcome.comparison.previous_snapshot_id == first.id
    assert outcome.comparison.current_snapshot_id == matching.id
    assert outcome.comparison.clicks.absolute_change == 20
    assert outcome.scope_conflicts


def test_newest_incompatible_period_does_not_destroy_an_older_matching_pair():
    first = observation(report_scope=report_scope())
    second = observation(2, 28, report_scope=report_scope())
    newest = observation(3, 56, report_scope=report_scope(search_type="image"))
    outcome = compare_performance([first, newest, second])
    assert outcome.comparison.previous_snapshot_id == first.id
    assert outcome.comparison.current_snapshot_id == second.id


def test_unknown_partial_scope_searches_older_nonconflicting_partner():
    partial_scope = {
        "property_id": "sc-domain:example.com",
        "search_type": None,
        "filters": [],
        "filters_complete": False,
    }
    first = observation(report_scope=report_scope())
    newer_conflict = observation(
        2,
        28,
        report_scope=report_scope(property_id="sc-domain:other.example"),
    )
    current = observation(3, 56, report_scope=partial_scope)
    outcome = compare_performance([current, newer_conflict, first])
    assert outcome.comparison.previous_snapshot_id == first.id
    assert outcome.comparison.current_snapshot_id == current.id
    assert outcome.comparison.scope_compatibility == "unknown"


def test_large_known_scope_history_does_not_enumerate_snapshot_pairs(monkeypatch):
    import app.analysis.performance_comparison as module

    calls = 0
    original = module.compare_report_scopes

    def count_scope_checks(left, right):
        nonlocal calls
        calls += 1
        return original(left, right)

    monkeypatch.setattr(module, "compare_report_scopes", count_scope_checks)
    scopes = report_scope(), report_scope(search_type="image")
    records = [
        observation(number + 1, (number // 2) * 28, report_scope=scopes[number % 2])
        for number in range(10000)
    ]
    outcome = compare_performance(records)
    assert outcome.comparison.scope_compatibility == "compatible"
    assert calls < 10
