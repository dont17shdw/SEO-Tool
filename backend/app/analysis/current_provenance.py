"""Validate recorded current-metric sources without inferring origin from equal values.
校验已记录的当前指标来源，不根据相同数值推断来源。
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from app.analysis.data_quality import QualityObservation
from app.analysis.performance_comparison import PerformanceObservation

METRIC_FIELDS = {
    "clicks_28d": "clicks",
    "impressions_28d": "impressions",
    "ctr": "ctr",
    "average_position": "average_position",
}
MetricValue = int | Decimal | None


@dataclass(frozen=True)
class RecordedMetricSource:
    page_id: UUID
    metric_name: str
    snapshot_id: UUID


@dataclass(frozen=True)
class MetricProvenance:
    metric_name: str
    current_value: MetricValue
    status: Literal["known", "unknown", "unavailable"]
    snapshot_id: UUID | None = None
    import_run_id: UUID | None = None
    period_start: date | None = None
    period_end: date | None = None
    imported_at: datetime | None = None


@dataclass(frozen=True)
class CurrentProvenance:
    page_id: UUID
    metrics: list[MetricProvenance]
    known_provenance_count: int
    unknown_provenance_count: int
    unavailable_metric_count: int
    all_known_metrics_share_one_snapshot: bool | None
    distinct_snapshot_ids: list[UUID]
    observations: list[QualityObservation]


def analyse_current_provenance(
    page_id: UUID,
    current_values: Mapping[str, MetricValue],
    observations: Sequence[PerformanceObservation],
    snapshot_import_ids: Mapping[UUID, UUID],
    recorded_sources: Sequence[RecordedMetricSource],
) -> CurrentProvenance:
    """Require an explicit, valid source link for each non-NULL current metric.
    为每个非 NULL 当前指标要求明确且有效的来源引用。

    Equality validates a recorded link; it never finds or fabricates a missing link.
    数值相等仅用于校验已记录引用，绝不寻找或编造缺失引用。
    Comparison readiness remains independent of current-state provenance.
    对比就绪度保持独立于当前状态来源追踪。
    """
    snapshots = {item.id: item for item in observations}
    links: dict[str, list[RecordedMetricSource]] = defaultdict(list)
    for source in recorded_sources:
        if source.page_id == page_id and source.metric_name in METRIC_FIELDS:
            links[source.metric_name].append(source)
    metrics: list[MetricProvenance] = []
    for metric_name, snapshot_field in METRIC_FIELDS.items():
        value = current_values.get(metric_name)
        if value is None:
            metrics.append(MetricProvenance(metric_name, None, "unavailable"))
            continue
        sources = links[metric_name]
        snapshot = snapshots.get(sources[0].snapshot_id) if len(sources) == 1 else None
        import_id = snapshot_import_ids.get(snapshot.id) if snapshot is not None else None
        supplied = getattr(snapshot, snapshot_field) if snapshot is not None else None
        if (
            snapshot is None
            or snapshot.page_id != page_id
            or import_id is None
            or supplied is None
            or supplied != value
        ):
            metrics.append(MetricProvenance(metric_name, value, "unknown"))
            continue
        metrics.append(
            MetricProvenance(
                metric_name=metric_name,
                current_value=value,
                status="known",
                snapshot_id=snapshot.id,
                import_run_id=import_id,
                period_start=snapshot.period_start,
                period_end=snapshot.period_end,
                imported_at=snapshot.imported_at,
            )
        )
    known = [item for item in metrics if item.status == "known"]
    unknown = [item for item in metrics if item.status == "unknown"]
    unavailable = [item for item in metrics if item.status == "unavailable"]
    snapshot_ids = sorted(
        {item.snapshot_id for item in known}, key=lambda identifier: identifier.int
    )
    quality: list[QualityObservation] = []
    if unknown:
        quality.append(
            QualityObservation(
                code="unknown_current_metric_provenance",
                severity="warning",
                scope="page",
                message=(
                    f"The source is unproven for {len(unknown)} current non-NULL metrics. / "
                    f"{len(unknown)} 个当前非空指标的来源尚未得到证明。"
                ),
                snapshot_ids=[],
                import_run_ids=[],
                evidence={
                    "metric_names": [item.metric_name for item in unknown],
                    "unknown_metric_count": len(unknown),
                },
            )
        )
    if len(snapshot_ids) >= 2:
        quality.append(
            QualityObservation(
                code="current_state_not_single_snapshot",
                severity="info",
                scope="page",
                message=(
                    "Current metrics are sourced from multiple snapshots. / 当前指标来自多个快照。"
                ),
                snapshot_ids=snapshot_ids,
                import_run_ids=sorted(
                    {item.import_run_id for item in known}, key=lambda identifier: identifier.int
                ),
                evidence={
                    "distinct_snapshot_count": len(snapshot_ids),
                    "metric_sources": [
                        {
                            "metric_name": item.metric_name,
                            "snapshot_id": str(item.snapshot_id),
                            "import_run_id": str(item.import_run_id),
                        }
                        for item in known
                    ],
                },
            )
        )
    return CurrentProvenance(
        page_id=page_id,
        metrics=metrics,
        known_provenance_count=len(known),
        unknown_provenance_count=len(unknown),
        unavailable_metric_count=len(unavailable),
        all_known_metrics_share_one_snapshot=(len(snapshot_ids) == 1 if known else None),
        distinct_snapshot_ids=snapshot_ids,
        observations=quality,
    )
