"use client";

import Link from "next/link";
import { useCallback, useState, type FormEvent } from "react";
import { HistoryControls, HistoryPagination } from "@/components/history-pagination";
import { OpportunityCandidates } from "@/components/opportunity-candidates";
import { usePaginatedResource } from "@/lib/use-paginated-resource";
import { listPrioritizedOpportunities, PRIORITY_LABELS, type OpportunityEligibilitySummary, type OpportunityFilters,
  type PrioritizedOpportunityCandidate, type PrioritizedOpportunitiesResponse, type PriorityTier } from "@/lib/opportunity-prioritization-api";

const INPUT_LABELS: Record<string, string> = {
  previous_clicks: "Previous clicks / 前期点击", current_clicks: "Current clicks / 当期点击",
  clicks_absolute_change: "Exact click change / 精确点击变化",
  clicks_percentage_change_numerator: "Exact click percentage numerator / 精确点击百分比的分子",
  clicks_percentage_change_denominator: "Exact click percentage denominator / 精确点击百分比的分母",
  previous_impressions: "Previous impressions / 前期展示", current_impressions: "Current impressions / 当期展示",
  impressions_absolute_change: "Exact impression change / 精确展示变化",
  impressions_percentage_change_numerator: "Exact impression percentage numerator / 精确展示百分比的分子",
  impressions_percentage_change_denominator: "Exact impression percentage denominator / 精确展示百分比的分母",
  previous_ctr: "Previous CTR fraction / 前期 CTR 比例", current_ctr: "Current CTR fraction / 当期 CTR 比例",
  ctr_percentage_point_change: "Exact CTR change (pp) / 精确 CTR 变化（百分点）",
  previous_average_position: "Previous average position / 前期平均排名", current_average_position: "Current average position / 当期平均排名",
  average_position_change: "Exact position worsening / 精确排名恶化幅度",
};
const THRESHOLD_LABELS: Record<string, { label: string; unit: string }> = {
  minimum_previous_clicks: { label: "Previous clicks / 前期点击", unit: "" },
  minimum_click_loss: { label: "Absolute click loss / 点击损失数量", unit: "" },
  minimum_click_decline_percentage: { label: "Click decline / 点击下降幅度", unit: "%" },
  minimum_impressions: { label: "Both periods' impressions / 两期展示", unit: "" },
  minimum_ctr_decline_percentage_points: { label: "CTR decline / CTR 下降幅度", unit: " pp / 百分点" },
  minimum_average_position_worsening: { label: "Average position worsening / 平均排名恶化幅度", unit: "" },
  minimum_impressions_growth_percentage: { label: "Impression growth / 展示增长幅度", unit: "%" },
};
const GATE_LABELS: Record<string, string> = {
  insufficient_history: "Insufficient comparable reporting periods / 可比报告时间段不足",
  unknown_report_scope: "Uncertain report scope / 报告范围不确定",
  incompatible_report_scope: "Conflicting report scope / 报告范围冲突",
  unknown_reporting_dates: "Unknown exact reporting dates / 精确报告日期未知",
  incomplete_date_coverage: "Incomplete observed date coverage / 已观察日期覆盖不完整",
  unknown_date_coverage: "Unknown observed date coverage / 已观察日期覆盖未知",
  overlapping_comparison_periods: "Overlapping comparison periods / 对比时间段重叠",
  missing_metrics: "Missing comparison metrics / 对比指标缺失",
  zero_percentage_baseline: "Zero percentage baseline / 百分比基准为零",
  out_of_order_import: "Relevant out-of-order import / 相关导入乱序",
};

/**
 * Display exact inputs as supplied, separating priority heuristics from factual detection rules.
 * 原样显示精确输入，将优先级启发式与事实检测规则分开。
 */
function PriorityEvidence({ candidate }: { candidate: PrioritizedOpportunityCandidate }) {
  return <div className="priority-evidence">
    <p><span className="priority-label" data-priority-tier={candidate.priority_tier}>Priority / 优先级：{PRIORITY_LABELS[candidate.priority_tier]}</span></p>
    <p>{candidate.priority_message}</p>
    <details className="quality-details priority-details">
      <summary>Priority inputs and thresholds / 优先级输入与门槛</summary>
      <p>Rule version / 规则版本：<code>{candidate.priority_rule_version}</code><br />Reason code / 原因代码：<code>{candidate.priority_reason_code}</code></p>
      <h4>Exact prioritization inputs / 精确优先级输入</h4>
      <dl className="mapping-list">{Object.entries(candidate.priority_inputs).map(([key, value]) => (
        <div key={key}><dt>{INPUT_LABELS[key] ?? key}</dt><dd><code>{String(value)}</code></dd></div>
      ))}</dl>
      {["clicks", "impressions"].filter((metric) => Object.hasOwn(candidate.priority_inputs, `${metric}_percentage_change_numerator`)).map((metric) => (
        <p key={metric}>Exact percentage change / 精确百分比变化：<code>{String(candidate.priority_inputs[`${metric}_percentage_change_numerator`])} / {String(candidate.priority_inputs[`${metric}_percentage_change_denominator`])}</code> %</p>
      ))}
      <p>Tier boundaries use exact values, rather than rounded display percentages. 等级边界使用精确值，不使用舍入后的展示百分比。</p>
      {(["high", "medium"] as const).map((tier) => <div key={tier}>
        <h4>{PRIORITY_LABELS[tier]} thresholds / 门槛</h4>
        <p>All conditions are required. High is checked first; otherwise Medium, then Low. 必须满足全部条件。先检查高等级，再检查中等级，否则为低等级。</p>
        <dl className="mapping-list">{Object.entries(candidate.priority_thresholds[tier]).map(([key, value]) => (
          <div key={key}><dt>{THRESHOLD_LABELS[key]?.label ?? key}</dt><dd>≥ {String(value)}{THRESHOLD_LABELS[key]?.unit ?? ""}</dd></div>
        ))}</dl>
      </div>)}
      <p>These preliminary attention heuristics are not calibrated business-value or statistical-confidence assessments. 这些初步关注启发式并非经过校准的业务价值或统计置信度评估。</p>
    </details>
  </div>;
}

function EligibilitySummary({ summary }: { summary: OpportunityEligibilitySummary }) {
  const counts: [keyof Omit<OpportunityEligibilitySummary, "gate_reason_counts">, string][] = [
    ["analyzed_pages", "Imported pages analyzed / 已分析导入页面"], ["eligible_pages", "Evidence-eligible pages / 证据合格页面"],
    ["ineligible_pages", "Pages without eligible evidence / 证据不合格页面"], ["pages_with_candidates", "Pages with detected candidates / 检测到候选的页面"],
    ["ready_pages_without_candidates", "Ready pages with no thresholds met / 就绪但未满足门槛的页面"], ["detected_candidates", "Detected candidates / 已检测候选"],
  ];
  const reasons = Object.entries(summary.gate_reason_counts).filter(([, count]) => count > 0);
  return <section className="eligibility-summary" data-opportunity-summary aria-labelledby="eligibility-heading">
    <h3 id="eligibility-heading">Evidence and detection summary / 证据与检测摘要</h3>
    <p>Counts cover all pages in the applied site filter before tier filtering and pagination. 计数覆盖已应用站点筛选中的全部页面，先于等级筛选与分页。</p>
    <dl className="summary-grid">{counts.map(([key, label]) => <div key={key}><dt>{label}</dt><dd data-summary-count={key}>{summary[key]}</dd></div>)}</dl>
    {reasons.length > 0 && <>
      <h4>Unavailable evidence / 不可用证据</h4>
      <ul>{reasons.map(([code, count]) => <li key={code} data-eligibility-reason={code}>{GATE_LABELS[code] ?? code}：{count}</li>)}</ul>
      <p>A page may have several evidence limitations; reason counts overlap. 一个页面可能有多种证据限制；原因计数可以重叠。</p>
    </>}
    <p>No candidates does not establish that a site&apos;s SEO is healthy. 没有候选不能证明站点 SEO 健康。</p>
  </section>;
}

/**
 * Distinguish unavailable evidence, eligible zero detection, filters, and an empty result page.
 * 区分不可用证据、合格但零检测、筛选与空结果页。
 */
function EmptyResult({ data, filters }: { data: PrioritizedOpportunitiesResponse; filters: OpportunityFilters }) {
  if (data.summary.analyzed_pages === 0) return <p data-priority-empty="no_pages">
    {filters.siteId ? "No imported pages for the selected site. 所选站点没有已导入页面。" : "No imported pages. 尚无已导入页面。"} <Link href="/imports/gsc">Import GSC reports / 导入 GSC 报告</Link>.
  </p>;
  if (data.total === 0 && data.summary.detected_candidates > 0) return <p data-priority-empty="filtered">
    Candidates were detected, but none match this priority-tier filter. Change the tier filter to inspect them. 已检测到候选，但没有候选匹配当前优先级筛选。请更改等级筛选查看。
  </p>;
  if (data.summary.detected_candidates === 0) return <div data-priority-empty="no_candidates">
    {data.summary.ready_pages_without_candidates > 0 && <p>Ready evidence exists, but no configured detection thresholds were met. 已有就绪证据，但未满足任何已配置检测门槛。</p>}
    {data.summary.ineligible_pages > 0 && <p>Some pages cannot be analyzed for opportunities because their evidence is unavailable or limited. See the evidence reasons above. 部分页面的证据不可用或有限，无法检测机会。请查看上方证据原因。</p>}
  </div>;
  return <p data-priority-empty="page">No candidates on this result page. Use the pagination controls to return to available results. 此结果页没有候选，请使用分页控制返回已有结果。</p>;
}

function PrioritizedList({ filters }: { filters: OpportunityFilters }) {
  const load = useCallback((page: number, pageSize: number, signal: AbortSignal) => listPrioritizedOpportunities(page, pageSize, filters, signal), [filters]);
  const state = usePaginatedResource(load);
  const { data, loading, error } = state;
  return <>
    <p>Applied site / 已应用站点：<code>{filters.siteId || "All imported sites / 全部已导入站点"}</code> · Tier / 等级：{filters.priorityTier ? PRIORITY_LABELS[filters.priorityTier] : "All / 全部"}</p>
    <HistoryControls {...state} />
    {loading && <p role="status">Loading prioritized opportunities… / 正在加载优先级机会……</p>}
    {error && <p className="notice error" role="alert">{error}</p>}
    {!loading && !error && data && <>
      <EligibilitySummary summary={data.summary} />
      {data.items.length === 0 ? <EmptyResult data={data} filters={filters} /> : <OpportunityCandidates candidates={data.items}
        renderPriority={(candidate) => {
          const prioritized = candidate as PrioritizedOpportunityCandidate;
          return { tier: prioritized.priority_tier, content: <PriorityEvidence candidate={prioritized} /> };
        }} />}
      <HistoryPagination data={data} loading={loading} changePage={state.changePage} />
    </>}
  </>;
}

/**
 * Apply filters explicitly and remount pagination to cancel stale requests and return to page one.
 * 明确应用筛选，并重建分页以取消过期请求、返回第一页。
 */
export function PrioritizedOpportunities() {
  const [siteId, setSiteId] = useState("");
  const [tier, setTier] = useState<PriorityTier | "all">("all");
  const [filters, setFilters] = useState<OpportunityFilters>({ siteId: "", priorityTier: "" });
  const [filterError, setFilterError] = useState<string | null>(null);
  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedSite = siteId.trim().toLowerCase();
    if (normalizedSite && !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(normalizedSite)) {
      setFilterError("Enter a valid site UUID or leave the field blank. 请填写有效站点 UUID，或保留空白。");
      return;
    }
    setFilterError(null);
    const nextTier = tier === "all" ? "" : tier;
    if (filters.siteId !== normalizedSite || filters.priorityTier !== nextTier) {
      setFilters({ siteId: normalizedSite, priorityTier: nextTier });
    }
  }
  return <section className="card" data-opportunity-view="prioritized" aria-labelledby="prioritized-heading">
    <h2 id="prioritized-heading">Prioritized opportunities / 已分配优先级的机会</h2>
    <p>High → Medium → Low, then URL, opportunity type, and page ID. Pagination counts candidates; every independent signal is retained. 高 → 中 → 低，其次按 URL、机会类型与页面 ID 排序。分页统计候选；每个独立信号均保留。</p>
    <p>Priority means attention to an observed signal. It does not estimate business value, traffic recovery, or an appropriate SEO action. 优先级表示对已观察信号的关注程度，不估算业务价值、流量恢复或合适的 SEO 行动。</p>
    <form className="opportunity-filters" onSubmit={applyFilters} noValidate>
      <label htmlFor="opportunity-site-id">Optional site ID / 可选站点 ID
        <input id="opportunity-site-id" type="text" value={siteId} autoComplete="off" aria-describedby="site-filter-help"
          onChange={(event) => setSiteId(event.target.value)} placeholder="Site UUID / 站点 UUID" />
      </label>
      <label htmlFor="priority-tier">Priority tier / 优先级
        <select id="priority-tier" value={tier} onChange={(event) => setTier(event.target.value as PriorityTier | "all")}>
          <option value="all">All / 全部</option>{Object.entries(PRIORITY_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
      <button type="submit">Apply filters / 应用筛选</button>
    </form>
    <p id="site-filter-help"><small>Recorded site IDs appear in import history. Blank selects all imported sites, including unknown-site pages. 导入历史显示已记录站点 ID。空白表示全部已导入站点，包括站点未知的页面。</small></p>
    {filterError && <p className="notice error" role="alert">{filterError}</p>}
    <PrioritizedList key={`${filters.siteId}:${filters.priorityTier}`} filters={filters} />
  </section>;
}
