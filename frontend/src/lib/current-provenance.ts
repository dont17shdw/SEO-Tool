import { isQualityObservation, type QualityObservation } from "@/lib/data-quality";
import { isCount, isRecord } from "@/lib/gsc-api";

export const CURRENT_METRIC_LABELS = {
  clicks_28d: "Clicks 28d / 28 天点击",
  impressions_28d: "Impressions 28d / 28 天展示",
  ctr: "CTR / 点击率",
  average_position: "Average position / 平均排名",
} as const;

export type CurrentMetricName = keyof typeof CURRENT_METRIC_LABELS;
export type MetricProvenance = {
  metric_name: CurrentMetricName;
  current_value: number | string | null;
  status: "known" | "unknown" | "unavailable";
  snapshot_id: string | null;
  import_run_id: string | null;
  period_start: string | null;
  period_end: string | null;
  imported_at: string | null;
};

export type CurrentProvenance = {
  page_id: string;
  metrics: MetricProvenance[];
  known_provenance_count: number;
  unknown_provenance_count: number;
  unavailable_metric_count: number;
  all_known_metrics_share_one_snapshot: boolean | null;
  distinct_snapshot_ids: string[];
  observations: QualityObservation[];
};

function isUuid(value: unknown): value is string {
  return typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

function isDate(value: unknown): value is string {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) &&
    Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
}

function isCurrentValue(value: unknown, metricName: CurrentMetricName): boolean {
  if (value === null) return true;
  if (metricName === "clicks_28d" || metricName === "impressions_28d") return isCount(value);
  return (typeof value === "number" || (typeof value === "string" && value.trim() !== "")) &&
    Number.isFinite(Number(value)) && Number(value) >= 0 && (metricName !== "ctr" || Number(value) <= 1);
}

/**
 * Validate a declared source link; unknown and unavailable metrics must carry no source metadata.
 * 验证已声明的来源链接；未知及不可用指标不得带有来源元数据。
 */
function isMetricProvenance(value: unknown, metricName: CurrentMetricName): value is MetricProvenance {
  if (!isRecord(value) || value.metric_name !== metricName || !isCurrentValue(value.current_value, metricName)) return false;
  if (value.status === "unavailable" || value.status === "unknown") {
    return (value.status === "unavailable" ? value.current_value === null : value.current_value !== null) &&
      [value.snapshot_id, value.import_run_id, value.period_start, value.period_end, value.imported_at].every((field) => field === null);
  }
  return value.status === "known" && value.current_value !== null && isUuid(value.snapshot_id) && isUuid(value.import_run_id) &&
    typeof value.imported_at === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value.imported_at) && Number.isFinite(Date.parse(value.imported_at)) &&
    ((value.period_start === null && value.period_end === null) ||
      (isDate(value.period_start) && isDate(value.period_end) && value.period_start <= value.period_end));
}

/**
 * Check declared provenance metadata and summary consistency without reconstructing origins.
 * 检查已声明来源元数据与汇总的一致性，不重建指标来源。
 */
export function isCurrentProvenance(value: unknown, pageId: string, currentPage: Record<string, unknown>): value is CurrentProvenance {
  const names = Object.keys(CURRENT_METRIC_LABELS) as CurrentMetricName[];
  if (!isRecord(value) || value.page_id !== pageId || !Array.isArray(value.metrics) || value.metrics.length !== names.length ||
    !value.metrics.every((metric, index) => isMetricProvenance(metric, names[index])) ||
    ![value.known_provenance_count, value.unknown_provenance_count, value.unavailable_metric_count].every(isCount) ||
    !Array.isArray(value.distinct_snapshot_ids) || !value.distinct_snapshot_ids.every(isUuid) ||
    !Array.isArray(value.observations) || !value.observations.every(isQualityObservation)) return false;

  const metrics = value.metrics as MetricProvenance[];
  const known = metrics.filter((metric) => metric.status === "known");
  const suppliedIds = value.distinct_snapshot_ids as string[];
  const knownIds = new Set(known.map((metric) => metric.snapshot_id));
  return metrics.every((metric) => metric.current_value === null
      ? currentPage[metric.metric_name] === null
      : currentPage[metric.metric_name] !== null && Number(metric.current_value) === Number(currentPage[metric.metric_name])) &&
    value.known_provenance_count === known.length &&
    value.unknown_provenance_count === metrics.filter((metric) => metric.status === "unknown").length &&
    value.unavailable_metric_count === metrics.filter((metric) => metric.status === "unavailable").length &&
    suppliedIds.length === knownIds.size && new Set(suppliedIds).size === suppliedIds.length && suppliedIds.every((id) => knownIds.has(id)) &&
    value.all_known_metrics_share_one_snapshot === (known.length === 0 ? null : knownIds.size === 1);
}
