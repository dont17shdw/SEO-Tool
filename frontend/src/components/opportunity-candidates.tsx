import Link from "next/link";
import type { ReactNode } from "react";
import { formatMetric } from "@/lib/gsc-api";
import { formatChange } from "@/lib/history-api";
import { OPPORTUNITY_LABELS, type EvidenceValues, type OpportunityCandidate, type PageOpportunityAnalysis } from "@/lib/opportunities-api";

const METRIC_LABELS: Record<string, string> = {
  clicks: "Clicks / 点击", impressions: "Impressions / 展示", ctr: "CTR / 点击率", average_position: "Average position / 平均排名",
};

const CHANGE_LABELS: Record<string, { label: string; unit: string }> = {
  clicks_absolute_change: { label: "Click change / 点击变化", unit: "" },
  clicks_percentage_change: { label: "Click percentage change / 点击百分比变化", unit: "%" },
  impressions_absolute_change: { label: "Impression change / 展示变化", unit: "" },
  impressions_percentage_change: { label: "Impression percentage change / 展示百分比变化", unit: "%" },
  ctr_percentage_point_change: { label: "CTR change / CTR 变化", unit: " pp / 百分点" },
  average_position_change: { label: "Average position change / 平均排名变化", unit: "" },
};

const THRESHOLD_LABELS: Record<string, { label: string; operator: string; unit: string }> = {
  minimum_previous_clicks: { label: "Previous clicks / 前期点击", operator: "≥", unit: "" },
  maximum_clicks_absolute_change: { label: "Click change / 点击变化", operator: "≤", unit: "" },
  maximum_clicks_percentage_change: { label: "Click percentage change / 点击百分比变化", operator: "≤", unit: "%" },
  minimum_impressions: { label: "Both periods' impressions / 两期展示", operator: "≥", unit: "" },
  maximum_ctr_percentage_point_change: { label: "CTR change / CTR 变化", operator: "≤", unit: " pp / 百分点" },
  maximum_average_position_change: { label: "Average position change / 平均排名变化", operator: "≤", unit: "" },
  minimum_impressions_percentage_change: { label: "Impression percentage change / 展示百分比变化", operator: "≥", unit: "%" },
  minimum_average_position_change: { label: "Average position change / 平均排名变化", operator: "≥", unit: "" },
  minimum_current_impressions_exclusive: { label: "Current impressions / 当期展示", operator: ">", unit: "" },
  maximum_clicks_percentage_change_exclusive: { label: "Click percentage change / 点击百分比变化", operator: "<", unit: "%" },
};

function Changes({ values }: { values: EvidenceValues }) {
  return <dl className="mapping-list">{Object.entries(CHANGE_LABELS).filter(([key]) => Object.hasOwn(values, key)).map(([key, { label, unit }]) => (
    <div key={key}><dt>{label}</dt><dd>{formatChange(values[key], unit)}</dd></div>
  ))}</dl>;
}

/**
 * Display only supplied backend evidence; CTR values are fractions and changes are already percentage points.
 * 仅显示后端提供的证据；CTR 值为比例，而变化已采用百分点。
 */
export function OpportunityCandidates({ candidates, renderPriority }: {
  candidates: OpportunityCandidate[];
  renderPriority?: (candidate: OpportunityCandidate) => { tier: string; content: ReactNode };
}) {
  return <div className="opportunity-candidates">{candidates.map((candidate) => {
    const priority = renderPriority?.(candidate);
    return <article className="opportunity-candidate" key={`${candidate.page_id}-${candidate.previous_snapshot_id}-${candidate.current_snapshot_id}-${candidate.opportunity_type}`} data-opportunity-type={candidate.opportunity_type} data-priority-tier={priority?.tier}>
      <h3>{OPPORTUNITY_LABELS[candidate.opportunity_type]}</h3>
      {priority?.content}
      <p className="url-cell"><Link href={`/pages/${encodeURIComponent(candidate.page_id)}`}>{candidate.url}</Link></p>
      <p>Previous / 前期：{candidate.previous_period_start} → {candidate.previous_period_end}<br />
        Current / 当期：{candidate.current_period_start} → {candidate.current_period_end}</p>
      <p>Evidence / 证据：Ready / 就绪 · Scope / 范围：Compatible / 兼容</p>
      <p>{candidate.message}</p>
      <div className="table-scroll" tabIndex={0} role="region" aria-label={`${OPPORTUNITY_LABELS[candidate.opportunity_type]} evidence / 证据`}>
        <table><thead><tr><th scope="col">Metric / 指标</th><th scope="col">Previous / 前期</th><th scope="col">Current / 当期</th></tr></thead>
          <tbody>{Object.entries(METRIC_LABELS).filter(([key]) => Object.hasOwn(candidate.evidence.previous, key)).map(([key, label]) => (
            <tr key={key}><th scope="row">{label}</th><td>{formatMetric(candidate.evidence.previous[key], key === "ctr")}</td><td>{formatMetric(candidate.evidence.current[key], key === "ctr")}</td></tr>
          ))}</tbody>
        </table>
      </div>
      <Changes values={candidate.evidence.changes} />
      <details className="quality-details">
        <summary>Rule thresholds and source snapshots / 规则门槛与来源快照</summary>
        <p>These are transparent v1 heuristic thresholds. 这些是透明的 v1 启发式门槛。</p>
        <dl className="mapping-list">{Object.entries(THRESHOLD_LABELS).filter(([key]) => Object.hasOwn(candidate.evidence.thresholds, key)).map(([key, { label, operator, unit }]) => (
          <div key={key}><dt>{label}</dt><dd>{operator} {formatMetric(candidate.evidence.thresholds[key])}{unit}</dd></div>
        ))}</dl>
        <p>Reason code / 原因代码：<code>{candidate.reason_code}</code><br />
          Previous snapshot / 前期快照：<code>{candidate.previous_snapshot_id}</code><br />
          Current snapshot / 当期快照：<code>{candidate.current_snapshot_id}</code></p>
      </details>
    </article>;
  })}</div>;
}

/**
 * Keep evidence gate limitations separate from factual signals and treat an eligible no-op as a valid result.
 * 将证据门槛限制与事实信号分开，并将合格但无候选视为有效结果。
 */
export function PageOpportunities({ analysis }: { analysis: PageOpportunityAnalysis }) {
  return <section className="card" aria-labelledby="opportunities-heading" data-opportunity-eligible={String(analysis.eligible)}>
    <h2 id="opportunities-heading">Opportunity candidates / 机会候选</h2>
    <p>What factual SEO signal is present? Candidates use the selected historical comparison and describe observed changes. The opportunity workspace separately assigns transparent attention tiers. 当前有哪些事实 SEO 信号？候选使用所选历史对比，描述已观察变化。机会工作区另行分配透明的关注等级。</p>
    {!analysis.eligible ? <div className="notice" data-opportunity-gate="unavailable">
      <p><strong>Opportunity detection unavailable / 机会检测暂不可用</strong></p>
      <p>Comparison evidence readiness / 对比证据就绪度：{analysis.evidence_readiness === "limited" ? "Limited / 有限" : "Insufficient / 不足"}</p>
      <ul>{analysis.gate_reasons.map((code) => <li key={code} data-opportunity-gate-reason={code}>
        <code>{code}</code>
        {analysis.gate_observations.filter((observation) => observation.code === code).map((observation, index) => <p key={index}>{observation.message}</p>)}
      </li>)}</ul>
      <p>Data quality explains the available evidence for comparison. 数据质量说明可用于对比的证据。</p>
    </div> : analysis.candidates.length === 0 ? <p data-opportunity-empty>
      Evidence is eligible; no configured v1 rule thresholds are met. 证据合格；未满足任何已配置的 v1 规则门槛。
    </p> : <OpportunityCandidates candidates={analysis.candidates} />}
    <p><Link href="/opportunities">View priorities and original signals / 查看优先级与原始信号 →</Link></p>
  </section>;
}
