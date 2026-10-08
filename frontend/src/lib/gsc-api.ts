import { API_BASE_URL } from "@/lib/api";
import { isDateCoverage, isReportScope, type DateCoverage, type ReportScope, type ScopeDeclaration } from "@/lib/report-scope";

export type PageMetrics = {
  url: string;
  clicks_28d: number | null;
  impressions_28d: number | null;
  ctr: string | number | null;
  average_position: string | number | null;
};

export type ImportPreview = DateCoverage & {
  source: "gsc_pages";
  reporting_window: "latest_28_days";
  period_start: string | null;
  period_end: string | null;
  period_status: "exact" | "unknown";
  detected_sheet: string | null;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  column_mapping: Record<"url" | "clicks" | "impressions" | "ctr" | "position", string>;
  errors: { row: number; field: string; code: string; message: string }[];
  sample_rows: (PageMetrics & { row: number })[];
  can_apply: boolean;
  preview_hash: string;
  file_hash: string;
  report_scope: ReportScope;
};

export type ImportResult = {
  created_count: number;
  updated_count: number;
  skipped_count: number;
  error_count: number;
  import_run_id: string;
  already_processed: boolean;
};

export type PagesResponse = {
  items: (PageMetrics & { id: string })[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isCount(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

function isMetric(value: unknown): boolean {
  return (
    value === null ||
    ((typeof value === "number" ||
      (typeof value === "string" && value.trim() !== "")) &&
      Number.isFinite(Number(value)) &&
      Number(value) >= 0)
  );
}

/**
 * Validate nullable database metrics at the browser boundary, including fraction-based CTR.
 * 在浏览器边界验证可空数据库指标，包括以比例存储的 CTR。
 */
export function isPageMetrics(value: unknown): boolean {
  return (
    isRecord(value) &&
    typeof value.url === "string" &&
    (value.clicks_28d === null || isCount(value.clicks_28d)) &&
    (value.impressions_28d === null || isCount(value.impressions_28d)) &&
    isMetric(value.ctr) &&
    (value.ctr === null || Number(value.ctr) <= 1) &&
    isMetric(value.average_position)
  );
}

/**
 * Read a JSON response and surface the API's human-readable error without a stack trace.
 * 读取 JSON 响应，并显示 API 提供的可读错误，不暴露堆栈信息。
 */
export async function requestJson(path: string, options: RequestInit): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    ...options,
    cache: "no-store",
    signal: options.signal
      ? AbortSignal.any([options.signal, AbortSignal.timeout(60_000)])
      : AbortSignal.timeout(60_000),
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (isRecord(payload)) {
      const detail = payload.detail;
      if (isRecord(detail) && typeof detail.message === "string") {
        throw new Error(detail.message);
      }
      if (typeof detail === "string") {
        throw new Error(detail);
      }
    }
    throw new Error(`Request failed (HTTP ${response.status}). 请求失败（HTTP ${response.status}）。`);
  }
  return payload;
}

/**
 * Verify the preview contract before enabling an explicit import confirmation.
 * 在启用明确的导入确认前，验证预览响应是否符合接口契约。
 */
export async function previewGscFile(file: File, scope: ScopeDeclaration, signal: AbortSignal): Promise<ImportPreview> {
  const body = new FormData();
  body.append("file", file);
  body.append("scope", JSON.stringify(scope));
  const payload = await requestJson("/imports/gsc/pages/preview", { method: "POST", body, signal });
  if (
    !isRecord(payload) ||
    payload.source !== "gsc_pages" ||
    payload.reporting_window !== "latest_28_days" ||
    !isReportingPeriod(payload) ||
    !isDateCoverage(payload) || !isReportScope(payload.report_scope) ||
    !(payload.detected_sheet === null || typeof payload.detected_sheet === "string") ||
    ![payload.total_rows, payload.valid_rows, payload.invalid_rows, payload.duplicate_rows].every(isCount) ||
    !isRecord(payload.column_mapping) ||
    !["url", "clicks", "impressions", "ctr", "position"].every(
      (key) => typeof (payload.column_mapping as Record<string, unknown>)[key] === "string",
    ) ||
    !Array.isArray(payload.errors) ||
    !payload.errors.every(
      (error) =>
        isRecord(error) &&
        isCount(error.row) &&
        typeof error.field === "string" &&
        typeof error.code === "string" &&
        typeof error.message === "string",
    ) ||
    !Array.isArray(payload.sample_rows) ||
    !payload.sample_rows.every((row) => isPageMetrics(row) && isRecord(row) && isCount(row.row)) ||
    typeof payload.can_apply !== "boolean" ||
    typeof payload.preview_hash !== "string" ||
    !/^[0-9a-f]{64}$/.test(payload.preview_hash) ||
    typeof payload.file_hash !== "string" || !/^[0-9a-f]{64}$/.test(payload.file_hash)
  ) {
    throw new Error("Unexpected import preview response. 导入预览响应格式不符合预期。");
  }
  return payload as ImportPreview;
}

/**
 * Resubmit the selected file, retained scope declaration, and bound preview fingerprint.
 * 重新提交所选文件、保留的范围声明及与之绑定的预览指纹。
 */
export async function applyGscFile(
  file: File,
  previewHash: string,
  scope: ScopeDeclaration,
  signal: AbortSignal,
): Promise<ImportResult> {
  const body = new FormData();
  body.append("file", file);
  body.append("confirmed", "true");
  body.append("preview_hash", previewHash);
  body.append("scope", JSON.stringify(scope));
  const payload = await requestJson("/imports/gsc/pages/apply", { method: "POST", body, signal });
  if (
    !isRecord(payload) ||
    ![payload.created_count, payload.updated_count, payload.skipped_count, payload.error_count].every(isCount) ||
    typeof payload.import_run_id !== "string" ||
    typeof payload.already_processed !== "boolean"
  ) {
    throw new Error("Unexpected import result response. 导入结果响应格式不符合预期。");
  }
  return payload as ImportResult;
}

/**
 * Retrieve a validated read-only page with explicit pagination metadata.
 * 获取经过验证的只读页面列表及明确的分页元数据。
 */
export async function listPages(
  page: number,
  pageSize: number,
  signal: AbortSignal,
): Promise<PagesResponse> {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  const payload = await requestJson(`/pages?${query}`, { method: "GET", signal });
  if (
    !isRecord(payload) ||
    !Array.isArray(payload.items) ||
    !payload.items.every((item) => isPageMetrics(item) && isRecord(item) && typeof item.id === "string") ||
    !isCount(payload.page) ||
    payload.page !== page ||
    !isCount(payload.page_size) ||
    payload.page_size !== pageSize ||
    !isCount(payload.total) ||
    !isCount(payload.total_pages)
  ) {
    throw new Error("Unexpected pages response. 页面列表响应格式不符合预期。");
  }
  return payload as PagesResponse;
}

export function requestErrorMessage(error: unknown): string {
  if (error instanceof Error && !["TypeError", "TimeoutError", "AbortError"].includes(error.name)) {
    return error.message;
  }
  return "Could not reach the API or the request timed out. Check the backend connection. 无法连接 API 或请求超时，请检查后端连接。";
}

/**
 * Display stored CTR fractions as percentages; unknown metrics stay visibly unknown.
 * 将已存储的 CTR 比例显示为百分比；未知指标保持明确的未知状态。
 */
export function formatMetric(value: string | number | null, percentage = false): string {
  if (value === null) return "—";
  const number = Number(value) * (percentage ? 100 : 1);
  return `${new Intl.NumberFormat("en", { maximumFractionDigits: 4 }).format(number)}${percentage ? "%" : ""}`;
}

/**
 * Exact report dates must be paired; unknown dates must remain explicitly absent.
 * 精确报告日期必须成对存在；未知日期必须保持明确缺失。
 */
export function isReportingPeriod(value: Record<string, unknown>): boolean {
  return value.period_status === "unknown"
    ? value.period_start === null && value.period_end === null
    : value.period_status === "exact" &&
        typeof value.period_start === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value.period_start) &&
        typeof value.period_end === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value.period_end) &&
        value.period_start <= value.period_end;
}
