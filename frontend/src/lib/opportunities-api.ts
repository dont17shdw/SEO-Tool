import { isCount, isRecord, requestJson } from "@/lib/gsc-api";
import { isQualityObservation, type DataQuality, type QualityObservation } from "@/lib/data-quality";
import type { PaginationMetadata, PerformanceComparison } from "@/lib/history-api";
import { isDateCoverage } from "@/lib/report-scope";

export const OPPORTUNITY_LABELS = {
  traffic_decline: "Traffic decline / 流量下降",
  ctr_opportunity: "CTR opportunity / CTR 机会",
  ranking_decline: "Ranking decline / 排名下降",
  impression_growth_gap: "Impression growth gap / 展示增长缺口",
} as const;

export type OpportunityType = keyof typeof OPPORTUNITY_LABELS;
export type EvidenceValues = Record<string, number | string>;
export type OpportunityCandidate = {
  opportunity_type: OpportunityType;
  page_id: string;
  site_id: string | null;
  url: string;
  previous_snapshot_id: string;
  current_snapshot_id: string;
  previous_period_start: string;
  previous_period_end: string;
  current_period_start: string;
  current_period_end: string;
  evidence_readiness: "ready";
  scope_compatibility: "compatible";
  reason_code: string;
  message: string;
  evidence: { previous: EvidenceValues; current: EvidenceValues; changes: EvidenceValues; thresholds: EvidenceValues };
};

export type PageOpportunityAnalysis = {
  page_id: string;
  site_id: string | null;
  url: string;
  eligible: boolean;
  evidence_readiness: DataQuality["readiness"];
  gate_reasons: string[];
  gate_observations: QualityObservation[];
  comparison: PerformanceComparison | null;
  candidates: OpportunityCandidate[];
};

export type OpportunitiesResponse = PaginationMetadata & { items: OpportunityCandidate[] };

const RULE_FIELDS: Record<OpportunityType, { metrics: string[]; changes: string[]; thresholds: string[] }> = {
  traffic_decline: {
    metrics: ["clicks"],
    changes: ["clicks_absolute_change", "clicks_percentage_change"],
    thresholds: ["minimum_previous_clicks", "maximum_clicks_absolute_change", "maximum_clicks_percentage_change"],
  },
  ctr_opportunity: {
    metrics: ["impressions", "ctr", "average_position"],
    changes: ["impressions_percentage_change", "ctr_percentage_point_change", "average_position_change"],
    thresholds: ["minimum_impressions", "maximum_ctr_percentage_point_change", "maximum_average_position_change", "minimum_impressions_percentage_change"],
  },
  ranking_decline: {
    metrics: ["impressions", "average_position"],
    changes: ["average_position_change"],
    thresholds: ["minimum_impressions", "minimum_average_position_change", "minimum_current_impressions_exclusive"],
  },
  impression_growth_gap: {
    metrics: ["clicks", "impressions", "ctr"],
    changes: ["clicks_absolute_change", "clicks_percentage_change", "impressions_absolute_change", "impressions_percentage_change", "ctr_percentage_point_change"],
    thresholds: ["minimum_impressions", "minimum_impressions_percentage_change", "maximum_clicks_percentage_change_exclusive", "maximum_ctr_percentage_point_change"],
  },
};

function isValue(value: unknown): value is string | number {
  return (typeof value === "number" || (typeof value === "string" && value.trim() !== "")) && Number.isFinite(Number(value));
}

function isValues(value: unknown, required: string[]): value is EvidenceValues {
  return isRecord(value) && required.every((key) => Object.hasOwn(value, key)) && Object.values(value).every(isValue);
}

function isIdentity(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

function isSiteId(value: unknown): value is string | null {
  return value === null || isIdentity(value);
}

/**
 * Validate auditable rule facts without recalculating signals or applying browser-side thresholds.
 * 校验可审计规则事实，不重新计算信号，也不在浏览器端应用门槛。
 */
export function isOpportunityCandidate(value: unknown): value is OpportunityCandidate {
  if (!isRecord(value) || typeof value.opportunity_type !== "string" || !Object.hasOwn(OPPORTUNITY_LABELS, value.opportunity_type) ||
    ![value.page_id, value.url, value.previous_snapshot_id, value.current_snapshot_id, value.reason_code, value.message].every(isIdentity) ||
    !isSiteId(value.site_id) || value.previous_snapshot_id === value.current_snapshot_id ||
    value.evidence_readiness !== "ready" || value.scope_compatibility !== "compatible" || !isRecord(value.evidence)) return false;
  const fields = RULE_FIELDS[value.opportunity_type as OpportunityType];
  if (!isValues(value.evidence.previous, fields.metrics) || !isValues(value.evidence.current, fields.metrics) ||
    !isValues(value.evidence.changes, fields.changes) || !isValues(value.evidence.thresholds, fields.thresholds)) return false;
  for (const metrics of [value.evidence.previous, value.evidence.current]) {
    if (!fields.metrics.every((field) => Number(metrics[field]) >= 0 &&
      (!["clicks", "impressions"].includes(field) || (typeof metrics[field] === "number" && isCount(metrics[field]))) &&
      (field !== "ctr" || Number(metrics[field]) <= 1))) return false;
  }
  return ["previous", "current"].every((prefix) => isDateCoverage({
    period_start: value[`${prefix}_period_start`], period_end: value[`${prefix}_period_end`],
    coverage_status: "complete", observed_date_count: 28, dates_consecutive: true,
  })) && typeof value.previous_period_end === "string" && typeof value.current_period_start === "string" &&
    value.previous_period_end < value.current_period_start;
}

/**
 * Compare embedded evidence structurally so conflicting or stale analysis is never presented as eligible.
 * 对内嵌证据进行结构比较，避免将冲突或过期分析展示为合格证据。
 */
function sameJson(left: unknown, right: unknown): boolean {
  if (left === right) return true;
  if (Array.isArray(left) && Array.isArray(right)) {
    return left.length === right.length && left.every((item, index) => sameJson(item, right[index]));
  }
  return isRecord(left) && isRecord(right) && Object.keys(left).length === Object.keys(right).length &&
    Object.keys(left).every((key) => Object.hasOwn(right, key) && sameJson(left[key], right[key]));
}

/**
 * Bind page candidates to the already validated comparison and readiness from the same response.
 * 将页面候选绑定至同一响应中已验证的对比与就绪度。
 */
export function isPageOpportunityAnalysis(value: unknown, currentPage: { id: string; site_id: string | null; url: string },
  comparison: PerformanceComparison | null, quality: DataQuality): value is PageOpportunityAnalysis {
  if (!isRecord(value) || value.page_id !== currentPage.id || value.site_id !== currentPage.site_id || value.url !== currentPage.url ||
    typeof value.eligible !== "boolean" || value.evidence_readiness !== quality.readiness ||
    !Array.isArray(value.gate_reasons) || !value.gate_reasons.every((reason) => typeof reason === "string") ||
    !Array.isArray(value.gate_observations) || !value.gate_observations.every(isQualityObservation) ||
    !sameJson(value.comparison, comparison) || !Array.isArray(value.candidates) || !value.candidates.every(isOpportunityCandidate)) return false;
  if (value.eligible !== (quality.readiness === "ready") || !sameJson(value.gate_reasons, quality.readiness_reasons)) return false;
  const gateReasons = value.gate_reasons;
  if (!sameJson(quality.selected_snapshot_ids, comparison ? [comparison.previous_snapshot_id, comparison.current_snapshot_id] : []) ||
    !value.gate_observations.every((observation) => gateReasons.includes(observation.code) &&
      quality.observations.some((qualityObservation) => sameJson(observation, qualityObservation)))) return false;
  if (!value.eligible) return value.candidates.length === 0 && value.gate_reasons.length > 0;
  if (!comparison || comparison.scope_compatibility !== "compatible" || comparison.periods_overlap ||
    comparison.previous_snapshot_id === comparison.current_snapshot_id || comparison.previous_period_end >= comparison.current_period_start ||
    comparison.previous_coverage_status !== "complete" || comparison.current_coverage_status !== "complete" ||
    value.gate_reasons.length > 0 || value.gate_observations.length > 0) return false;
  return new Set(value.candidates.map((candidate) => candidate.opportunity_type)).size === value.candidates.length &&
    value.candidates.every((candidate) => candidate.page_id === currentPage.id && candidate.site_id === currentPage.site_id &&
      candidate.url === currentPage.url && ["previous_snapshot_id", "current_snapshot_id", "previous_period_start", "previous_period_end",
        "current_period_start", "current_period_end"].every((key) => candidate[key as keyof OpportunityCandidate] === comparison[key as keyof PerformanceComparison]));
}

/**
 * Paginate actual runtime candidates, preserving the API's neutral deterministic order.
 * 对实际运行时候选进行分页，保留 API 的中性确定性顺序。
 */
export async function listOpportunities(page: number, pageSize: number, signal: AbortSignal): Promise<OpportunitiesResponse> {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  const payload = await requestJson(`/opportunities?${query}`, { method: "GET", signal });
  if (!isRecord(payload) || payload.page !== page || payload.page_size !== pageSize || !isCount(payload.total) || !isCount(payload.total_pages) ||
    payload.total_pages !== Math.ceil(payload.total / pageSize) || !Array.isArray(payload.items) || !payload.items.every(isOpportunityCandidate) ||
    payload.items.length !== Math.max(0, Math.min(pageSize, payload.total - (page - 1) * pageSize)) ||
    new Set(payload.items.map((candidate) => [candidate.page_id, candidate.previous_snapshot_id, candidate.current_snapshot_id, candidate.opportunity_type].join(":"))).size !== payload.items.length) {
    throw new Error("Unexpected opportunity response. 机会响应格式不符合预期。");
  }
  return payload as OpportunitiesResponse;
}
