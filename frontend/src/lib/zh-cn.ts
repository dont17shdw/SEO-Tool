import type { QualityObservation } from "@/lib/data-quality";
import type { OpportunityCandidate } from "@/lib/opportunities-api";
import type { PrioritizedOpportunityCandidate } from "@/lib/opportunity-prioritization-api";

// Localize presentation only; stable API keys and all returned evidence remain unchanged.
// 仅本地化展示；稳定的 API 字段和所有返回的分析依据保持不变。
export const metricLabels = {
  clicks: "点击量",
  clicks_28d: "28 天点击量",
  impressions: "展示量",
  impressions_28d: "28 天展示量",
  ctr: "点击率（CTR）",
  position: "平均排名",
  average_position: "平均排名",
} as const;

export const fieldLabels = { url: "页面 URL", row: "整行数据", ...metricLabels } as const;
export const readinessLabels = { ready: "已就绪", limited: "证据有限", insufficient: "证据不足" } as const;
export const severityLabels = { info: "提示", warning: "警告", blocking: "阻止分析" } as const;
export const provenanceStatusLabels = { known: "来源已知", unknown: "来源未知", unavailable: "指标缺失" } as const;
export const opportunityLabels = {
  traffic_decline: "点击量下降",
  ctr_opportunity: "点击率下降机会",
  ranking_decline: "排名下降",
  impression_growth_gap: "展示增长与点击增长不匹配",
} as const;
export const priorityLabels = { high: "高优先级", medium: "中优先级", low: "低优先级" } as const;
export const searchTypeLabels = { web: "网页", image: "图片", video: "视频", news: "新闻" } as const;
export const deviceLabels = { mobile: "移动设备", desktop: "桌面设备", tablet: "平板设备" } as const;
export const filterDimensionLabels = {
  country: "国家（ISO 三字母代码）",
  device: "设备",
  search_appearance: "搜索结果呈现",
  query: "查询",
  page: "网页",
} as const;
export const filterOperatorLabels = {
  equals: "等于",
  not_equals: "不等于",
  contains: "包含",
  not_contains: "不包含",
  regex: "匹配正则表达式",
  not_regex: "不匹配正则表达式",
} as const;
export const coverageLabels = {
  complete: "日期覆盖完整",
  partial: "日期覆盖不完整",
  unknown: "日期覆盖未知",
} as const;
export const qualityCountLabels = {
  total_snapshots: "全部快照",
  exact_date_snapshots: "日期已知快照",
  unknown_date_snapshots: "日期未知快照",
  snapshots_with_missing_metrics: "指标缺失快照",
  distinct_exact_periods: "不同的精确报告周期",
  revision_periods: "存在修订的报告周期",
  compatible_exact_periods: "兼容的精确报告周期",
} as const;
export const currentMetricLabels = {
  clicks_28d: metricLabels.clicks_28d,
  impressions_28d: metricLabels.impressions_28d,
  ctr: metricLabels.ctr,
  average_position: metricLabels.average_position,
} as const;

const qualityReasonLabels: Record<string, string> = {
  insufficient_history: "可比历史不足",
  unknown_report_scope: "报告范围未知",
  incompatible_report_scope: "报告范围不兼容",
  unknown_reporting_dates: "报告日期未知",
  incomplete_date_coverage: "日期覆盖不完整",
  unknown_date_coverage: "日期覆盖未知",
  overlapping_comparison_periods: "对比周期重叠",
  missing_metrics: "指标缺失",
  zero_percentage_baseline: "百分比变化的基准为零",
  same_period_revisions: "同一周期存在多个版本",
  out_of_order_import: "报告未按时间顺序导入",
  overlapping_reporting_periods: "历史报告周期重叠",
  unknown_current_metric_provenance: "当前指标来源未知",
  current_state_not_single_snapshot: "当前指标来自多个快照",
};

export function metricLabel(field: string): string {
  return Object.hasOwn(metricLabels, field) ? metricLabels[field as keyof typeof metricLabels] : "其他指标";
}

export function fieldLabel(field: string): string {
  return Object.hasOwn(fieldLabels, field) ? fieldLabels[field as keyof typeof fieldLabels] : "其他字段";
}

export function qualityReasonLabel(code: string): string {
  return Object.hasOwn(qualityReasonLabels, code) ? qualityReasonLabels[code] : "其他分析依据提示";
}

function countText(evidence: Record<string, unknown>, key: string): string | null {
  const value = evidence[key];
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0 ? String(value) : null;
}

/**
 * Present stable observations from structured facts without trusting backend message text.
 * 根据结构化事实展示稳定的观察结果，不信任后端消息文本。
 */
export function qualityObservationMessage(observation: Pick<QualityObservation, "code" | "scope" | "evidence">): string {
  const { code, scope, evidence } = observation;
  const snapshots = countText(evidence, "snapshot_count");
  const subject = scope === "import" ? "此报告" : snapshots !== null ? `${snapshots} 个快照` : "部分历史快照";
  switch (code) {
    case "insufficient_history":
      return "已存储历史中尚无可用的兼容周期对比。需要两个日期精确、时长相等且报告范围无明确冲突的不同周期；只有一个报告周期时无法对比。";
    case "unknown_report_scope":
      return `${subject}的属性、搜索类型或完整筛选范围尚未得到完整证明。用户声明与工作簿观察结果分别记录，缺失信息保持未知。`;
    case "incompatible_report_scope":
      return "已存储报告存在明确冲突的范围信息。具有明确范围冲突的报告不会被选为对比周期。";
    case "unknown_reporting_dates":
      return `${subject}缺少可靠的精确报告日期，不能据此推断报告周期。`;
    case "incomplete_date_coverage":
      return `${subject}的已观察日期未证明完整、连续的 28 天覆盖。日期范围声明不能补足缺失的每日观察。`;
    case "unknown_date_coverage":
      return `${subject}缺少可靠的日期覆盖证据，日期覆盖情况保持未知。`;
    case "overlapping_comparison_periods":
      return "所选上一周期与当前周期存在重叠。当前对比仅用于描述变化，不能进入 SEO 机会检测。";
    case "missing_metrics":
      return `${subject}存在缺失指标。缺失值保持未知，不会按零处理。`;
    case "zero_percentage_baseline":
      return "上一周期的已知点击量或展示量为零，因此对应的百分比变化无法计算；绝对变化仍可显示。";
    case "same_period_revisions": {
      const periods = countText(evidence, "revision_period_count");
      const imports = countText(evidence, "revision_import_count");
      return scope === "import" && imports !== null
        ? `另外 ${imports} 个文件具有相同的精确报告日期范围，属于同一周期的不同导入版本。`
        : periods !== null
          ? `${periods} 个精确报告周期具有多个导入版本，不代表新增独立周期。`
          : "同一精确报告周期存在多个导入版本，不代表新增独立周期。";
    }
    case "out_of_order_import": {
      const affected = countText(evidence, "affected_snapshot_count");
      return affected !== null ? `${affected} 个快照的较早报告周期在较新报告证据之后导入。报告时间顺序与导入时间顺序不同。`
        : "较早报告周期在较新报告证据之后导入。报告时间顺序与导入时间顺序不同。";
    }
    case "overlapping_reporting_periods": {
      const imports = countText(evidence, "overlapping_import_count");
      return imports !== null ? `此报告周期与另外 ${imports} 个已导入周期重叠，不能将其视为互不重叠的独立报告。`
        : "已存储报告存在重叠的周期，不能将其视为互不重叠的独立报告。";
    }
    case "unknown_current_metric_provenance": {
      const metrics = countText(evidence, "unknown_metric_count");
      return `${metrics !== null ? `${metrics} 个` : "部分"}当前非空指标的来源尚未得到证明。不能据此指定来源快照或报告周期。`;
    }
    case "current_state_not_single_snapshot": {
      const count = countText(evidence, "distinct_snapshot_count");
      return `当前指标来自${count !== null ? ` ${count} 个` : "多个"}不同快照，不能将当前页面状态视为单一报告快照。`;
    }
    default:
      return "后端返回了一项分析依据提示，暂无对应的中文说明。请查看提示代码和已记录的分析依据，勿据此推断新的 SEO 结论。";
  }
}

// Remove insignificant trailing decimal zeros without recomputing returned measurements.
// 去除无意义的小数末尾零，不重新计算返回的测量值。
function valueText(value: string | number): string {
  const text = String(value);
  return /^[-+]?\d+\.\d+$/.test(text) ? text.replace(/0+$/, "").replace(/\.$/, "") : text;
}

const candidateReasonCodes = {
  traffic_decline: "clicks_decline_threshold_met",
  ctr_opportunity: "ctr_declined_with_comparable_visibility",
  ranking_decline: "average_position_worsening_threshold_met",
  impression_growth_gap: "impressions_grew_faster_than_clicks",
} as const;

/**
 * Describe returned detection evidence; no browser-side rule evaluation is performed.
 * 描述返回的检测依据；不在浏览器端评估规则。
 */
export function candidateExplanation(candidate: OpportunityCandidate): string {
  const { opportunity_type: type, evidence } = candidate;
  if (candidate.reason_code !== candidateReasonCodes[type]) {
    return "后端已返回该页面的 SEO 机会信号，暂无对应的中文原因说明。请查看原始指标、检测阈值和原因代码。";
  }
  const previous = evidence.previous, current = evidence.current, changes = evidence.changes, thresholds = evidence.thresholds;
  const v = valueText;
  switch (type) {
    case "traffic_decline":
      return `该页面点击量从上一周期的 ${v(previous.clicks)} 次降至当前周期的 ${v(current.clicks)} 次，变化 ${v(changes.clicks_absolute_change)} 次（${v(changes.clicks_percentage_change)}%）。已达到检测阈值：上一周期点击量 ≥ ${v(thresholds.minimum_previous_clicks)} 次、绝对变化 ≤ ${v(thresholds.maximum_clicks_absolute_change)} 次、百分比变化 ≤ ${v(thresholds.maximum_clicks_percentage_change)}%。`;
    case "ctr_opportunity":
      return `该页面点击率变化 ${v(changes.ctr_percentage_point_change)} 个百分点，平均排名变化 ${v(changes.average_position_change)}，展示量变化 ${v(changes.impressions_percentage_change)}%。已达到检测阈值：两个周期展示量均 ≥ ${v(thresholds.minimum_impressions)} 次、点击率变化 ≤ ${v(thresholds.maximum_ctr_percentage_point_change)} 个百分点、平均排名变化 ≤ ${v(thresholds.maximum_average_position_change)}、展示量变化 ≥ ${v(thresholds.minimum_impressions_percentage_change)}%。`;
    case "ranking_decline":
      return `该页面平均排名从上一周期的 ${v(previous.average_position)} 变为当前周期的 ${v(current.average_position)}，变化 ${v(changes.average_position_change)}。数值增大表示排名变差。已达到检测阈值：两个周期展示量均 ≥ ${v(thresholds.minimum_impressions)} 次、平均排名变化 ≥ ${v(thresholds.minimum_average_position_change)}，当前展示量 > ${v(thresholds.minimum_current_impressions_exclusive)} 次。`;
    case "impression_growth_gap":
      return `该页面展示量变化 ${v(changes.impressions_percentage_change)}%，点击量变化 ${v(changes.clicks_percentage_change)}%，点击率变化 ${v(changes.ctr_percentage_point_change)} 个百分点。已达到检测阈值：两个周期展示量均 ≥ ${v(thresholds.minimum_impressions)} 次、展示量变化 ≥ ${v(thresholds.minimum_impressions_percentage_change)}%、点击量变化 < ${v(thresholds.maximum_clicks_percentage_change_exclusive)}%、点击率变化 ≤ ${v(thresholds.maximum_ctr_percentage_point_change)} 个百分点。`;
  }
}

/**
 * Describe supplied tier thresholds without testing measurements against them.
 * 描述已提供的等级阈值，不将测量值与阈值进行判定。
 */
function priorityThresholdText(candidate: PrioritizedOpportunityCandidate, tier: "high" | "medium"): string {
  const thresholds = candidate.priority_thresholds[tier], v = valueText;
  switch (candidate.opportunity_type) {
    case "traffic_decline":
      return `上一周期点击量 ≥ ${v(thresholds.minimum_previous_clicks)} 次、减少量 ≥ ${v(thresholds.minimum_click_loss)} 次、下降比例 ≥ ${v(thresholds.minimum_click_decline_percentage)}%`;
    case "ctr_opportunity":
      return `两个周期展示量均 ≥ ${v(thresholds.minimum_impressions)} 次、点击率下降 ≥ ${v(thresholds.minimum_ctr_decline_percentage_points)} 个百分点`;
    case "ranking_decline":
      return `两个周期展示量均 ≥ ${v(thresholds.minimum_impressions)} 次、平均排名变差 ≥ ${v(thresholds.minimum_average_position_worsening)}`;
    case "impression_growth_gap":
      return `两个周期展示量均 ≥ ${v(thresholds.minimum_impressions)} 次、展示量增长 ≥ ${v(thresholds.minimum_impressions_growth_percentage)}%、点击率下降 ≥ ${v(thresholds.minimum_ctr_decline_percentage_points)} 个百分点`;
  }
}

/**
 * Explain the server-returned tier using its exact inputs and configured thresholds.
 * 使用准确输入及配置阈值解释服务端返回的等级。
 * Rounded descriptive percentages are display evidence, never browser priority calculations.
 * 已舍入的描述性百分比仅用于展示依据，绝不用于浏览器优先级计算。
 */
export function priorityExplanation(candidate: PrioritizedOpportunityCandidate): string {
  const { opportunity_type: type, priority_tier: tier, priority_inputs: inputs } = candidate;
  const expectedCode = `${type}_${tier === "low" ? "low_higher_tier_thresholds_not_met" : `${tier}_thresholds_met`}`;
  if (candidate.priority_reason_code !== expectedCode) {
    return "此信号的优先级由后端规则返回，暂无对应的中文原因说明。请查看规则版本、准确输入和阈值。";
  }
  const v = valueText;
  let measurement: string;
  switch (type) {
    case "traffic_decline":
      measurement = `上一周期点击量为 ${v(inputs.previous_clicks)} 次，当前周期为 ${v(inputs.current_clicks)} 次，变化 ${v(inputs.clicks_absolute_change)} 次（${v(candidate.evidence.changes.clicks_percentage_change)}%）。`;
      break;
    case "ctr_opportunity":
      measurement = `展示量从 ${v(inputs.previous_impressions)} 次变为 ${v(inputs.current_impressions)} 次，点击率变化 ${v(inputs.ctr_percentage_point_change)} 个百分点。`;
      break;
    case "ranking_decline":
      measurement = `展示量从 ${v(inputs.previous_impressions)} 次变为 ${v(inputs.current_impressions)} 次，平均排名从 ${v(inputs.previous_average_position)} 变为 ${v(inputs.current_average_position)}，变差 ${v(inputs.average_position_change)}。`;
      break;
    case "impression_growth_gap":
      measurement = `展示量从 ${v(inputs.previous_impressions)} 次变为 ${v(inputs.current_impressions)} 次，变化 ${v(inputs.impressions_absolute_change)} 次（${v(candidate.evidence.changes.impressions_percentage_change)}%），点击率变化 ${v(inputs.ctr_percentage_point_change)} 个百分点。`;
      break;
  }
  return tier === "low" ? `${measurement}此信号已达到机会检测阈值，但未同时满足中优先级的全部条件，因此标为低优先级。中优先级条件为：${priorityThresholdText(candidate, "medium")}。`
    : `${measurement}根据 ${candidate.priority_rule_version} 规则，满足${priorityLabels[tier]}的全部条件：${priorityThresholdText(candidate, tier)}。`;
}

export function comparisonUnavailableMessage(): string {
  return "暂无可用的周期对比。需要两个不同的报告周期，且日期精确、页面与数据源及报告窗口一致、时长相等、报告范围无明确冲突。";
}

const importRowErrors: Record<string, string> = {
  missing_url: "缺少页面 URL，请填写完整的网址。",
  invalid_url: "页面 URL 无效，请使用带有有效主机名的完整 http:// 或 https:// 网址。",
  invalid_clicks: "点击量必须是 0 至 9007199254740991 之间的整数。",
  invalid_impressions: "展示量必须是 0 至 9007199254740991 之间的整数。",
  invalid_ctr: "点击率必须为 0 至 1 的小数，或 0% 至 100% 的百分数。",
  invalid_position: "平均排名必须为 0 至 999999.9999 之间的数值。",
  duplicate_url: "同一页面 URL 出现多次。请删除重复行后重新预览。",
  unexpected_columns: "此行的数据列多于标题列，请检查 CSV 分隔符及引号。",
};

export function importRowErrorMessage(code: string): string {
  return Object.hasOwn(importRowErrors, code) ? importRowErrors[code] : "此行未通过校验，请检查对应字段及错误代码。";
}

const scopeIssues: Record<string, string> = {
  formula_scope_metadata: "范围信息中包含未计算的公式，无法作为可靠的工作簿证据。",
  unsupported_scope_row_shape: "部分范围信息行的格式无法识别。",
  unsupported_filter_metadata: "部分筛选信息无法确认其条件，报告范围保持不确定。",
  unparsed_property_id_metadata: "无法可靠解析工作簿中的属性标识。",
  unparsed_search_type_metadata: "无法可靠解析工作簿中的搜索类型。",
  unparsed_country_filter: "无法可靠解析工作簿中的国家筛选条件。",
  unparsed_device_filter: "无法可靠解析工作簿中的设备筛选条件。",
  unparsed_search_appearance_filter: "无法可靠解析工作簿中的搜索结果呈现筛选条件。",
  unparsed_query_filter: "无法可靠解析工作簿中的查询筛选条件。",
  unparsed_page_filter: "无法可靠解析工作簿中的网页筛选条件。",
};

export function scopeIssueLabel(code: string): string {
  return Object.hasOwn(scopeIssues, code) ? scopeIssues[code] : "部分工作簿范围信息无法可靠解析，请查看原始证据。";
}

const apiErrors: Record<string, string> = {
  database_unavailable: "数据服务暂时不可用，请稍后重试。",
  page_not_found: "未找到该页面，请返回网站页面列表重试。",
  import_not_found: "未找到该导入记录，请刷新导入历史重试。",
  invalid_report_scope: "报告范围声明无效，请检查属性标识、搜索类型及筛选条件。",
  confirmation_required: "请先确认导入预览，再提交导入。",
  preview_changed: "文件、报告范围或预览内容已改变，请重新预览并确认后再导入。",
  invalid_import: "文件含有无效或重复数据，请修正预览中列出的错误后重新上传。",
  ambiguous_columns: "多个列对应同一指标，无法确定应使用哪一列，请检查标题列。",
  ambiguous_pages_sheet: "存在多个可能的网页数据工作表，无法确定来源，请使用清晰的 GSC 网页导出文件。",
  empty_file: "文件或网页工作表为空，请上传包含网页数据的 GSC 导出文件。",
  file_too_large: "文件超出大小限制：上传文件最多 5 MiB，解压后的 XLSX 最多 50 MiB。",
  malformed_csv: "无法读取 CSV，请检查 UTF-8 编码、分隔符及引号。",
  malformed_xlsx: "无法读取 XLSX 工作簿，请重新从 GSC 导出有效的文件。",
  missing_performance_columns: "缺少可识别的 GSC 表现指标列，请确认包含点击量、展示量、点击率和平均排名。",
  missing_url_column: "缺少可识别的网页 URL 列，请上传 GSC 网页表现导出文件。",
  pages_sheet_missing: "未找到具有有效网页 URL 和表现指标的网页工作表。",
  too_many_rows: "工作表行数超出限制，单个工作表最多支持 10000 行。",
  unsupported_file_type: "文件格式不受支持，请选择 GSC 网页表现 CSV 或 XLSX 导出文件。",
  unsupported_reporting_window: "请选择最近 28 天报告，或明确且恰为 28 天的自定义日期范围。仅有“自定义”标签时，工作簿必须独立提供 28 个不同且连续的已观察日期。",
  conflicting_reporting_dates: "工作簿中的报告日期证据存在冲突：自定义日期范围不一致，或已观察日期超出声明范围。请核对文件后重新导出。",
  conflicting_scope_metadata: "工作簿中的属性、搜索类型或筛选条件互相冲突，请核对源报告。",
  scope_declaration_conflict: "声明的报告范围与工作簿观察证据冲突，请核对属性、搜索类型及筛选条件。",
};

/**
 * Only locally constructed presentation errors may expose their message to the UI.
 * 只有在本地构造的展示错误才能向界面公开其消息。
 */
export class ChineseUiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ChineseUiError";
  }
}

/**
 * Map stable error codes and HTTP status; never render raw backend details or paths.
 * 映射稳定的错误代码及 HTTP 状态；绝不展示原始后端详情或路径。
 */
export function apiErrorMessage(code: unknown, status: number, path = ""): string {
  if (typeof code === "string" && Object.hasOwn(apiErrors, code)) return apiErrors[code];
  if (status === 422) return path.startsWith("/imports/gsc/")
    ? "上传内容或报告范围声明无效，请检查文件及表单信息后重试。"
    : "请求参数无效，请检查页码或筛选条件后重试。";
  if (status === 404) return "未找到所请求的内容，请刷新页面后重试。";
  if (status >= 500) return `后端服务暂时不可用（HTTP ${status}），请稍后重试。`;
  return `请求未成功（HTTP ${status}），请检查输入或稍后重试。`;
}

/**
 * Keep unexpected errors generic so raw network or server details cannot reach the interface.
 * 对未知错误使用通用说明，避免原始网络或服务端详情进入界面。
 */
export function trustedRequestErrorMessage(error: unknown): string {
  if (error instanceof ChineseUiError) return error.message;
  if (error instanceof Error && ["TypeError", "TimeoutError", "AbortError"].includes(error.name)) {
    return "无法连接后端服务，或请求已超时。请检查后端连接后重试。";
  }
  return "请求未能完成，请稍后重试；若问题持续，请检查后端连接。";
}
