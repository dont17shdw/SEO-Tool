import { isCount, isRecord } from "@/lib/gsc-api";

export const SEARCH_TYPE_LABELS = {
  web: "Web / 网页",
  image: "Image / 图片",
  video: "Video / 视频",
  news: "News / 新闻",
} as const;

export const FILTER_DIMENSION_LABELS = {
  country: "Country (ISO 3-letter code) / 国家（ISO 三字母代码）",
  device: "Device / 设备",
  search_appearance: "Search appearance / 搜索结果呈现",
  query: "Query / 查询",
  page: "Page / 网页",
} as const;

export const FILTER_OPERATOR_LABELS = {
  equals: "Equals / 等于",
  not_equals: "Does not equal / 不等于",
  contains: "Contains / 包含",
  not_contains: "Does not contain / 不包含",
  regex: "Matches regex / 匹配正则表达式",
  not_regex: "Does not match regex / 不匹配正则表达式",
} as const;

export const COVERAGE_LABELS = {
  complete: "Complete observed 28-day coverage / 已观察完整 28 天覆盖",
  partial: "Partial observed coverage / 已观察部分覆盖",
  unknown: "Unknown coverage / 覆盖未知",
} as const;

export type ScopeFilter = {
  dimension: keyof typeof FILTER_DIMENSION_LABELS;
  operator: keyof typeof FILTER_OPERATOR_LABELS;
  value: string;
};

export type ScopeDeclaration = {
  property_id: string | null;
  search_type: keyof typeof SEARCH_TYPE_LABELS | null;
  filters: ScopeFilter[] | null;
};

export type ReportScope = {
  property_id: string | null;
  property_status: "known" | "unknown";
  site_identifier: string | null;
  search_type: keyof typeof SEARCH_TYPE_LABELS | null;
  filters: ScopeFilter[];
  filters_complete: boolean;
  status: "known" | "unknown";
  fingerprint: string;
  workbook_observed: ScopeDeclaration;
  user_declared: ScopeDeclaration;
  issues: string[];
};

export type DateCoverage = {
  observed_date_count: number | null;
  dates_consecutive: boolean | null;
  coverage_status: keyof typeof COVERAGE_LABELS;
};

function isSearchType(value: unknown): boolean {
  return value === null || (typeof value === "string" && Object.hasOwn(SEARCH_TYPE_LABELS, value));
}

function isFilter(value: unknown): value is ScopeFilter {
  return isRecord(value) && typeof value.dimension === "string" && Object.hasOwn(FILTER_DIMENSION_LABELS, value.dimension) &&
    typeof value.operator === "string" && Object.hasOwn(FILTER_OPERATOR_LABELS, value.operator) &&
    typeof value.value === "string" && value.value.trim().length > 0 &&
    (["query", "page"].includes(value.dimension) || ["equals", "not_equals"].includes(value.operator)) &&
    (value.dimension !== "country" || /^[A-Z]{3}$/.test(value.value)) &&
    (value.dimension !== "device" || ["mobile", "desktop", "tablet"].includes(value.value));
}

function isFilterList(value: unknown): value is ScopeFilter[] {
  return Array.isArray(value) && value.every(isFilter) && new Set(value.map((filter) => filter.dimension)).size === value.length;
}

function isDeclaration(value: unknown): value is ScopeDeclaration {
  return isRecord(value) && (value.property_id === null || (typeof value.property_id === "string" && value.property_id.trim().length > 0)) &&
    isSearchType(value.search_type) && (value.filters === null || isFilterList(value.filters));
}

/**
 * Validate recorded scope evidence without deriving identity from page URLs or dates.
 * 校验已记录范围证据，不根据页面 URL 或日期推导身份。
 */
export function isReportScope(value: unknown): value is ReportScope {
  if (!isRecord(value) || !(value.property_id === null || (typeof value.property_id === "string" && value.property_id.trim().length > 0)) ||
    value.property_status !== (value.property_id === null ? "unknown" : "known") || value.site_identifier !== value.property_id ||
    !isSearchType(value.search_type) || !isFilterList(value.filters) ||
    typeof value.filters_complete !== "boolean" || typeof value.fingerprint !== "string" || !/^[0-9a-f]{64}$/.test(value.fingerprint) ||
    !isDeclaration(value.workbook_observed) || !isDeclaration(value.user_declared) ||
    !Array.isArray(value.issues) || !value.issues.every((issue) => typeof issue === "string")) return false;
  return value.status === (value.property_id !== null && value.search_type !== null && value.filters_complete ? "known" : "unknown");
}

/**
 * Keep absent coverage unknown and require observed facts for complete 28-day coverage.
 * 将缺失覆盖保持为未知，并要求已观察事实才能标记完整 28 天覆盖。
 */
export function isDateCoverage(value: unknown): boolean {
  if (!isRecord(value)) return false;
  const hasPeriod = Object.hasOwn(value, "period_start") || Object.hasOwn(value, "period_end");
  let inclusiveDays: number | null = null;
  if (hasPeriod) {
    if (value.period_start === null && value.period_end === null) {
      if (value.coverage_status !== "unknown") return false;
    } else {
      const isCalendarDate = (date: unknown): date is string => typeof date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(date) &&
        Number.isFinite(Date.parse(date)) && new Date(date).toISOString().slice(0, 10) === date;
      if (!isCalendarDate(value.period_start) || !isCalendarDate(value.period_end) || value.period_start > value.period_end) return false;
      inclusiveDays = (Date.parse(value.period_end) - Date.parse(value.period_start)) / 86_400_000 + 1;
    }
  }
  if (value.coverage_status === "unknown") return value.observed_date_count === null && value.dates_consecutive === null;
  return (value.coverage_status === "partial" || value.coverage_status === "complete") &&
    isCount(value.observed_date_count) && value.observed_date_count > 0 && typeof value.dates_consecutive === "boolean" &&
    (inclusiveDays === null || (value.observed_date_count <= inclusiveDays && value.dates_consecutive === (value.observed_date_count === inclusiveDays))) &&
    value.coverage_status === (value.observed_date_count === 28 && value.dates_consecutive ? "complete" : "partial");
}

export function formatCoverage(coverage: DateCoverage): string {
  return coverage.coverage_status === "unknown" ? COVERAGE_LABELS.unknown :
    `${coverage.observed_date_count} / 28 observed dates / 已观察日期 · ${COVERAGE_LABELS[coverage.coverage_status]}`;
}

export function formatFilter(filter: ScopeFilter): string {
  return `${FILTER_DIMENSION_LABELS[filter.dimension]} · ${FILTER_OPERATOR_LABELS[filter.operator]} · ${filter.value}`;
}
