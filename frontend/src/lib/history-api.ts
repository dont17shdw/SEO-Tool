import { isCount, isPageMetrics, isRecord, isReportingPeriod, requestJson, type PageMetrics } from "@/lib/gsc-api";
import { isDataQuality, type DataQuality } from "@/lib/data-quality";
import { isCurrentProvenance, type CurrentProvenance } from "@/lib/current-provenance";

type ReportingPeriod = {
  reporting_window: "latest_28_days";
  period_start: string | null;
  period_end: string | null;
  period_status: "exact" | "unknown";
};

export type ImportRun = ReportingPeriod & {
  id: string;
  source: "gsc";
  source_type: "pages_performance";
  file_hash: string;
  filename: string;
  imported_at: string;
  total_rows: number;
  created_count: number;
  updated_count: number;
  skipped_count: number;
  status: "completed";
};

export type PerformanceSnapshot = ReportingPeriod & {
  id: string;
  import_run_id: string;
  page_id: string;
  url: string;
  source: "gsc";
  source_type: "pages_performance";
  imported_at: string;
  created_at: string;
  clicks: number | null;
  impressions: number | null;
  ctr: string | number | null;
  average_position: string | number | null;
};

type MetricChange = { absolute_change: number | null; percentage_change: string | number | null };

export type PerformanceComparison = {
  previous_snapshot_id: string;
  current_snapshot_id: string;
  previous_period_start: string;
  previous_period_end: string;
  current_period_start: string;
  current_period_end: string;
  periods_overlap: boolean;
  clicks: MetricChange;
  impressions: MetricChange;
  ctr_percentage_point_change: string | number | null;
  average_position_change: string | number | null;
};

export type PaginationMetadata = { page: number; page_size: number; total: number; total_pages: number };
export type ImportHistoryResponse = PaginationMetadata & { items: ImportRun[] };
export type PagePerformanceResponse = PaginationMetadata & {
  current_page: PageMetrics & { id: string };
  items: PerformanceSnapshot[];
  comparison: PerformanceComparison | null;
  comparison_unavailable_reason: string | null;
  quality: DataQuality;
  provenance: CurrentProvenance;
};

function isPagination(value: Record<string, unknown>, page: number, pageSize: number): boolean {
  return value.page === page && value.page_size === pageSize && isCount(value.total) && isCount(value.total_pages);
}

function isTimestamp(value: unknown): boolean {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}

function isSourcePeriod(value: Record<string, unknown>): boolean {
  return value.source === "gsc" && value.source_type === "pages_performance" &&
    value.reporting_window === "latest_28_days" && isReportingPeriod(value);
}

function isImportRun(value: unknown): boolean {
  return isRecord(value) && isSourcePeriod(value) && typeof value.id === "string" &&
    typeof value.file_hash === "string" && typeof value.filename === "string" &&
    isTimestamp(value.imported_at) && value.status === "completed" &&
    [value.total_rows, value.created_count, value.updated_count, value.skipped_count].every(isCount);
}

/**
 * Validate snapshot observations independently from the latest stored page metrics.
 * 将快照观察值与最新已保存页面指标分开验证。
 */
function isSnapshot(value: unknown): boolean {
  return isRecord(value) && isSourcePeriod(value) && typeof value.id === "string" &&
    typeof value.import_run_id === "string" && typeof value.page_id === "string" &&
    isTimestamp(value.imported_at) && isTimestamp(value.created_at) &&
    isPageMetrics({ ...value, clicks_28d: value.clicks, impressions_28d: value.impressions });
}

function isNullableChange(value: unknown): boolean {
  return value === null || ((typeof value === "number" || (typeof value === "string" && value.trim() !== "")) && Number.isFinite(Number(value)));
}

function isMetricChange(value: unknown): boolean {
  return isRecord(value) && (value.absolute_change === null ||
    (typeof value.absolute_change === "number" && Number.isSafeInteger(value.absolute_change))) &&
    isNullableChange(value.percentage_change);
}

/**
 * Allow signed descriptive changes and preserve unavailable calculations as NULL.
 * 允许带符号的描述性变化，并将不可计算的值保持为 NULL。
 */
function isComparison(value: unknown): boolean {
  return value === null || (isRecord(value) &&
    [value.previous_snapshot_id, value.current_snapshot_id, value.previous_period_start,
      value.previous_period_end, value.current_period_start, value.current_period_end].every((item) => typeof item === "string") &&
    typeof value.periods_overlap === "boolean" && isMetricChange(value.clicks) && isMetricChange(value.impressions) &&
    isNullableChange(value.ctr_percentage_point_change) && isNullableChange(value.average_position_change));
}

/**
 * Read completed import events with bounded pagination and no mutation endpoints.
 * 通过受限分页读取已完成的导入事件，不提供修改接口。
 */
export async function listImportHistory(page: number, pageSize: number, signal: AbortSignal): Promise<ImportHistoryResponse> {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  const payload = await requestJson(`/imports?${query}`, { method: "GET", signal });
  if (!isRecord(payload) || !isPagination(payload, page, pageSize) || !Array.isArray(payload.items) || !payload.items.every(isImportRun)) {
    throw new Error("Unexpected import history response. 导入历史响应格式不符合预期。");
  }
  return payload as ImportHistoryResponse;
}

/**
 * Fetch chronological snapshots and the API-selected compatible report comparison.
 * 获取按时间排序的快照及 API 选出的兼容报告时间段对比。
 */
export async function getPagePerformance(pageId: string, page: number, pageSize: number, signal: AbortSignal): Promise<PagePerformanceResponse> {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  const payload = await requestJson(`/pages/${encodeURIComponent(pageId)}/performance?${query}`, { method: "GET", signal });
  if (!isRecord(payload) || !isPagination(payload, page, pageSize) ||
    !isRecord(payload.current_page) || payload.current_page.id !== pageId || !isPageMetrics(payload.current_page) ||
    !Array.isArray(payload.items) || !payload.items.every(isSnapshot) || !isComparison(payload.comparison) ||
    !(payload.comparison_unavailable_reason === null || typeof payload.comparison_unavailable_reason === "string") ||
    !isDataQuality(payload.quality, pageId) || !isCurrentProvenance(payload.provenance, pageId, payload.current_page)) {
    throw new Error("Unexpected page performance response. 页面表现响应格式不符合预期。");
  }
  return payload as PagePerformanceResponse;
}

export function formatPeriod(period: { period_start: string | null; period_end: string | null }): string {
  return period.period_start && period.period_end
    ? `${period.period_start} → ${period.period_end}`
    : "Unknown exact dates / 精确日期未知";
}

export function formatImportTime(timestamp: string): string {
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "medium" }).format(new Date(timestamp));
}

/**
 * Percentage changes and CTR points are already calculated by the backend; do not multiply again.
 * 百分比变化及 CTR 百分点已由后端计算；不要再次乘以 100。
 */
export function formatChange(value: string | number | null, unit = ""): string {
  if (value === null) return "Unavailable / 不可计算";
  return `${new Intl.NumberFormat("en", { maximumFractionDigits: 6, signDisplay: "exceptZero" }).format(Number(value))}${unit}`;
}
