from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from app.analysis.current_provenance import RecordedMetricSource, analyse_current_provenance
from app.analysis.performance_comparison import PerformanceObservation

PAGE_ID = UUID(int=100)
METRIC_VALUES = {
    "clicks_28d": 20,
    "impressions_28d": 500,
    "ctr": Decimal("0.025"),
    "average_position": Decimal("8"),
}


def snapshot(number=1, **changes):
    values = {
        "id": UUID(int=number),
        "page_id": PAGE_ID,
        "source": "gsc",
        "source_type": "pages_performance",
        "reporting_window": "latest_28_days",
        "period_start": date(2026, 1, 1),
        "period_end": date(2026, 1, 28),
        "imported_at": datetime(2026, 2, number, tzinfo=UTC),
        "clicks": 20,
        "impressions": 500,
        "ctr": Decimal("0.025"),
        "average_position": Decimal("8"),
    }
    return PerformanceObservation(**(values | changes))


def links(snapshot_id=None):
    snapshot_id = snapshot_id if snapshot_id is not None else UUID(int=1)
    return [RecordedMetricSource(PAGE_ID, metric, snapshot_id) for metric in METRIC_VALUES]


def analyse(values=None, observations=None, recorded_sources=None, imports=None):
    observations = observations if observations is not None else [snapshot()]
    return analyse_current_provenance(
        page_id=PAGE_ID,
        current_values=METRIC_VALUES if values is None else values,
        observations=observations,
        snapshot_import_ids=(
            {item.id: UUID(int=1000 + item.id.int) for item in observations}
            if imports is None
            else imports
        ),
        recorded_sources=links() if recorded_sources is None else recorded_sources,
    )


def test_recorded_four_metric_sources_are_known_and_have_exact_metadata():
    result = analyse()
    assert [item.metric_name for item in result.metrics] == list(METRIC_VALUES)
    assert result.known_provenance_count == 4
    assert result.unknown_provenance_count == result.unavailable_metric_count == 0
    assert result.all_known_metrics_share_one_snapshot is True
    assert result.distinct_snapshot_ids == [UUID(int=1)]
    assert result.observations == []
    for metric in result.metrics:
        assert metric.current_value == METRIC_VALUES[metric.metric_name]
        assert metric.status == "known"
        assert metric.snapshot_id == UUID(int=1)
        assert metric.import_run_id == UUID(int=1001)
        assert metric.period_start == date(2026, 1, 1)
        assert metric.period_end == date(2026, 1, 28)
        assert metric.imported_at == datetime(2026, 2, 1, tzinfo=UTC)


def test_equal_historical_values_never_infer_unrecorded_provenance():
    result = analyse(observations=[snapshot(), snapshot(2)], recorded_sources=[])
    assert result.known_provenance_count == 0
    assert result.unknown_provenance_count == 4
    assert result.distinct_snapshot_ids == []
    assert result.all_known_metrics_share_one_snapshot is None
    assert [item.code for item in result.observations] == ["unknown_current_metric_provenance"]
    assert result.observations[0].severity == "warning"
    assert result.observations[0].evidence["metric_names"] == list(METRIC_VALUES)
    assert result.observations[0].snapshot_ids == []
    for item in result.metrics:
        assert item.status == "unknown"
        assert item.snapshot_id is item.import_run_id is item.imported_at is None


def test_null_current_values_are_unavailable_without_unknown_source_observation():
    result = analyse(values=dict.fromkeys(METRIC_VALUES), observations=[], recorded_sources=[])
    assert result.unavailable_metric_count == 4
    assert result.known_provenance_count == result.unknown_provenance_count == 0
    assert result.observations == []
    assert result.all_known_metrics_share_one_snapshot is None
    assert all(item.status == "unavailable" for item in result.metrics)


def test_partially_known_summary_only_describes_known_metrics():
    result = analyse(
        values={"clicks_28d": 20, "impressions_28d": 500},
        recorded_sources=[RecordedMetricSource(PAGE_ID, "clicks_28d", UUID(int=1))],
    )
    assert result.known_provenance_count == result.unknown_provenance_count == 1
    assert result.unavailable_metric_count == 2
    assert result.all_known_metrics_share_one_snapshot is True
    assert "current_state_not_single_snapshot" not in {item.code for item in result.observations}


def test_distinct_recorded_snapshot_ids_prove_mixed_current_state():
    recorded = [
        RecordedMetricSource(PAGE_ID, name, UUID(int=2) if name == "ctr" else UUID(int=1))
        for name in METRIC_VALUES
    ]
    for observations in ([snapshot(2), snapshot()], [snapshot(), snapshot(2)]):
        result = analyse(observations=observations, recorded_sources=list(reversed(recorded)))
        assert result.known_provenance_count == 4
        assert result.all_known_metrics_share_one_snapshot is False
        assert result.distinct_snapshot_ids == [UUID(int=1), UUID(int=2)]
        observation = result.observations[0]
        assert observation.code == "current_state_not_single_snapshot"
        assert observation.severity == "info"
        assert observation.scope == "page"
        assert observation.snapshot_ids == result.distinct_snapshot_ids
        assert observation.import_run_ids == [UUID(int=1001), UUID(int=1002)]
        assert observation.evidence["distinct_snapshot_count"] == 2


@pytest.mark.parametrize(
    "case",
    [
        "dangling_snapshot",
        "missing_import",
        "cross_page_link",
        "cross_page_snapshot",
        "unsupported",
    ],
)
def test_invalid_recorded_sources_remain_unknown(case):
    observations = [snapshot()]
    recorded = [RecordedMetricSource(PAGE_ID, "clicks_28d", UUID(int=1))]
    imports = {UUID(int=1): UUID(int=1001)}
    if case == "dangling_snapshot":
        recorded = [RecordedMetricSource(PAGE_ID, "clicks_28d", UUID(int=999))]
    elif case == "missing_import":
        imports = {}
    elif case == "cross_page_link":
        recorded = [RecordedMetricSource(UUID(int=101), "clicks_28d", UUID(int=1))]
    elif case == "cross_page_snapshot":
        observations = [snapshot(page_id=UUID(int=101))]
    else:
        recorded = [RecordedMetricSource(PAGE_ID, "clicks_7d", UUID(int=1))]
    result = analyse(
        values={"clicks_28d": 20},
        observations=observations,
        recorded_sources=recorded,
        imports=imports,
    )
    metric = result.metrics[0]
    assert metric.status == "unknown"
    assert metric.snapshot_id is metric.import_run_id is metric.imported_at is None
    assert result.all_known_metrics_share_one_snapshot is None


@pytest.mark.parametrize("observed_clicks", [None, 21])
def test_recorded_snapshot_must_have_the_current_non_null_metric_value(observed_clicks):
    result = analyse(observations=[snapshot(clicks=observed_clicks)])
    assert result.metrics[0].status == "unknown"
    assert result.known_provenance_count == 3
    assert result.unknown_provenance_count == 1
    assert result.observations[0].evidence["metric_names"] == ["clicks_28d"]


def test_manual_value_mismatch_does_not_expose_stale_source_metadata():
    result = analyse(values=METRIC_VALUES | {"clicks_28d": 123})
    metric = result.metrics[0]
    assert metric.current_value == 123
    assert metric.status == "unknown"
    assert metric.snapshot_id is metric.import_run_id is None
    assert metric.period_start is metric.period_end is metric.imported_at is None


def test_null_current_value_ignores_even_a_recorded_source():
    result = analyse(values=METRIC_VALUES | {"clicks_28d": None})
    metric = result.metrics[0]
    assert metric.status == "unavailable"
    assert metric.snapshot_id is metric.import_run_id is metric.imported_at is None
    assert result.unknown_provenance_count == 0
    assert result.observations == []


def test_zero_is_a_known_observation_not_an_unavailable_metric():
    result = analyse(values=METRIC_VALUES | {"clicks_28d": 0}, observations=[snapshot(clicks=0)])
    assert result.metrics[0].current_value == 0
    assert result.metrics[0].status == "known"
    assert result.unavailable_metric_count == 0


def test_known_source_can_have_unknown_reporting_dates():
    result = analyse(observations=[snapshot(period_start=None, period_end=None)])
    assert result.known_provenance_count == 4
    assert result.metrics[0].period_start is result.metrics[0].period_end is None
    assert result.metrics[0].imported_at is not None


def test_known_source_follows_explicit_applied_snapshot_not_newest_report_period():
    newer_report = snapshot(1, period_start=date(2026, 2, 1), period_end=date(2026, 2, 28))
    older_applied_later = snapshot(2)
    result = analyse(
        observations=[older_applied_later, newer_report], recorded_sources=links(UUID(int=2))
    )
    assert result.distinct_snapshot_ids == [older_applied_later.id]
    assert result.metrics[0].period_start == date(2026, 1, 1)


def test_ambiguous_multiple_recorded_links_do_not_choose_an_origin():
    recorded = links() + [RecordedMetricSource(PAGE_ID, "clicks_28d", UUID(int=2))]
    result = analyse(observations=[snapshot(), snapshot(2)], recorded_sources=recorded)
    assert result.metrics[0].status == "unknown"
    assert result.known_provenance_count == 3


def test_unknown_metrics_alone_do_not_prove_mixed_state_with_one_known_snapshot():
    result = analyse(
        observations=[snapshot(), replace(snapshot(2), clicks=42)],
        recorded_sources=[RecordedMetricSource(PAGE_ID, "clicks_28d", UUID(int=1))],
    )
    assert result.unknown_provenance_count == 3
    assert result.all_known_metrics_share_one_snapshot is True
    assert [item.code for item in result.observations] == ["unknown_current_metric_provenance"]
