"""Describe compatible reporting periods without SEO scoring or recommendations.
描述兼容报告周期的变化，不进行 SEO 评分或推荐。
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import Any, Literal
from uuid import UUID

from app.normalization.report_scope import (
    ReportScope,
    canonical_scope_key,
    compare_report_scopes,
    unknown_scope,
)


@dataclass(frozen=True)
class PerformanceObservation:
    id: UUID
    page_id: UUID
    source: str
    source_type: str
    reporting_window: str
    period_start: date | None
    period_end: date | None
    imported_at: datetime
    clicks: int | None
    impressions: int | None
    ctr: Decimal | None
    average_position: Decimal | None
    report_scope: ReportScope | dict[str, Any] | None = None
    coverage_status: Literal["unknown", "partial", "complete"] = "unknown"
    observed_date_count: int | None = None
    dates_consecutive: bool | None = None


@dataclass(frozen=True)
class MetricChange:
    absolute_change: int | None
    percentage_change: Decimal | None


@dataclass(frozen=True)
class PerformanceComparison:
    previous_snapshot_id: UUID
    current_snapshot_id: UUID
    previous_period_start: date
    previous_period_end: date
    current_period_start: date
    current_period_end: date
    periods_overlap: bool
    clicks: MetricChange
    impressions: MetricChange
    ctr_percentage_point_change: Decimal | None
    average_position_change: Decimal | None
    previous_report_scope: ReportScope
    current_report_scope: ReportScope
    scope_compatibility: Literal["compatible", "unknown"]
    previous_coverage_status: Literal["unknown", "partial", "complete"]
    current_coverage_status: Literal["unknown", "partial", "complete"]
    previous_observed_date_count: int | None
    current_observed_date_count: int | None
    previous_dates_consecutive: bool | None
    current_dates_consecutive: bool | None


@dataclass(frozen=True)
class ScopeConflict:
    """Keep representative rejected evidence, without listing every conflicting snapshot pair.
    保留被拒绝的代表性证据，不枚举全部范围冲突快照对。
    """

    previous_snapshot_id: UUID
    current_snapshot_id: UUID
    dimensions: tuple[str, ...]


@dataclass(frozen=True)
class ComparisonOutcome:
    comparison: PerformanceComparison | None
    unavailable_reason: str | None
    scope_conflicts: tuple[ScopeConflict, ...] = ()


def _count_change(previous: int | None, current: int | None) -> MetricChange:
    """Preserve missing data and avoid percentage division by a zero baseline.
    保留缺失数据，并避免使用零基准进行百分比除法。
    """
    if previous is None or current is None:
        return MetricChange(None, None)
    absolute = current - previous
    if previous == 0:
        return MetricChange(absolute, None)
    with localcontext() as context:
        context.prec = 40
        percentage = (Decimal(absolute) / Decimal(previous) * Decimal(100)).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
    return MetricChange(absolute, percentage)


def _scope(observation: PerformanceObservation) -> ReportScope:
    if observation.report_scope is None:
        return unknown_scope()
    return ReportScope.model_validate(observation.report_scope)


def _revision_order(observation: PerformanceObservation) -> tuple[datetime, int]:
    return observation.imported_at, observation.id.int


def _pair_order(pair: tuple[PerformanceObservation, PerformanceObservation]) -> tuple:
    previous, current = pair
    return (
        current.period_end,
        current.period_start,
        current.imported_at,
        current.id.int,
        previous.period_end,
        previous.period_start,
        previous.imported_at,
        previous.id.int,
    )


def compare_performance(observations: Sequence[PerformanceObservation]) -> ComparisonOutcome:
    """Select the newest dated pair without treating unknown scope as proven compatibility.
    选择最新具有日期的快照对，不将未知范围当作已证明的兼容性。

    Revisions replace only the same period and canonical scope, preserving other scopes.
    修订仅替换相同周期与规范范围的记录，保留其他范围的证据。
    Each scope stream contributes its newest two periods; metric arithmetic remains separate.
    每个范围流仅提供其最新两个周期；指标计算仍与选择逻辑分离。
    """
    groups: dict[
        tuple[UUID, str, str, str, int],
        dict[str, dict[tuple[date, date], PerformanceObservation]],
    ] = defaultdict(lambda: defaultdict(dict))
    for observation in observations:
        start, end = observation.period_start, observation.period_end
        if start is None or end is None or end < start:
            continue
        group_key = (
            observation.page_id,
            observation.source,
            observation.source_type,
            observation.reporting_window,
            (end - start).days,
        )
        scope_key = canonical_scope_key(observation.report_scope)
        periods = groups[group_key][scope_key]
        previous_revision = periods.get((start, end))
        if previous_revision is None or _revision_order(observation) > _revision_order(
            previous_revision
        ):
            periods[(start, end)] = observation

    candidates: list[tuple[PerformanceObservation, PerformanceObservation]] = []
    conflicts: dict[tuple[str, ...], ScopeConflict] = {}

    def record_conflict(
        left: PerformanceObservation,
        right: PerformanceObservation,
        dimensions: tuple[str, ...],
    ) -> None:
        """Bound conflict output to factual dimension combinations and keep a stable witness.
        将冲突输出限制为事实维度组合，并保留稳定的证据记录。
        """
        previous, current = sorted(
            (left, right),
            key=lambda item: (
                item.period_end,
                item.period_start,
                item.imported_at,
                item.id.int,
            ),
        )
        witness = ScopeConflict(previous.id, current.id, dimensions)
        existing = conflicts.get(dimensions)
        if existing is None or (
            witness.current_snapshot_id.int,
            witness.previous_snapshot_id.int,
        ) > (
            existing.current_snapshot_id.int,
            existing.previous_snapshot_id.int,
        ):
            conflicts[dimensions] = witness

    for group_key in sorted(groups):
        streams = {}
        for scope_key, periods in sorted(groups[group_key].items()):
            ordered = sorted(periods, key=lambda period: (period[1], period[0]))
            streams[scope_key] = [periods[period] for period in ordered[-2:]]
            if len(ordered) >= 2:
                candidates.append((periods[ordered[-2]], periods[ordered[-1]]))

        # Known scopes can only match their own canonical stream, avoiding all-pairs scans.
        # 已知范围只能匹配自身规范范围流，避免枚举全部快照对。
        known = [items for items in streams.values() if _scope(items[-1]).status == "known"]
        if known:
            anchor = known[0][-1]
            for items in known[1:]:
                compatibility = compare_report_scopes(anchor.report_scope, items[-1].report_scope)
                if compatibility.status == "incompatible":
                    record_conflict(anchor, items[-1], compatibility.conflicts)

        for scope_key, items in streams.items():
            representative = items[-1]
            if _scope(representative).status == "known":
                continue
            partner_periods: dict[tuple[date, date], PerformanceObservation] = {}
            for other_key, others in streams.items():
                if other_key == scope_key:
                    continue
                compatibility = compare_report_scopes(
                    representative.report_scope, others[-1].report_scope
                )
                if compatibility.status == "incompatible":
                    record_conflict(representative, others[-1], compatibility.conflicts)
                    continue
                for partner in others:
                    period = partner.period_start, partner.period_end
                    existing = partner_periods.get(period)
                    if existing is None or _revision_order(partner) > _revision_order(existing):
                        partner_periods[period] = partner
                    if len(partner_periods) > 2:
                        oldest = min(partner_periods, key=lambda value: (value[1], value[0]))
                        del partner_periods[oldest]
            for item in items:
                for partner in partner_periods.values():
                    if (item.period_start, item.period_end) == (
                        partner.period_start,
                        partner.period_end,
                    ):
                        continue
                    previous, current = sorted(
                        (item, partner), key=lambda value: (value.period_end, value.period_start)
                    )
                    candidates.append((previous, current))
    scope_conflicts = tuple(conflicts[key] for key in sorted(conflicts))
    if not candidates:
        return ComparisonOutcome(
            comparison=None,
            unavailable_reason=(
                "Two distinct reporting periods with exact dates, the same page/source/window, "
                "equal duration, and no explicit report-scope conflict are required. / "
                "需要两个日期精确、页面与数据源及窗口相同、时长相等且无明确报告范围冲突的"
                "不同报告周期。"
            ),
            scope_conflicts=scope_conflicts,
        )
    previous, current = max(candidates, key=_pair_order)
    scope_compatibility = compare_report_scopes(previous.report_scope, current.report_scope)
    assert scope_compatibility.status != "incompatible"
    # Exact dates are established above; overlapping periods remain descriptive.
    # 上述逻辑已确认日期精确；重叠周期的比较仍仅为描述性信息。
    assert previous.period_start is not None and previous.period_end is not None
    assert current.period_start is not None and current.period_end is not None
    with localcontext() as context:
        context.prec = 40
        ctr_change = (
            (current.ctr - previous.ctr) * Decimal(100)
            if current.ctr is not None and previous.ctr is not None
            else None
        )
        position_change = (
            current.average_position - previous.average_position
            if current.average_position is not None and previous.average_position is not None
            else None
        )
    return ComparisonOutcome(
        comparison=PerformanceComparison(
            previous_snapshot_id=previous.id,
            current_snapshot_id=current.id,
            previous_period_start=previous.period_start,
            previous_period_end=previous.period_end,
            current_period_start=current.period_start,
            current_period_end=current.period_end,
            periods_overlap=(
                max(previous.period_start, current.period_start)
                <= min(previous.period_end, current.period_end)
            ),
            clicks=_count_change(previous.clicks, current.clicks),
            impressions=_count_change(previous.impressions, current.impressions),
            ctr_percentage_point_change=ctr_change,
            average_position_change=position_change,
            previous_report_scope=_scope(previous),
            current_report_scope=_scope(current),
            scope_compatibility=scope_compatibility.status,
            previous_coverage_status=previous.coverage_status,
            current_coverage_status=current.coverage_status,
            previous_observed_date_count=previous.observed_date_count,
            current_observed_date_count=current.observed_date_count,
            previous_dates_consecutive=previous.dates_consecutive,
            current_dates_consecutive=current.dates_consecutive,
        ),
        unavailable_reason=None,
        scope_conflicts=scope_conflicts,
    )
