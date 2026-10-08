"""Assign transparent attention tiers only to existing runtime opportunity candidates.
仅为已有运行时机会候选分配透明的关注等级。

Detection, evidence eligibility, source records, and persistence remain upstream concerns.
检测、证据资格、来源记录及持久化仍属于上游职责。
"""

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from decimal import Context, Decimal, localcontext
from typing import Literal

from app.analysis.opportunity_engine import EvidenceValue, OpportunityCandidate

PriorityTier = Literal["high", "medium", "low"]
PriorityInput = int | Decimal | str
PRIORITY_TIER_ORDER = ("high", "medium", "low")


@dataclass(frozen=True)
class TrafficPriorityThresholds:
    minimum_previous_clicks: int
    minimum_click_loss: int
    minimum_click_decline_percentage: Decimal


@dataclass(frozen=True)
class CtrPriorityThresholds:
    minimum_impressions: int
    minimum_ctr_decline_percentage_points: Decimal


@dataclass(frozen=True)
class RankingPriorityThresholds:
    minimum_impressions: int
    minimum_average_position_worsening: Decimal


@dataclass(frozen=True)
class GrowthPriorityThresholds:
    minimum_impressions: int
    minimum_impressions_growth_percentage: Decimal
    minimum_ctr_decline_percentage_points: Decimal


@dataclass(frozen=True)
class OpportunityPriorityConfig:
    """Keep preliminary v1 heuristics immutable, including each nested threshold set.
    将初步第一版启发式规则设为不可变，包括每组嵌套阈值。

    Tiers describe attention to measured signals, not commercial value or confidence.
    等级描述对已测量信号的关注程度，不表示商业价值或置信度。
    """

    version: str = "priority-v1"
    traffic_decline_high: TrafficPriorityThresholds = TrafficPriorityThresholds(
        20, 10, Decimal("30")
    )
    traffic_decline_medium: TrafficPriorityThresholds = TrafficPriorityThresholds(
        10, 5, Decimal("20")
    )
    ctr_opportunity_high: CtrPriorityThresholds = CtrPriorityThresholds(500, Decimal("1"))
    ctr_opportunity_medium: CtrPriorityThresholds = CtrPriorityThresholds(150, Decimal("0.7"))
    ranking_decline_high: RankingPriorityThresholds = RankingPriorityThresholds(500, Decimal("4"))
    ranking_decline_medium: RankingPriorityThresholds = RankingPriorityThresholds(150, Decimal("3"))
    impression_growth_gap_high: GrowthPriorityThresholds = GrowthPriorityThresholds(
        500, Decimal("50"), Decimal("1")
    )
    impression_growth_gap_medium: GrowthPriorityThresholds = GrowthPriorityThresholds(
        150, Decimal("35"), Decimal("0.5")
    )


DEFAULT_PRIORITY_CONFIG = OpportunityPriorityConfig()


@dataclass(frozen=True)
class PrioritizedOpportunityCandidate:
    """Retain the original candidate and expose the exact tier inputs and both threshold sets.
    保留原始候选，并公开准确的等级输入及两组阈值。
    """

    candidate: OpportunityCandidate
    priority_tier: PriorityTier
    priority_rule_version: str
    priority_reason_code: str
    priority_message: str
    priority_inputs: dict[str, PriorityInput]
    priority_thresholds: dict[str, dict[str, EvidenceValue]]


def _count(value: EvidenceValue) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Priority count inputs must be nonnegative integers.")
    return value


def _decimal(value: EvidenceValue) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, int | Decimal):
        raise ValueError("Priority decimal inputs must be finite normalized numbers.")
    result = Decimal(value)
    if not result.is_finite() or result < 0:
        raise ValueError("Priority decimal inputs must be finite normalized numbers.")
    return result


def _exact_change(previous: Decimal, current: Decimal, *, scale: int = 1) -> Decimal:
    """Subtract original finite decimals with sufficient precision and an independent context.
    使用足够精度及独立上下文对原始有限小数做减法。

    Dynamic precision preserves small differences without inheriting caller rounding/traps.
    动态精度保留细小差异，不继承调用方的舍入或异常设置。
    """
    precision = (
        max(previous.adjusted(), current.adjusted(), 0)
        - min(previous.as_tuple().exponent, current.as_tuple().exponent, 0)
        + len(str(scale))
        + 2
    )
    with localcontext(Context(prec=precision)):
        return (current - previous) * scale


def _inputs(candidate: OpportunityCandidate) -> dict[str, PriorityInput]:
    """Read original measurements rather than rounded descriptive comparison percentages.
    读取原始测量值，不读取已舍入的描述性比较百分比。

    Exact integer ratio strings survive JSON and JavaScript without losing integer precision.
    精确整数比字符串经过 JSON 及 JavaScript 后不会丢失整数精度。
    """
    previous, current = candidate.evidence["previous"], candidate.evidence["current"]
    inputs: dict[str, PriorityInput] = {}
    if candidate.opportunity_type == "traffic_decline":
        first, second = _count(previous["clicks"]), _count(current["clicks"])
        if first <= 0:
            raise ValueError("An existing traffic candidate must have a positive count baseline.")
        inputs.update(
            previous_clicks=first,
            current_clicks=second,
            clicks_absolute_change=second - first,
            clicks_percentage_change_numerator=str((second - first) * 100),
            clicks_percentage_change_denominator=str(first),
        )
    else:
        first = _count(previous["impressions"])
        second = _count(current["impressions"])
        inputs.update(previous_impressions=first, current_impressions=second)
        if candidate.opportunity_type == "impression_growth_gap":
            if first <= 0:
                raise ValueError("An existing growth candidate must have a positive baseline.")
            inputs.update(
                impressions_absolute_change=second - first,
                impressions_percentage_change_numerator=str((second - first) * 100),
                impressions_percentage_change_denominator=str(first),
            )
        if candidate.opportunity_type in {"ctr_opportunity", "impression_growth_gap"}:
            first_ctr, second_ctr = _decimal(previous["ctr"]), _decimal(current["ctr"])
            if first_ctr > 1 or second_ctr > 1:
                raise ValueError("Normalized CTR must remain a fraction between zero and one.")
            inputs.update(
                previous_ctr=first_ctr,
                current_ctr=second_ctr,
                ctr_percentage_point_change=_exact_change(first_ctr, second_ctr, scale=100),
            )
        if candidate.opportunity_type == "ranking_decline":
            first_position = _decimal(previous["average_position"])
            second_position = _decimal(current["average_position"])
            inputs.update(
                previous_average_position=first_position,
                current_average_position=second_position,
                average_position_change=_exact_change(first_position, second_position),
            )
    return inputs


def _ratio_at_least(numerator: int, denominator: int, threshold: Decimal) -> bool:
    """Compare exact percentage ratios by integer cross multiplication, with inclusive bounds.
    使用整数交叉相乘比较精确百分比比率，边界包含等号。
    """
    boundary_numerator, boundary_denominator = threshold.as_integer_ratio()
    return numerator * boundary_denominator >= denominator * boundary_numerator


def _matches(
    opportunity_type: str,
    inputs: dict[str, PriorityInput],
    thresholds: dict[str, EvidenceValue],
) -> bool:
    """Require every predicate in one tier; upstream detection predicates remain unchanged.
    要求同一等级的全部谓词成立；上游检测谓词保持不变。
    """
    if opportunity_type == "traffic_decline":
        return (
            inputs["previous_clicks"] >= thresholds["minimum_previous_clicks"]
            and -inputs["clicks_absolute_change"] >= thresholds["minimum_click_loss"]
            and _ratio_at_least(
                -int(inputs["clicks_percentage_change_numerator"]),
                int(inputs["clicks_percentage_change_denominator"]),
                thresholds["minimum_click_decline_percentage"],
            )
        )
    if (
        min(inputs["previous_impressions"], inputs["current_impressions"])
        < thresholds["minimum_impressions"]
    ):
        return False
    if opportunity_type == "ranking_decline":
        return inputs["average_position_change"] >= thresholds["minimum_average_position_worsening"]
    # copy_negate is exact; unary Decimal negation can inherit ambient rounding.
    # copy_negate 保持精确；Decimal 一元取负可能继承外部舍入。
    if (
        inputs["ctr_percentage_point_change"].copy_negate()
        < thresholds["minimum_ctr_decline_percentage_points"]
    ):
        return False
    return opportunity_type == "ctr_opportunity" or _ratio_at_least(
        int(inputs["impressions_percentage_change_numerator"]),
        int(inputs["impressions_percentage_change_denominator"]),
        thresholds["minimum_impressions_growth_percentage"],
    )


def _measurement_text(opportunity_type: str, inputs: dict[str, PriorityInput]) -> tuple[str, str]:
    """Describe only measured changes, without predicting their cause or business impact.
    仅描述已测量变化，不预测其原因或业务影响。
    """
    if opportunity_type == "traffic_decline":
        first, second = inputs["previous_clicks"], inputs["current_clicks"]
        loss = -inputs["clicks_absolute_change"]
        ratio = (
            f"{-int(inputs['clicks_percentage_change_numerator'])}"
            f"/{inputs['clicks_percentage_change_denominator']}"
        )
        return (
            f"Clicks {first} → {second}; loss {loss}; exact decline {ratio}%.",
            f"点击数 {first} → {second}；减少 {loss}；精确下降比率 {ratio}%。",
        )
    impressions = f"{inputs['previous_impressions']} → {inputs['current_impressions']}"
    if opportunity_type == "ranking_decline":
        change = inputs["average_position_change"]
        return (
            f"Impressions {impressions}; average position worsened by {change}.",
            f"展示数 {impressions}；平均排名变差 {change}。",
        )
    change = inputs["ctr_percentage_point_change"]
    english = f"Impressions {impressions}; CTR changed by {change} percentage points."
    chinese = f"展示数 {impressions}；CTR 变化为 {change} 个百分点。"
    if opportunity_type == "impression_growth_gap":
        ratio = (
            f"{inputs['impressions_percentage_change_numerator']}"
            f"/{inputs['impressions_percentage_change_denominator']}"
        )
        english += f" Exact impression growth {ratio}%."
        chinese += f" 精确展示增长比率 {ratio}%。"
    return english, chinese


def prioritize_candidate(
    candidate: OpportunityCandidate, config: OpportunityPriorityConfig = DEFAULT_PRIORITY_CONFIG
) -> PrioritizedOpportunityCandidate:
    """Evaluate high then medium; retain every existing signal with low as the remaining tier.
    先评估高等级，再评估中等级；其余已有信号保留为低等级。

    This function cannot create a candidate or upgrade page evidence eligibility.
    此函数不能创建候选，也不能提升页面证据资格。
    """
    inputs = _inputs(candidate)
    thresholds = {
        tier: asdict(getattr(config, f"{candidate.opportunity_type}_{tier}"))
        for tier in ("high", "medium")
    }
    tier: PriorityTier = "low"
    for evaluated in ("high", "medium"):
        if _matches(candidate.opportunity_type, inputs, thresholds[evaluated]):
            tier = evaluated
            break
    english, chinese = _measurement_text(candidate.opportunity_type, inputs)
    if tier == "low":
        explanation = "Low: the detected signal does not meet every medium-tier threshold."
        translated = "低：已检测信号未同时满足中等级的全部阈值。"
        suffix = "low_higher_tier_thresholds_not_met"
    else:
        explanation = f"{tier.capitalize()}: every {tier}-tier threshold is met."
        translated = f"{'高' if tier == 'high' else '中'}：满足该等级的全部阈值。"
        suffix = f"{tier}_thresholds_met"
    return PrioritizedOpportunityCandidate(
        candidate=candidate,
        priority_tier=tier,
        priority_rule_version=config.version,
        priority_reason_code=f"{candidate.opportunity_type}_{suffix}",
        priority_message=f"{explanation} {english} / {translated} {chinese}",
        priority_inputs=inputs,
        priority_thresholds=thresholds,
    )


def prioritize_candidates(
    candidates: Iterable[OpportunityCandidate],
    config: OpportunityPriorityConfig = DEFAULT_PRIORITY_CONFIG,
) -> tuple[PrioritizedOpportunityCandidate, ...]:
    """Order all retained candidates by tier, exact URL, type, and stable page ID.
    将全部保留候选按等级、准确 URL、类型及稳定页面 ID 排序。

    No numerical impact score or within-tier SEO-value ordering is introduced.
    不增加数值影响评分，也不按等级内 SEO 价值排序。
    """
    prioritized = [prioritize_candidate(candidate, config) for candidate in candidates]
    return tuple(
        sorted(
            prioritized,
            key=lambda item: (
                PRIORITY_TIER_ORDER.index(item.priority_tier),
                item.candidate.url,
                item.candidate.opportunity_type,
                item.candidate.page_id.int,
            ),
        )
    )
