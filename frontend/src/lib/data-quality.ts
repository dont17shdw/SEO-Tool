import { isCount, isRecord } from "@/lib/gsc-api";

export type QualityObservation = {
  code: string;
  severity: "info" | "warning" | "blocking";
  scope: "page" | "import";
  message: string;
  snapshot_ids: string[];
  import_run_ids: string[];
  evidence: Record<string, unknown>;
};

export const QUALITY_COUNT_LABELS = {
  total_snapshots: "Total snapshots / 全部快照",
  exact_date_snapshots: "Exact dates / 日期已知快照",
  unknown_date_snapshots: "Unknown dates / 日期未知快照",
  snapshots_with_missing_metrics: "Missing metrics / 指标缺失快照",
  distinct_exact_periods: "Distinct exact periods / 不同精确时间段",
  revision_periods: "Periods with revisions / 存在修订的时间段",
  compatible_exact_periods: "Compatible exact periods / 兼容精确时间段",
} as const;

export type DataQuality = {
  page_id: string;
  readiness: "insufficient" | "limited" | "ready";
  comparison_exists: boolean;
  selected_snapshot_ids: string[];
  readiness_reasons: string[];
  counts: Record<keyof typeof QUALITY_COUNT_LABELS, number>;
  observations: QualityObservation[];
};

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

/**
 * Share the factual observation contract across history quality and current provenance.
 * 在历史质量与当前来源追踪之间共享事实观察契约。
 */
export function isQualityObservation(value: unknown): value is QualityObservation {
  return isRecord(value) && typeof value.code === "string" && typeof value.message === "string" &&
    typeof value.severity === "string" && ["info", "warning", "blocking"].includes(value.severity) &&
    typeof value.scope === "string" && ["page", "import"].includes(value.scope) &&
    isStringArray(value.snapshot_ids) && isStringArray(value.import_run_ids) && isRecord(value.evidence);
}

/**
 * Validate read-only evidence metadata before displaying readiness or observations.
 * 在显示就绪程度或观察结果前，验证只读证据元数据。
 */
export function isDataQuality(value: unknown, pageId: string): boolean {
  return isRecord(value) && value.page_id === pageId &&
    typeof value.readiness === "string" && ["insufficient", "limited", "ready"].includes(value.readiness) &&
    typeof value.comparison_exists === "boolean" && isStringArray(value.selected_snapshot_ids) &&
    value.selected_snapshot_ids.length === (value.comparison_exists ? 2 : 0) &&
    isStringArray(value.readiness_reasons) && isRecord(value.counts) &&
    Object.keys(QUALITY_COUNT_LABELS).every((key) => isCount((value.counts as Record<string, unknown>)[key])) &&
    Array.isArray(value.observations) && value.observations.every(isQualityObservation);
}
