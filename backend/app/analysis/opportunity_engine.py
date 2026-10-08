"""Detect runtime factual signals from the existing selected comparison and readiness.
根据现有所选对比与就绪度检测运行时事实信号。

Candidates are evidence, not persisted decisions, scores, or recommended actions.
候选是证据，不是持久化决策、评分或建议行动。
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from app.analysis.data_quality import CODE_ORDER, PageQuality, QualityObservation
from app.analysis.performance_comparison import (
    ComparisonOutcome,
    MetricChange,
    PerformanceComparison,
    PerformanceObservation,
)

OpportunityType = Literal[
    "traffic_decline", "ctr_opportunity", "ranking_decline", "impression_growth_gap"
]
EvidenceValue = int | Decimal


@dataclass(frozen=True)
class OpportunityRuleConfig:
    """Centralize transparent v1 heuristics without claiming universal SEO thresholds.
    集中定义透明的第一版启发式规则，不宣称它们是通用 SEO 阈值。
    """

    traffic_minimum_previous_clicks: int = 5
    traffic_maximum_clicks_absolute_change: int = -3
    traffic_maximum_clicks_percentage_change: Decimal = Decimal("-20")
    ctr_minimum_impressions: int = 50
    ctr_maximum_percentage_point_change: Decimal = Decimal("-0.5")
    ctr_maximum_average_position_change: Decimal = Decimal("0.5")
    ctr_minimum_impressions_percentage_change: Decimal = Decimal("-10")
    ranking_minimum_impressions: int = 50
    ranking_minimum_average_position_change: Decimal = Decimal("2.0")
    ranking_minimum_current_impressions_exclusive: int = 0
    growth_minimum_impressions: int = 50
    growth_minimum_impressions_percentage_change: Decimal = Decimal("25")
    growth_maximum_clicks_percentage_change_exclusive: Decimal = Decimal("10")
    growth_maximum_ctr_percentage_point_change: Decimal = Decimal("-0.3")


DEFAULT_RULE_CONFIG = OpportunityRuleConfig()


@dataclass(frozen=True)
class OpportunityCandidate:
    """Retain the exact selected records, relevant metrics, and thresholds for audit.
    保留准确的所选记录、相关指标及阈值供审阅。
    """

    opportunity_type: OpportunityType
    page_id: UUID
    site_id: UUID | None
    url: str
    previous_snapshot_id: UUID
    current_snapshot_id: UUID
    previous_period_start: date
    previous_period_end: date
    current_period_start: date
    current_period_end: date
    evidence_readiness: Literal["ready"]
    scope_compatibility: Literal["compatible"]
    reason_code: str
    message: str
    evidence: dict[str, dict[str, EvidenceValue]]


@dataclass(frozen=True)
class PageOpportunityAnalysis:
    """Separate an unavailable evidence gate from an eligible result with no signals.
    区分不可用的证据门槛与合格但没有信号的结果。
    """

    page_id: UUID
    site_id: UUID | None
    url: str
    eligible: bool
    evidence_readiness: Literal["insufficient", "limited", "ready"]
    gate_reasons: tuple[str, ...]
    gate_observations: tuple[QualityObservation, ...]
    comparison: PerformanceComparison | None
    candidates: tuple[OpportunityCandidate, ...]


def _percentage_matches(
    change: MetricChange,
    previous: int | None,
    threshold: Decimal,
    operator: Literal["at_most", "at_least", "below"],
) -> bool:
    """Compare exact count ratios rather than rounding a percentage into a threshold.
    比较精确计数比率，而不是将百分比四舍五入后达到阈值。

    Phase 3's six-decimal percentage remains unchanged in descriptive evidence.
    第三阶段的六位小数百分比在描述性证据中保持不变。
    Integer cross multiplication is independent of the caller's Decimal context.
    整数交叉相乘不受调用方 Decimal 上下文影响。
    """
    if previous is None or previous <= 0 or change.absolute_change is None:
        return False
    if change.percentage_change is None:
        return False
    numerator, denominator = threshold.as_integer_ratio()
    actual = change.absolute_change * 100 * denominator
    boundary = previous * numerator
    if operator == "at_most":
        return actual <= boundary
    if operator == "at_least":
        return actual >= boundary
    return actual < boundary


def _gate_reasons(
    comparison: PerformanceComparison | None, quality: PageQuality
) -> tuple[str, ...]:
    """Consume selected readiness facts, keeping unrelated historical warnings independent.
    使用所选对比的就绪事实，使无关历史警告保持独立。
    """
    reasons = set(quality.readiness_reasons)
    if comparison is None:
        reasons.add("insufficient_history")
    else:
        if comparison.scope_compatibility != "compatible":
            reasons.add("unknown_report_scope")
        for side in ("previous", "current"):
            status = getattr(comparison, f"{side}_coverage_status")
            if status == "unknown":
                reasons.add("unknown_date_coverage")
            elif (
                status != "complete"
                or getattr(comparison, f"{side}_observed_date_count") != 28
                or getattr(comparison, f"{side}_dates_consecutive") is not True
                or (
                    getattr(comparison, f"{side}_period_end")
                    - getattr(comparison, f"{side}_period_start")
                ).days
                != 27
            ):
                reasons.add("incomplete_date_coverage")
        if comparison.periods_overlap:
            reasons.add("overlapping_comparison_periods")
    return tuple(sorted(reasons, key=CODE_ORDER.index))


def analyse_page_opportunities(
    *,
    page_id: UUID,
    site_id: UUID | None,
    url: str,
    observations: Sequence[PerformanceObservation],
    outcome: ComparisonOutcome,
    quality: PageQuality,
    config: OpportunityRuleConfig = DEFAULT_RULE_CONFIG,
) -> PageOpportunityAnalysis:
    """Apply four factual rules only to a ready, compatible, fully covered selected pair.
    仅对就绪、兼容且完整覆盖的所选快照对应用四项事实规则。

    The caller reuses Phase 3 comparison and Phase 4/6 readiness; no second pair is selected.
    调用方复用第三阶段对比及第四、六阶段就绪度；不另选第二组快照对。
    Current applied values and Phase 5 provenance are deliberately not rule inputs.
    当前应用值及第五阶段来源追踪明确不作为规则输入。
    """
    comparison = outcome.comparison
    reasons = _gate_reasons(comparison, quality)
    eligible = quality.readiness == "ready" and comparison is not None and not reasons
    candidates: list[OpportunityCandidate] = []
    if eligible:
        by_id = {item.id: item for item in observations}
        previous = by_id[comparison.previous_snapshot_id]
        current = by_id[comparison.current_snapshot_id]
        if previous.page_id != page_id or current.page_id != page_id:
            raise ValueError("Selected comparison observations must belong to the analysed page.")

        def add_candidate(
            opportunity_type: OpportunityType,
            reason_code: str,
            message: str,
            fields: tuple[str, ...],
            changes: dict[str, EvidenceValue],
            thresholds: dict[str, EvidenceValue],
        ) -> None:
            """Build one auditable candidate from the supplied selected snapshot pair.
            根据提供的所选快照对构建一个可审阅候选。
            """
            candidates.append(
                OpportunityCandidate(
                    opportunity_type=opportunity_type,
                    page_id=page_id,
                    site_id=site_id,
                    url=url,
                    previous_snapshot_id=comparison.previous_snapshot_id,
                    current_snapshot_id=comparison.current_snapshot_id,
                    previous_period_start=comparison.previous_period_start,
                    previous_period_end=comparison.previous_period_end,
                    current_period_start=comparison.current_period_start,
                    current_period_end=comparison.current_period_end,
                    evidence_readiness="ready",
                    scope_compatibility="compatible",
                    reason_code=reason_code,
                    message=message,
                    evidence={
                        "previous": {field: getattr(previous, field) for field in fields},
                        "current": {field: getattr(current, field) for field in fields},
                        "changes": changes,
                        "thresholds": thresholds,
                    },
                )
            )

        clicks_present = previous.clicks is not None and current.clicks is not None
        impressions_present = previous.impressions is not None and current.impressions is not None
        ctr_present = previous.ctr is not None and current.ctr is not None
        position_present = (
            previous.average_position is not None and current.average_position is not None
        )
        if (
            clicks_present
            and previous.clicks >= config.traffic_minimum_previous_clicks
            and comparison.clicks.absolute_change is not None
            and comparison.clicks.absolute_change <= config.traffic_maximum_clicks_absolute_change
            and _percentage_matches(
                comparison.clicks,
                previous.clicks,
                config.traffic_maximum_clicks_percentage_change,
                "at_most",
            )
        ):
            add_candidate(
                "traffic_decline",
                "clicks_decline_threshold_met",
                f"Clicks decreased from {previous.clicks} to {current.clicks} "
                f"({comparison.clicks.percentage_change}%) across the selected comparable "
                "periods. / "
                f"所选可比周期的点击次数从 {previous.clicks} 降至 {current.clicks}"
                f"（{comparison.clicks.percentage_change}%）。",
                ("clicks",),
                {
                    "clicks_absolute_change": comparison.clicks.absolute_change,
                    "clicks_percentage_change": comparison.clicks.percentage_change,
                },
                {
                    "minimum_previous_clicks": config.traffic_minimum_previous_clicks,
                    "maximum_clicks_absolute_change": config.traffic_maximum_clicks_absolute_change,
                    "maximum_clicks_percentage_change": (
                        config.traffic_maximum_clicks_percentage_change
                    ),
                },
            )
        if (
            impressions_present
            and ctr_present
            and position_present
            and previous.impressions >= config.ctr_minimum_impressions
            and current.impressions >= config.ctr_minimum_impressions
            and comparison.ctr_percentage_point_change is not None
            and comparison.ctr_percentage_point_change <= config.ctr_maximum_percentage_point_change
            and comparison.average_position_change is not None
            and comparison.average_position_change <= config.ctr_maximum_average_position_change
            and _percentage_matches(
                comparison.impressions,
                previous.impressions,
                config.ctr_minimum_impressions_percentage_change,
                "at_least",
            )
        ):
            add_candidate(
                "ctr_opportunity",
                "ctr_declined_with_comparable_visibility",
                f"CTR changed by {comparison.ctr_percentage_point_change} percentage points while "
                f"average position changed by {comparison.average_position_change} and impressions "
                f"by {comparison.impressions.percentage_change}% across the selected periods. / "
                f"所选周期的 CTR 变化为 {comparison.ctr_percentage_point_change} 个百分点，"
                f"同时平均排名变化为 {comparison.average_position_change}，"
                f"展示次数变化为 {comparison.impressions.percentage_change}%。",
                ("impressions", "ctr", "average_position"),
                {
                    "impressions_percentage_change": comparison.impressions.percentage_change,
                    "ctr_percentage_point_change": comparison.ctr_percentage_point_change,
                    "average_position_change": comparison.average_position_change,
                },
                {
                    "minimum_impressions": config.ctr_minimum_impressions,
                    "maximum_ctr_percentage_point_change": (
                        config.ctr_maximum_percentage_point_change
                    ),
                    "maximum_average_position_change": config.ctr_maximum_average_position_change,
                    "minimum_impressions_percentage_change": (
                        config.ctr_minimum_impressions_percentage_change
                    ),
                },
            )
        if (
            impressions_present
            and position_present
            and previous.impressions >= config.ranking_minimum_impressions
            and current.impressions >= config.ranking_minimum_impressions
            and current.impressions > config.ranking_minimum_current_impressions_exclusive
            and comparison.average_position_change is not None
            and comparison.average_position_change >= config.ranking_minimum_average_position_change
        ):
            add_candidate(
                "ranking_decline",
                "average_position_worsening_threshold_met",
                f"Average position worsened from {previous.average_position} to "
                f"{current.average_position} (+{comparison.average_position_change}) across the "
                f"selected comparable periods. / 所选可比周期的平均排名从 "
                f"{previous.average_position} 变为 {current.average_position}"
                f"（+{comparison.average_position_change}），排名变差。",
                ("impressions", "average_position"),
                {"average_position_change": comparison.average_position_change},
                {
                    "minimum_impressions": config.ranking_minimum_impressions,
                    "minimum_average_position_change": (
                        config.ranking_minimum_average_position_change
                    ),
                    "minimum_current_impressions_exclusive": (
                        config.ranking_minimum_current_impressions_exclusive
                    ),
                },
            )
        if (
            impressions_present
            and clicks_present
            and ctr_present
            and previous.impressions >= config.growth_minimum_impressions
            and current.impressions >= config.growth_minimum_impressions
            and comparison.ctr_percentage_point_change is not None
            and comparison.ctr_percentage_point_change
            <= config.growth_maximum_ctr_percentage_point_change
            and _percentage_matches(
                comparison.impressions,
                previous.impressions,
                config.growth_minimum_impressions_percentage_change,
                "at_least",
            )
            and _percentage_matches(
                comparison.clicks,
                previous.clicks,
                config.growth_maximum_clicks_percentage_change_exclusive,
                "below",
            )
        ):
            add_candidate(
                "impression_growth_gap",
                "impressions_grew_faster_than_clicks",
                f"Impressions changed by {comparison.impressions.percentage_change}% while clicks "
                f"changed by {comparison.clicks.percentage_change}% and CTR by "
                f"{comparison.ctr_percentage_point_change} percentage points across the selected "
                f"periods. / 所选周期的展示次数变化为 {comparison.impressions.percentage_change}%，"
                f"点击次数变化为 {comparison.clicks.percentage_change}%，"
                f"CTR 变化为 {comparison.ctr_percentage_point_change} 个百分点。",
                ("clicks", "impressions", "ctr"),
                {
                    "clicks_absolute_change": comparison.clicks.absolute_change,
                    "clicks_percentage_change": comparison.clicks.percentage_change,
                    "impressions_absolute_change": comparison.impressions.absolute_change,
                    "impressions_percentage_change": comparison.impressions.percentage_change,
                    "ctr_percentage_point_change": comparison.ctr_percentage_point_change,
                },
                {
                    "minimum_impressions": config.growth_minimum_impressions,
                    "minimum_impressions_percentage_change": (
                        config.growth_minimum_impressions_percentage_change
                    ),
                    "maximum_clicks_percentage_change_exclusive": (
                        config.growth_maximum_clicks_percentage_change_exclusive
                    ),
                    "maximum_ctr_percentage_point_change": (
                        config.growth_maximum_ctr_percentage_point_change
                    ),
                },
            )
    return PageOpportunityAnalysis(
        page_id=page_id,
        site_id=site_id,
        url=url,
        eligible=eligible,
        evidence_readiness=quality.readiness,
        gate_reasons=reasons,
        gate_observations=tuple(item for item in quality.observations if item.code in reasons),
        comparison=comparison,
        candidates=tuple(sorted(candidates, key=lambda item: item.opportunity_type)),
    )
