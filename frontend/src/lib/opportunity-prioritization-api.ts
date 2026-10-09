import { isCount, isRecord, requestJson } from "@/lib/gsc-api";
import type { PaginationMetadata } from "@/lib/history-api";
import { isOpportunityCandidate, type EvidenceValues, type OpportunityCandidate, type OpportunityType } from "@/lib/opportunities-api";
import { ChineseUiError, priorityLabels } from "@/lib/zh-cn";

export const PRIORITY_LABELS = priorityLabels;
export type PriorityTier = keyof typeof PRIORITY_LABELS;
export type OpportunityFilters = { siteId: string; priorityTier: PriorityTier | "" };
export type PrioritizedOpportunityCandidate = OpportunityCandidate & {
  priority_tier: PriorityTier;
  priority_rule_version: string;
  priority_reason_code: string;
  priority_message: string;
  priority_inputs: EvidenceValues;
  priority_thresholds: { high: EvidenceValues; medium: EvidenceValues };
};
export type OpportunityEligibilitySummary = {
  analyzed_pages: number;
  eligible_pages: number;
  ineligible_pages: number;
  pages_with_candidates: number;
  ready_pages_without_candidates: number;
  detected_candidates: number;
  gate_reason_counts: Record<string, number>;
};
export type PrioritizedOpportunitiesResponse = PaginationMetadata & {
  items: PrioritizedOpportunityCandidate[];
  summary: OpportunityEligibilitySummary;
};

const INPUT_FIELDS: Record<OpportunityType, string[]> = {
  traffic_decline: ["previous_clicks", "current_clicks", "clicks_absolute_change", "clicks_percentage_change_numerator", "clicks_percentage_change_denominator"],
  ctr_opportunity: ["previous_impressions", "current_impressions", "previous_ctr", "current_ctr", "ctr_percentage_point_change"],
  ranking_decline: ["previous_impressions", "current_impressions", "previous_average_position", "current_average_position", "average_position_change"],
  impression_growth_gap: ["previous_impressions", "current_impressions", "impressions_absolute_change", "impressions_percentage_change_numerator", "impressions_percentage_change_denominator", "previous_ctr", "current_ctr", "ctr_percentage_point_change"],
};
const THRESHOLD_FIELDS: Record<OpportunityType, string[]> = {
  traffic_decline: ["minimum_previous_clicks", "minimum_click_loss", "minimum_click_decline_percentage"],
  ctr_opportunity: ["minimum_impressions", "minimum_ctr_decline_percentage_points"],
  ranking_decline: ["minimum_impressions", "minimum_average_position_worsening"],
  impression_growth_gap: ["minimum_impressions", "minimum_impressions_growth_percentage", "minimum_ctr_decline_percentage_points"],
};

function isNumeric(value: unknown): value is number | string {
  return (typeof value === "number" || (typeof value === "string" && value.trim() !== "")) && Number.isFinite(Number(value));
}

function hasNumericFields(value: unknown, fields: string[]): value is EvidenceValues {
  return isRecord(value) && fields.every((field) => Object.hasOwn(value, field)) && Object.values(value).every(isNumeric);
}

function isIntegerString(value: unknown): value is string {
  return typeof value === "string" && /^-?(0|[1-9]\d*)$/.test(value);
}

/**
 * Bind exact priority inputs to retained detection evidence without assigning a tier in the browser.
 * 将精确优先级输入绑定至保留的检测证据，不在浏览器中分配等级。
 */
export function isPrioritizedOpportunityCandidate(value: unknown): value is PrioritizedOpportunityCandidate {
  if (!isRecord(value)) return false;
  const metadata: Record<string, unknown> = value;
  if (!isOpportunityCandidate(value) || typeof metadata.priority_tier !== "string" ||
    !Object.hasOwn(PRIORITY_LABELS, metadata.priority_tier) ||
    ![metadata.priority_rule_version, metadata.priority_reason_code, metadata.priority_message].every((field) => typeof field === "string" && field.trim() !== "") ||
    !hasNumericFields(metadata.priority_inputs, INPUT_FIELDS[value.opportunity_type]) || !isRecord(metadata.priority_thresholds) ||
    ![metadata.priority_thresholds.high, metadata.priority_thresholds.medium].every((thresholds) =>
      hasNumericFields(thresholds, THRESHOLD_FIELDS[value.opportunity_type]) && Object.values(thresholds).every((field) => Number(field) >= 0))) return false;

  const inputs = metadata.priority_inputs;
  for (const period of ["previous", "current"] as const) {
    for (const metric of ["clicks", "impressions", "ctr", "average_position"]) {
      const key = `${period}_${metric}`;
      if (Object.hasOwn(inputs, key) && (Number(inputs[key]) !== Number(value.evidence[period][metric]) ||
        (["clicks", "impressions"].includes(metric) && !isCount(inputs[key])))) return false;
    }
  }
  for (const field of ["clicks_absolute_change", "impressions_absolute_change", "ctr_percentage_point_change", "average_position_change"]) {
    if (Object.hasOwn(inputs, field) && Number(inputs[field]) !== Number(value.evidence.changes[field])) return false;
  }
  for (const metric of ["clicks", "impressions"]) {
    const numerator = inputs[`${metric}_percentage_change_numerator`];
    const denominator = inputs[`${metric}_percentage_change_denominator`];
    if (numerator === undefined && denominator === undefined) continue;
    if (!isIntegerString(numerator) || !isIntegerString(denominator) || BigInt(denominator) <= BigInt(0) ||
      BigInt(denominator) !== BigInt(inputs[`previous_${metric}`]) ||
      BigInt(numerator) !== (BigInt(inputs[`current_${metric}`]) - BigInt(inputs[`previous_${metric}`])) * BigInt(100)) return false;
  }
  return true;
}

/**
 * Counts describe all selected-site pages before tier filtering; blocking reasons may overlap.
 * 计数描述等级筛选前的全部所选站点页面；阻止原因可以重叠。
 */
function isEligibilitySummary(value: unknown): value is OpportunityEligibilitySummary {
  if (!isRecord(value) || ![value.analyzed_pages, value.eligible_pages, value.ineligible_pages, value.pages_with_candidates,
    value.ready_pages_without_candidates, value.detected_candidates].every(isCount) || !isRecord(value.gate_reason_counts) ||
    !Object.entries(value.gate_reason_counts).every(([code, count]) => code !== "" && isCount(count) && count <= Number(value.ineligible_pages))) return false;
  const summary = value as OpportunityEligibilitySummary;
  return summary.eligible_pages + summary.ineligible_pages === summary.analyzed_pages &&
    summary.pages_with_candidates + summary.ready_pages_without_candidates === summary.eligible_pages &&
    summary.detected_candidates >= summary.pages_with_candidates && summary.detected_candidates <= summary.pages_with_candidates * 4;
}

/**
 * Read prioritized runtime candidates while retaining the original neutral endpoint and server ordering.
 * 读取已分配优先级的运行时候选，保留原始中性接口与服务端顺序。
 */
export async function listPrioritizedOpportunities(page: number, pageSize: number, filters: OpportunityFilters,
  signal: AbortSignal): Promise<PrioritizedOpportunitiesResponse> {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (filters.siteId) query.set("site_id", filters.siteId);
  if (filters.priorityTier) query.set("priority_tier", filters.priorityTier);
  const payload = await requestJson(`/opportunities/prioritized?${query}`, { method: "GET", signal });
  if (!isRecord(payload) || payload.page !== page || payload.page_size !== pageSize || !isCount(payload.total) || !isCount(payload.total_pages) ||
    payload.total_pages !== Math.ceil(payload.total / pageSize) || !Array.isArray(payload.items) || !payload.items.every(isPrioritizedOpportunityCandidate) ||
    payload.items.length !== Math.max(0, Math.min(pageSize, payload.total - (page - 1) * pageSize)) || !isEligibilitySummary(payload.summary) ||
    payload.total > payload.summary.detected_candidates || (!filters.priorityTier && payload.total !== payload.summary.detected_candidates) ||
    !payload.items.every((candidate) => (!filters.priorityTier || candidate.priority_tier === filters.priorityTier) &&
      (!filters.siteId || candidate.site_id === filters.siteId)) ||
    new Set(payload.items.map((candidate) => [candidate.page_id, candidate.previous_snapshot_id, candidate.current_snapshot_id, candidate.opportunity_type].join(":"))).size !== payload.items.length) {
    throw new ChineseUiError("SEO 机会优先级响应格式异常，请刷新页面或检查后端版本。");
  }
  return payload as PrioritizedOpportunitiesResponse;
}
