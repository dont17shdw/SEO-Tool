import Link from "next/link";
import type { ReactNode } from "react";
import { formatMetric } from "@/lib/gsc-api";
import { formatChange } from "@/lib/history-api";
import { OPPORTUNITY_LABELS, type EvidenceValues, type OpportunityCandidate, type PageOpportunityAnalysis } from "@/lib/opportunities-api";
import { candidateExplanation, metricLabels, qualityObservationMessage, qualityReasonLabel, readinessLabels } from "@/lib/zh-cn";

const METRIC_LABELS: Record<string, string> = {
  clicks: metricLabels.clicks, impressions: metricLabels.impressions,
  ctr: metricLabels.ctr, average_position: metricLabels.average_position,
};

const CHANGE_LABELS: Record<string, { label: string; unit: string }> = {
  clicks_absolute_change: { label: "点击量变化", unit: "" },
  clicks_percentage_change: { label: "点击量百分比变化", unit: "%" },
  impressions_absolute_change: { label: "展示量变化", unit: "" },
  impressions_percentage_change: { label: "展示量百分比变化", unit: "%" },
  ctr_percentage_point_change: { label: "点击率变化", unit: " 个百分点" },
  average_position_change: { label: "平均排名变化", unit: "" },
};

const THRESHOLD_LABELS: Record<string, { label: string; operator: string; unit: string }> = {
  minimum_previous_clicks: { label: "上一周期点击量", operator: "≥", unit: "" },
  maximum_clicks_absolute_change: { label: "点击量变化", operator: "≤", unit: "" },
  maximum_clicks_percentage_change: { label: "点击量百分比变化", operator: "≤", unit: "%" },
  minimum_impressions: { label: "两个周期的展示量", operator: "≥", unit: "" },
  maximum_ctr_percentage_point_change: { label: "点击率变化", operator: "≤", unit: " 个百分点" },
  maximum_average_position_change: { label: "平均排名变化", operator: "≤", unit: "" },
  minimum_impressions_percentage_change: { label: "展示量百分比变化", operator: "≥", unit: "%" },
  minimum_average_position_change: { label: "平均排名变化", operator: "≥", unit: "" },
  minimum_current_impressions_exclusive: { label: "当前周期展示量", operator: ">", unit: "" },
  maximum_clicks_percentage_change_exclusive: { label: "点击量百分比变化", operator: "<", unit: "%" },
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
      <p>上一周期：{candidate.previous_period_start} → {candidate.previous_period_end}<br />
        当前周期：{candidate.current_period_start} → {candidate.current_period_end}</p>
      <p>分析依据：已就绪 · 报告范围兼容</p>
      <p>{candidateExplanation(candidate)}</p>
      <div className="table-scroll" tabIndex={0} role="region" aria-label={`${OPPORTUNITY_LABELS[candidate.opportunity_type]}的分析依据`}>
        <table><thead><tr><th scope="col">指标</th><th scope="col">上一周期</th><th scope="col">当前周期</th></tr></thead>
          <tbody>{Object.entries(METRIC_LABELS).filter(([key]) => Object.hasOwn(candidate.evidence.previous, key)).map(([key, label]) => (
            <tr key={key}><th scope="row">{label}</th><td>{formatMetric(candidate.evidence.previous[key], key === "ctr")}</td><td>{formatMetric(candidate.evidence.current[key], key === "ctr")}</td></tr>
          ))}</tbody>
        </table>
      </div>
      <Changes values={candidate.evidence.changes} />
      <details className="quality-details">
        <summary>规则阈值与来源快照</summary>
        <p>以下为 v1 检测规则阈值，用于描述已观察到的信号，不代表其成因或业务价值。</p>
        <dl className="mapping-list">{Object.entries(THRESHOLD_LABELS).filter(([key]) => Object.hasOwn(candidate.evidence.thresholds, key)).map(([key, { label, operator, unit }]) => (
          <div key={key}><dt>{label}</dt><dd>{operator} {formatMetric(candidate.evidence.thresholds[key])}{unit}</dd></div>
        ))}</dl>
        <p>检测原因代码：<code>{candidate.reason_code}</code><br />
          上一周期来源快照：<code>{candidate.previous_snapshot_id}</code><br />
          当前周期来源快照：<code>{candidate.current_snapshot_id}</code></p>
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
    <h2 id="opportunities-heading">SEO 机会</h2>
    <p>SEO 机会描述所选历史周期对比中已观察到的事实信号。SEO 机会优先级页面另行展示这些信号的关注等级。</p>
    {!analysis.eligible ? <div className="notice" data-opportunity-gate="unavailable">
      <p><strong>暂时无法检测 SEO 机会</strong></p>
      <p>周期对比证据状态：{readinessLabels[analysis.evidence_readiness]}</p>
      <ul>{analysis.gate_reasons.map((code) => <li key={code} data-opportunity-gate-reason={code}>
        <strong>{qualityReasonLabel(code)}</strong>
        {analysis.gate_observations.filter((observation) => observation.code === code).map((observation, index) => <p key={index}>{qualityObservationMessage(observation)}</p>)}
      </li>)}</ul>
      <details className="quality-details"><summary>检测限制的原因代码</summary>
        <p><code>{analysis.gate_reasons.join(", ")}</code></p>
      </details>
      <p>请查看数据质量，了解周期对比所需证据的具体限制。</p>
    </div> : analysis.candidates.length === 0 ? <p data-opportunity-empty>
      分析证据已就绪，但未达到任何已配置的 v1 检测规则阈值。
    </p> : <OpportunityCandidates candidates={analysis.candidates} />}
    <p><Link href="/opportunities">查看 SEO 机会优先级与原始信号 →</Link></p>
  </section>;
}
