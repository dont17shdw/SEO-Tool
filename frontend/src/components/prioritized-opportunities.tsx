"use client";

import Link from "next/link";
import { useCallback, useState, type FormEvent } from "react";
import { HistoryControls, HistoryPagination } from "@/components/history-pagination";
import { OpportunityCandidates } from "@/components/opportunity-candidates";
import { usePaginatedResource } from "@/lib/use-paginated-resource";
import { listPrioritizedOpportunities, PRIORITY_LABELS, type OpportunityEligibilitySummary, type OpportunityFilters,
  type PrioritizedOpportunityCandidate, type PrioritizedOpportunitiesResponse, type PriorityTier } from "@/lib/opportunity-prioritization-api";
import { priorityExplanation, qualityReasonLabel } from "@/lib/zh-cn";

const INPUT_LABELS: Record<string, string> = {
  previous_clicks: "上一周期点击量", current_clicks: "当前周期点击量",
  clicks_absolute_change: "精确点击量变化",
  clicks_percentage_change_numerator: "精确点击量百分比变化的分子",
  clicks_percentage_change_denominator: "精确点击量百分比变化的分母",
  previous_impressions: "上一周期展示量", current_impressions: "当前周期展示量",
  impressions_absolute_change: "精确展示量变化",
  impressions_percentage_change_numerator: "精确展示量百分比变化的分子",
  impressions_percentage_change_denominator: "精确展示量百分比变化的分母",
  previous_ctr: "上一周期点击率（原始比例）", current_ctr: "当前周期点击率（原始比例）",
  ctr_percentage_point_change: "精确点击率变化（百分点）",
  previous_average_position: "上一周期平均排名", current_average_position: "当前周期平均排名",
  average_position_change: "精确平均排名变化",
};
const THRESHOLD_LABELS: Record<string, { label: string; unit: string }> = {
  minimum_previous_clicks: { label: "上一周期点击量", unit: "" },
  minimum_click_loss: { label: "点击量减少数量", unit: "" },
  minimum_click_decline_percentage: { label: "点击量下降幅度", unit: "%" },
  minimum_impressions: { label: "两个周期的展示量", unit: "" },
  minimum_ctr_decline_percentage_points: { label: "点击率下降幅度", unit: " 个百分点" },
  minimum_average_position_worsening: { label: "平均排名变差幅度", unit: "" },
  minimum_impressions_growth_percentage: { label: "展示量增长幅度", unit: "%" },
};

/**
 * Display exact inputs as supplied, separating priority heuristics from factual detection rules.
 * 原样显示精确输入，将优先级启发式与事实检测规则分开。
 */
function PriorityEvidence({ candidate }: { candidate: PrioritizedOpportunityCandidate }) {
  return <div className="priority-evidence">
    <p><span className="priority-label" data-priority-tier={candidate.priority_tier}>优先级：{PRIORITY_LABELS[candidate.priority_tier]}</span></p>
    <p>{priorityExplanation(candidate)}</p>
    <details className="quality-details priority-details">
      <summary>优先级分析依据与规则阈值</summary>
      <p>规则版本：<code>{candidate.priority_rule_version}</code><br />优先级原因代码：<code>{candidate.priority_reason_code}</code></p>
      <h4>优先级计算的精确输入</h4>
      <dl className="mapping-list">{Object.entries(candidate.priority_inputs).map(([key, value]) => (
        <div key={key}><dt>{INPUT_LABELS[key] ?? <>其他输入（<code>{key}</code>）</>}</dt><dd><code>{String(value)}</code></dd></div>
      ))}</dl>
      {["clicks", "impressions"].filter((metric) => Object.hasOwn(candidate.priority_inputs, `${metric}_percentage_change_numerator`)).map((metric) => (
        <p key={metric}>精确百分比变化：<code>{String(candidate.priority_inputs[`${metric}_percentage_change_numerator`])} / {String(candidate.priority_inputs[`${metric}_percentage_change_denominator`])}</code> %</p>
      ))}
      <p>优先级边界使用精确输入值判断。此处保留精确比率；展示百分比的舍入不会改变等级。</p>
      {(["high", "medium"] as const).map((tier) => <div key={tier}>
        <h4>{PRIORITY_LABELS[tier]}规则阈值</h4>
        <p>同一等级须同时满足全部条件。服务端先判断高优先级，再判断中优先级，其余已检测到的信号归为低优先级。</p>
        <dl className="mapping-list">{Object.entries(candidate.priority_thresholds[tier]).map(([key, value]) => (
          <div key={key}><dt>{THRESHOLD_LABELS[key]?.label ?? <>其他阈值（<code>{key}</code>）</>}</dt><dd>≥ {String(value)}{THRESHOLD_LABELS[key]?.unit ?? ""}</dd></div>
        ))}</dl>
      </div>)}
      <p>这些优先级规则仅表示对事实信号的关注程度，尚未经过真实站点校准，不是业务价值或统计置信度评估。</p>
    </details>
  </div>;
}

function EligibilitySummary({ summary }: { summary: OpportunityEligibilitySummary }) {
  const counts: [keyof Omit<OpportunityEligibilitySummary, "gate_reason_counts">, string][] = [
    ["analyzed_pages", "已分析页面"], ["eligible_pages", "分析证据已就绪的页面"],
    ["ineligible_pages", "分析证据尚未就绪的页面"], ["pages_with_candidates", "检测到 SEO 机会的页面"],
    ["ready_pages_without_candidates", "证据已就绪但未达到检测阈值的页面"], ["detected_candidates", "已检测到的 SEO 机会"],
  ];
  const reasons = Object.entries(summary.gate_reason_counts).filter(([, count]) => count > 0);
  return <section className="eligibility-summary" data-opportunity-summary aria-labelledby="eligibility-heading">
    <h3 id="eligibility-heading">分析依据与检测摘要</h3>
    <p>以下统计覆盖所选站点的全部页面，不受优先级筛选或当前分页影响。</p>
    <dl className="summary-grid">{counts.map(([key, label]) => <div key={key}><dt>{label}</dt><dd data-summary-count={key}>{summary[key]}</dd></div>)}</dl>
    {reasons.length > 0 && <>
      <h4>尚未就绪的分析依据</h4>
      <ul>{reasons.map(([code, count]) => <li key={code} data-eligibility-reason={code}>{qualityReasonLabel(code)}：{count}</li>)}</ul>
      <details className="quality-details"><summary>分析限制的原因代码</summary>
        <ul>{reasons.map(([code, count]) => <li key={code}><code>{code}</code>：{count}</li>)}</ul>
      </details>
      <p>同一页面可能存在多种证据限制，因此各原因的页面计数可能重叠。</p>
    </>}
    <p>未检测到 SEO 机会，并不能证明站点的 SEO 状况良好。</p>
  </section>;
}

/**
 * Distinguish unavailable evidence, eligible zero detection, filters, and an empty result page.
 * 区分不可用证据、合格但零检测、筛选与空结果页。
 */
function EmptyResult({ data, filters }: { data: PrioritizedOpportunitiesResponse; filters: OpportunityFilters }) {
  if (data.summary.analyzed_pages === 0) return <p data-priority-empty="no_pages">
    {filters.siteId ? "所选站点尚无已导入页面。" : "尚无已导入页面。"} <Link href="/imports/gsc">导入 GSC 数据</Link>。
  </p>;
  if (data.total === 0 && data.summary.detected_candidates > 0) return <p data-priority-empty="filtered">
    已检测到 SEO 机会，但没有结果匹配当前优先级筛选。请选择其他优先级或全部优先级查看。
  </p>;
  if (data.summary.detected_candidates === 0) return <div data-priority-empty="no_candidates">
    {data.summary.ready_pages_without_candidates > 0 && <p>部分页面的分析证据已就绪，但未达到任何已配置的检测规则阈值。</p>}
    {data.summary.ineligible_pages > 0 && <p>部分页面因证据不足或证据有限，暂时无法检测 SEO 机会。请查看上方列出的证据限制。</p>}
  </div>;
  return <p data-priority-empty="page">当前结果页没有 SEO 机会，请使用分页控件返回有结果的页面。</p>;
}

function PrioritizedList({ filters }: { filters: OpportunityFilters }) {
  const load = useCallback((page: number, pageSize: number, signal: AbortSignal) => listPrioritizedOpportunities(page, pageSize, filters, signal), [filters]);
  const state = usePaginatedResource(load);
  const { data, loading, error } = state;
  return <>
    <p>当前站点筛选：<code>{filters.siteId || "全部已导入站点"}</code> · 优先级筛选：{filters.priorityTier ? PRIORITY_LABELS[filters.priorityTier] : "全部优先级"}</p>
    <HistoryControls {...state} />
    {loading && <p role="status">正在加载 SEO 机会优先级……</p>}
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
      setFilterError("请输入有效的站点 UUID；留空可查看全部站点。");
      return;
    }
    setFilterError(null);
    const nextTier = tier === "all" ? "" : tier;
    if (filters.siteId !== normalizedSite || filters.priorityTier !== nextTier) {
      setFilters({ siteId: normalizedSite, priorityTier: nextTier });
    }
  }
  return <section className="card" data-opportunity-view="prioritized" aria-labelledby="prioritized-heading">
    <h2 id="prioritized-heading">SEO 机会优先级</h2>
    <p>按高、中、低优先级排列；同一等级按 URL、机会类型与页面 ID 排序。分页按 SEO 机会计数，同一页面的多个独立信号分别保留。</p>
    <p>优先级表示对已观察信号的关注程度，不估算业务价值、流量恢复，也不提供 SEO 行动建议。</p>
    <form className="opportunity-filters" onSubmit={applyFilters} noValidate>
      <label htmlFor="opportunity-site-id">站点 UUID（选填）
        <input id="opportunity-site-id" type="text" value={siteId} autoComplete="off" aria-describedby="site-filter-help"
          onChange={(event) => setSiteId(event.target.value)} placeholder="输入站点 UUID" />
      </label>
      <label htmlFor="priority-tier">优先级筛选
        <select id="priority-tier" value={tier} onChange={(event) => setTier(event.target.value as PriorityTier | "all")}>
          <option value="all">全部优先级</option>{Object.entries(PRIORITY_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
      <button type="submit">应用筛选</button>
    </form>
    <p id="site-filter-help"><small>站点 UUID 可在导入历史中查看。留空表示全部已导入站点，包括尚未记录站点身份的页面。</small></p>
    {filterError && <p className="notice error" role="alert">{filterError}</p>}
    <PrioritizedList key={`${filters.siteId}:${filters.priorityTier}`} filters={filters} />
  </section>;
}
