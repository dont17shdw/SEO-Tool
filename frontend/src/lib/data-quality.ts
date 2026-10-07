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
    Array.isArray(value.observations) && value.observations.every((observation) =>
      isRecord(observation) && typeof observation.code === "string" && typeof observation.message === "string" &&
      typeof observation.severity === "string" && ["info", "warning", "blocking"].includes(observation.severity) &&
      typeof observation.scope === "string" && ["page", "import"].includes(observation.scope) && isStringArray(observation.snapshot_ids) &&
      isStringArray(observation.import_run_ids) && isRecord(observation.evidence));
}
