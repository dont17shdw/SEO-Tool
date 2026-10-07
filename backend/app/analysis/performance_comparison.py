"""Describe compatible reporting periods without SEO scoring or recommendations.
描述兼容报告周期的变化，不进行 SEO 评分或推荐。
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, localcontext
from uuid import UUID


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


@dataclass(frozen=True)
class ComparisonOutcome:
    comparison: PerformanceComparison | None
    unavailable_reason: str | None


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


def compare_performance(observations: Sequence[PerformanceObservation]) -> ComparisonOutcome:
    """Select the newest compatible exact-period pair across all supplied history.
    从全部提供的历史记录中选择最新的兼容精确周期对。

    Latest imported revisions replace same-period revisions for selection only.
    选择时仅使用同一周期最新导入的修订版本。
    Import chronology and current stored page metrics are separate concepts.
    导入时间顺序与当前存储的页面指标属于不同概念。
    """
    groups: dict[
        tuple[UUID, str, str, str, int], dict[tuple[date, date], PerformanceObservation]
    ] = defaultdict(dict)
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
        previous_revision = groups[group_key].get((start, end))
        if previous_revision is None or (observation.imported_at, observation.id.int) > (
            previous_revision.imported_at,
            previous_revision.id.int,
        ):
            groups[group_key][(start, end)] = observation

    candidates: list[tuple[PerformanceObservation, PerformanceObservation]] = []
    for periods in groups.values():
        if len(periods) >= 2:
            ordered = sorted(periods, key=lambda period: (period[1], period[0]))
            candidates.append((periods[ordered[-2]], periods[ordered[-1]]))
    if not candidates:
        return ComparisonOutcome(
            comparison=None,
            unavailable_reason=(
                "Two distinct reporting periods with exact dates, the same page/source/window, "
                "and equal duration are required. / "
                "需要两个日期精确、页面与数据源及窗口相同、时长相等的不同报告周期。"
            ),
        )
    previous, current = max(
        candidates,
        key=lambda pair: (
            pair[1].period_end,
            pair[1].period_start,
            pair[1].imported_at,
            pair[1].id.int,
            pair[0].id.int,
        ),
    )
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
        ),
        unavailable_reason=None,
    )
