"""Exercise evidence readiness with synthetic history, without databases or external calls.
使用合成历史测试证据就绪状态，不使用数据库或外部调用。
"""

import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import permutations
from uuid import UUID

import pytest

from app.analysis.data_quality import ImportEvidence, analyse_import_quality, analyse_page_quality
from app.analysis.performance_comparison import (
    ComparisonOutcome,
    PerformanceObservation,
    compare_performance,
)


def snapshot(number: int, *, start: int | None = 0, days: int = 28, **fields):
    period_start = date(2026, 1, 1) + timedelta(days=start) if start is not None else None
    defaults = {
        "id": UUID(int=number),
        "page_id": UUID(int=100),
        "source": "gsc",
        "source_type": "pages_performance",
        "reporting_window": "latest_28_days",
        "period_start": period_start,
        "period_end": period_start + timedelta(days=days - 1) if period_start else None,
        "imported_at": datetime(2026, 4, 1, tzinfo=UTC) + timedelta(hours=number),
        "clicks": 10,
        "impressions": 100,
        "ctr": Decimal("0.100000"),
        "average_position": Decimal("5.0000"),
    }
    return PerformanceObservation(**(defaults | fields))


def quality(*items, outcome=None, import_ids=None):
    mapping = import_ids or {item.id: UUID(int=item.id.int + 1000) for item in items}
    return analyse_page_quality(items, outcome or compare_performance(items), mapping)


def by_code(result):
    return {item.code: item for item in result.observations}


def import_evidence(number: int, *, start: int | None = 0, days: int = 28, **fields):
    item = snapshot(number, start=start, days=days)
    defaults = {
        "id": item.id,
        "source": item.source,
        "source_type": item.source_type,
        "reporting_window": item.reporting_window,
        "period_start": item.period_start,
        "period_end": item.period_end,
        "imported_at": item.imported_at,
        "file_hash": f"{number:064x}",
    }
    return ImportEvidence(**(defaults | fields))


def test_no_history_is_insufficient_and_has_complete_zero_counts():
    result = quality()
    assert result.readiness == "insufficient"
    assert not result.comparison_exists
    assert result.selected_snapshot_ids == []
    assert result.readiness_reasons == ["insufficient_history"]
    assert all(count == 0 for count in result.counts.values())
    observation = by_code(result)["insufficient_history"]
    assert observation.severity == "blocking"
    assert observation.scope == "page"
    assert observation.snapshot_ids == observation.import_run_ids == []
    assert observation.evidence["comparison_unavailable_reason"]


def test_one_snapshot_is_insufficient_even_with_known_metrics_and_dates():
    item = snapshot(1)
    result = quality(item)
    assert result.readiness == "insufficient"
    assert result.counts["total_snapshots"] == 1
    assert result.counts["compatible_exact_periods"] == 1
    assert by_code(result)["insufficient_history"].snapshot_ids == [item.id]


def test_two_compatible_exact_periods_are_ready_without_caveats():
    previous, current = snapshot(1), snapshot(2, start=28)
    result = quality(previous, current)
    assert result.readiness == "ready"
    assert result.comparison_exists
    assert result.selected_snapshot_ids == [previous.id, current.id]
    assert result.observations == result.readiness_reasons == []
    assert result.counts == {
        "total_snapshots": 2,
        "exact_date_snapshots": 2,
        "unknown_date_snapshots": 0,
        "snapshots_with_missing_metrics": 0,
        "distinct_exact_periods": 2,
        "revision_periods": 0,
        "compatible_exact_periods": 2,
    }


@pytest.mark.parametrize("field", ["source", "source_type", "reporting_window", "page_id"])
def test_incompatible_history_does_not_establish_readiness(field):
    different = UUID(int=200) if field == "page_id" else "other"
    result = quality(snapshot(1), snapshot(2, start=28, **{field: different}))
    assert result.readiness == "insufficient"
    assert result.counts["distinct_exact_periods"] == 2
    assert result.counts["compatible_exact_periods"] == 1


def test_unequal_period_lengths_are_not_compatible():
    result = quality(snapshot(1), snapshot(2, start=28, days=7))
    assert result.readiness == "insufficient"
    assert result.counts["compatible_exact_periods"] == 1


def test_unknown_dates_are_explicit_and_never_inferred():
    unknown = snapshot(1, start=None)
    result = quality(unknown, snapshot(2))
    observation = by_code(result)["unknown_reporting_dates"]
    assert result.readiness == "insufficient"
    assert result.counts["unknown_date_snapshots"] == 1
    assert observation.severity == "warning"
    assert observation.snapshot_ids == [unknown.id]
    assert observation.evidence["snapshots"][0]["period_start"] is None
    assert observation.evidence["snapshots"][0]["period_end"] is None


@pytest.mark.parametrize("field", ["clicks", "impressions", "ctr", "average_position"])
@pytest.mark.parametrize("selected_side", ["previous", "current"])
def test_any_missing_selected_metric_limits_readiness(field, selected_side):
    previous, current = snapshot(1), snapshot(2, start=28)
    if selected_side == "previous":
        previous = replace(previous, **{field: None})
        missing = previous
    else:
        current = replace(current, **{field: None})
        missing = current
    result = quality(previous, current)
    assert result.readiness == "limited"
    assert result.readiness_reasons == ["missing_metrics"]
    assert by_code(result)["missing_metrics"].evidence["missing_fields_by_snapshot"] == {
        str(missing.id): [field]
    }


@pytest.mark.parametrize("field", ["clicks", "impressions"])
@pytest.mark.parametrize("current_value", [0, 20])
def test_known_zero_count_baseline_limits_percentage_readiness(field, current_value):
    previous = snapshot(1, **{field: 0})
    current = snapshot(2, start=28, **{field: current_value})
    result = quality(previous, current)
    assert result.readiness == "limited"
    assert result.readiness_reasons == ["zero_percentage_baseline"]
    assert by_code(result)["zero_percentage_baseline"].evidence["metrics"] == {
        field: {"previous": 0, "current": current_value}
    }


@pytest.mark.parametrize("field", ["clicks", "impressions"])
def test_zero_with_unknown_current_count_reports_missing_without_zero_baseline(field):
    result = quality(snapshot(1, **{field: 0}), snapshot(2, start=28, **{field: None}))
    assert result.readiness_reasons == ["missing_metrics"]
    assert "zero_percentage_baseline" not in by_code(result)


def test_zero_ctr_or_position_is_not_a_count_percentage_baseline():
    result = quality(
        snapshot(1, ctr=Decimal(0), average_position=Decimal(0)), snapshot(2, start=28)
    )
    assert result.readiness == "ready"
    assert "zero_percentage_baseline" not in by_code(result)


@pytest.mark.parametrize("start", [14, 27])
def test_selected_period_overlap_includes_a_shared_boundary_day(start):
    result = quality(snapshot(1), snapshot(2, start=start))
    observation = by_code(result)["overlapping_comparison_periods"]
    assert result.readiness == "limited"
    assert result.readiness_reasons == ["overlapping_comparison_periods"]
    assert (
        observation.evidence["overlap_start"]
        == (date(2026, 1, 1) + timedelta(days=start)).isoformat()
    )
    assert observation.evidence["overlap_end"] == "2026-01-28"


def test_same_period_revisions_are_informational_and_do_not_form_a_comparison():
    first, revision = snapshot(1), snapshot(2)
    result = quality(first, revision)
    assert result.readiness == "insufficient"
    assert result.counts["revision_periods"] == 1
    assert result.counts["distinct_exact_periods"] == 1
    observation = by_code(result)["same_period_revisions"]
    assert observation.severity == "info"
    assert observation.import_run_ids == [UUID(int=1001), UUID(int=1002)]


def test_latest_same_period_revision_alone_does_not_lower_ready_comparison():
    first, older_revision, latest_revision = (
        snapshot(1),
        snapshot(2, start=28),
        snapshot(3, start=28),
    )
    result = quality(first, older_revision, latest_revision)
    assert result.readiness == "ready"
    assert result.selected_snapshot_ids == [first.id, latest_revision.id]
    assert list(by_code(result)) == ["same_period_revisions"]


def test_missing_older_revision_does_not_lower_a_complete_selected_revision():
    first = snapshot(1)
    old_revision = snapshot(2, start=28, clicks=None)
    latest = snapshot(3, start=28)
    result = quality(first, old_revision, latest)
    assert result.readiness == "ready"
    assert "missing_metrics" in by_code(result)
    assert result.readiness_reasons == []


def test_same_period_snapshots_without_distinct_import_ids_are_not_called_revisions():
    items = snapshot(1), snapshot(2)
    result = quality(*items, import_ids={item.id: UUID(int=999) for item in items})
    assert result.counts["revision_periods"] == 0
    assert "same_period_revisions" not in by_code(result)


def test_an_older_selected_period_imported_later_limits_readiness_with_explicit_evidence():
    newer = snapshot(1, start=28)
    older = snapshot(2)
    result = quality(newer, older)
    assert result.readiness == "limited"
    assert result.readiness_reasons == ["out_of_order_import"]
    case = by_code(result)["out_of_order_import"].evidence["cases"][0]
    assert case["older_period_snapshot"]["snapshot_id"] == str(older.id)
    assert case["earlier_imported_newer_period"]["snapshot_id"] == str(newer.id)


def test_equal_import_timestamps_cannot_prove_out_of_order_chronology():
    timestamp = datetime(2026, 4, 1, tzinfo=UTC)
    result = quality(
        snapshot(1, start=28, imported_at=timestamp), snapshot(2, imported_at=timestamp)
    )
    assert result.readiness == "ready"
    assert "out_of_order_import" not in by_code(result)


def test_an_entire_timestamp_batch_is_inspected_before_it_can_become_a_witness():
    first = snapshot(1)
    same_time = datetime(2026, 4, 2, tzinfo=UTC)
    current = snapshot(2, start=56, imported_at=same_time)
    middle = snapshot(3, start=28, imported_at=same_time)
    result = quality(first, current, middle)
    assert result.readiness == "ready"
    assert "out_of_order_import" not in by_code(result)


def test_zero_baseline_in_unselected_older_history_does_not_lower_readiness():
    historical = snapshot(1, clicks=0, impressions=0)
    previous, current = snapshot(2, start=28), snapshot(3, start=56)
    result = quality(historical, previous, current)
    assert result.readiness == "ready"
    assert "zero_percentage_baseline" not in by_code(result)


def test_unknown_and_missing_history_outside_the_selected_pair_remain_visible_without_downgrade():
    unknown = snapshot(1, start=None, clicks=None)
    first, second = snapshot(2), snapshot(3, start=28)
    result = quality(unknown, first, second)
    assert result.readiness == "ready"
    assert result.selected_snapshot_ids == [first.id, second.id]
    assert set(by_code(result)) == {"unknown_reporting_dates", "missing_metrics"}


def test_historical_out_of_order_import_outside_selected_pair_does_not_lower_readiness():
    historical_newer, historical_older = snapshot(1, start=28), snapshot(2)
    selected_previous, selected_current = snapshot(3, start=56), snapshot(4, start=84)
    result = quality(historical_newer, historical_older, selected_previous, selected_current)
    assert result.readiness == "ready"
    assert result.selected_snapshot_ids == [selected_previous.id, selected_current.id]
    assert "out_of_order_import" in by_code(result)


def test_selected_chronology_witness_is_not_the_older_period_offender():
    previous, current = snapshot(1, start=28), snapshot(2, start=56)
    later_old = snapshot(3, start=0)
    result = quality(previous, current, later_old)
    assert result.readiness == "ready"
    assert result.selected_snapshot_ids == [previous.id, current.id]
    assert "out_of_order_import" in by_code(result)


@pytest.mark.parametrize("field", ["source", "source_type", "reporting_window", "page_id"])
def test_chronology_and_revisions_do_not_cross_evidence_contexts(field):
    different = UUID(int=200) if field == "page_id" else "other"
    result = quality(snapshot(1, start=28), snapshot(2, **{field: different}))
    assert "out_of_order_import" not in by_code(result)
    assert "same_period_revisions" not in by_code(result)


def test_quality_respects_supplied_unavailable_comparison_without_selecting_a_pair():
    result = quality(
        snapshot(1), snapshot(2, start=28), outcome=ComparisonOutcome(None, "Test context")
    )
    assert result.readiness == "insufficient"
    assert result.counts["compatible_exact_periods"] == 2
    assert (
        by_code(result)["insufficient_history"].evidence["comparison_unavailable_reason"]
        == "Test context"
    )


def test_quality_keeps_the_supplied_pair_instead_of_selecting_a_newer_pair():
    previous, current, newest = (
        snapshot(1),
        snapshot(2, start=28),
        snapshot(3, start=56, clicks=None),
    )
    selected_outcome = compare_performance([previous, current])
    result = quality(previous, current, newest, outcome=selected_outcome)
    assert result.selected_snapshot_ids == [previous.id, current.id]
    assert result.readiness == "ready"
    assert "missing_metrics" in by_code(result)


def test_all_observation_evidence_is_json_safe_bilingual_and_stable_under_input_order():
    items = snapshot(1, start=28, clicks=0), snapshot(2), snapshot(3, start=None, ctr=None)
    expected = quality(*items)
    for order in permutations(items):
        result = quality(*order)
        assert result == expected
        assert "current_state_not_single_snapshot" not in by_code(result)
        for observation in result.observations:
            json.dumps(observation.evidence)
            assert " / " in observation.message
            assert any("\u4e00" <= character <= "\u9fff" for character in observation.message)
            assert not any(
                term in observation.message.casefold()
                for term in ("good", "bad", "opportunity", "priority", "optimize", "action")
            )


def test_import_without_known_dates_has_a_target_only_warning():
    target = import_evidence(1, start=None)
    result = analyse_import_quality(target, [target, import_evidence(2)])
    assert result.counts["total_imports"] == 2
    assert result.counts["unknown_date_imports"] == 1
    observation = by_code(result)["unknown_reporting_dates"]
    assert observation.scope == "import"
    assert observation.snapshot_ids == []
    assert observation.import_run_ids == [target.id]
    assert observation.evidence["target"]["period_start"] is None


def test_known_import_does_not_inherit_another_runs_unknown_dates_warning():
    result = analyse_import_quality(import_evidence(1), [import_evidence(2, start=None)])
    assert result.counts["unknown_date_imports"] == 1
    assert "unknown_reporting_dates" not in by_code(result)


def test_import_revisions_require_different_hashes_and_same_exact_bounds():
    target, revision = import_evidence(1), import_evidence(2)
    retry = import_evidence(3, file_hash=target.file_hash)
    result = analyse_import_quality(target, [revision, retry])
    assert result.counts["same_period_revision_imports"] == 1
    observation = by_code(result)["same_period_revisions"]
    assert observation.severity == "info"
    assert observation.import_run_ids == [target.id, revision.id]
    assert "overlapping_reporting_periods" not in by_code(result)


def test_identical_file_retry_does_not_generate_import_observations():
    target = import_evidence(1)
    assert analyse_import_quality(target, [replace(target, id=UUID(int=2))]).observations == []


@pytest.mark.parametrize("start", [14, 27])
def test_import_overlap_is_inclusive_and_excludes_exact_period_revisions(start):
    target = import_evidence(1)
    revision, overlapping = import_evidence(2), import_evidence(3, start=start)
    result = analyse_import_quality(target, [revision, overlapping])
    assert result.counts["overlapping_imports"] == 1
    observation = by_code(result)["overlapping_reporting_periods"]
    assert observation.severity == "warning"
    assert observation.import_run_ids == [target.id, overlapping.id]


def test_import_adjacent_periods_do_not_overlap():
    result = analyse_import_quality(import_evidence(1), [import_evidence(2, start=28)])
    assert "overlapping_reporting_periods" not in by_code(result)


def test_import_chronology_requires_a_strictly_earlier_import_with_a_later_report_end():
    older = import_evidence(3)
    earlier_newer = import_evidence(1, start=28)
    same_timestamp = import_evidence(4, start=56, imported_at=older.imported_at)
    later_newer = import_evidence(5, start=84)
    result = analyse_import_quality(older, [earlier_newer, same_timestamp, later_newer])
    assert result.counts["earlier_imported_newer_periods"] == 1
    observation = by_code(result)["out_of_order_import"]
    assert observation.import_run_ids == [earlier_newer.id, older.id]
    assert observation.evidence["earlier_imported_newer_periods"][0]["import_run_id"] == str(
        earlier_newer.id
    )


def test_import_equal_timestamp_ties_are_not_out_of_order_evidence():
    target = import_evidence(2)
    newer = import_evidence(1, start=28, imported_at=target.imported_at)
    result = analyse_import_quality(target, [newer])
    assert "out_of_order_import" not in by_code(result)
    assert result.counts["earlier_imported_newer_periods"] == 0


@pytest.mark.parametrize("field", ["source", "source_type", "reporting_window"])
def test_import_checks_ignore_other_source_type_or_window_context(field):
    target = import_evidence(2)
    revision = import_evidence(3, **{field: "other"})
    newer = import_evidence(1, start=14, **{field: "other"})
    result = analyse_import_quality(target, [revision, newer])
    assert result.counts["total_imports"] == 1
    assert result.observations == []


def test_import_result_is_stable_deduplicates_context_ids_and_includes_the_target():
    target = import_evidence(3)
    runs = import_evidence(1, start=14), import_evidence(2)
    expected = analyse_import_quality(target, runs)
    for order in permutations(runs):
        result = analyse_import_quality(target, [*order, *order, target])
        assert result == expected
        for observation in result.observations:
            json.dumps(observation.evidence)
            assert " / " in observation.message
