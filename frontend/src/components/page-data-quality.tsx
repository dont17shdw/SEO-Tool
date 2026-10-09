import { QUALITY_COUNT_LABELS, type DataQuality, type QualityObservation } from "@/lib/data-quality";
import { isCount, isRecord } from "@/lib/gsc-api";
import { metricLabels, qualityObservationMessage, qualityReasonLabel, readinessLabels, severityLabels } from "@/lib/zh-cn";

const EVIDENCE_COUNT_LABELS: Record<string, string> = {
  snapshot_count: "受影响快照数",
  import_count: "受影响导入数",
  revision_period_count: "存在修订的报告周期数",
  revision_import_count: "报告周期修订导入数",
  affected_snapshot_count: "较晚导入的旧周期快照数",
  earlier_imported_newer_period_count: "较早导入的新周期数",
};

const METRIC_LABELS: Record<string, string> = {
  clicks: metricLabels.clicks,
  impressions: metricLabels.impressions,
  ctr: metricLabels.ctr,
  average_position: metricLabels.average_position,
};

/**
 * Render supported factual context without calculating new findings from the evidence.
 * 显示受支持的事实背景，不从证据计算新的发现。
 */
function EvidenceContext({ evidence }: { evidence: QualityObservation["evidence"] }) {
  const counts = Object.entries(EVIDENCE_COUNT_LABELS).filter(([key]) => isCount(evidence[key]));
  const periodFields = ["previous_period_start", "previous_period_end", "current_period_start", "current_period_end", "overlap_start", "overlap_end"];
  const hasPeriods = periodFields.every((key) => typeof evidence[key] === "string");
  const baselines = isRecord(evidence.metrics) ? Object.entries(evidence.metrics).filter(
    ([field, metric]) => ["clicks", "impressions"].includes(field) && isRecord(metric) && metric.previous === 0 && isCount(metric.current),
  ) : [];

  return (
    <>
      {counts.length > 0 && <dl className="mapping-list">{counts.map(([key, label]) => (
        <div key={key}><dt>{label}</dt><dd>{String(evidence[key])}</dd></div>
      ))}</dl>}
      {hasPeriods && <p>
        上一周期：{String(evidence.previous_period_start)} → {String(evidence.previous_period_end)}<br />
        当前周期：{String(evidence.current_period_start)} → {String(evidence.current_period_end)}<br />
        重叠日期：{String(evidence.overlap_start)} → {String(evidence.overlap_end)}
      </p>}
      {baselines.map(([field, metric]) => (
        <p key={field}>{METRIC_LABELS[field]} · 上一周期：0 · 当前周期：{String((metric as Record<string, unknown>).current)}</p>
      ))}
    </>
  );
}

function EvidenceIds({ ids, label }: { ids: string[]; label: string }) {
  return ids.length > 0 && <p>{label}：<code>{ids.slice(0, 10).join(", ")}</code>
    {ids.length > 10 && <span> · 共 {ids.length} 条，仅显示前 10 条</span>}
  </p>;
}

/**
 * Show affected records without dumping arbitrary structured evidence into the interface.
 * 显示受影响记录，不将任意结构化证据直接转储到界面。
 */
function ObservationEvidence({ observation }: { observation: QualityObservation }) {
  const missingFields = isRecord(observation.evidence.missing_fields_by_snapshot)
    ? Object.entries(observation.evidence.missing_fields_by_snapshot).filter(
      ([, fields]) => Array.isArray(fields) && fields.every((field) => typeof field === "string" && Object.hasOwn(METRIC_LABELS, field)),
    ) : [];
  return (
    <details className="quality-details">
      <summary>分析依据记录 · {observation.scope === "page" ? "页面" : "导入"}</summary>
      <p>原因代码：<code>{observation.code}</code></p>
      <EvidenceIds ids={observation.snapshot_ids} label="来源快照 UUID" />
      <EvidenceIds ids={observation.import_run_ids} label="导入 UUID" />
      {missingFields.slice(0, 10).map(([snapshotId, fields]) => (
        <p key={snapshotId}>缺失指标 · <code>{snapshotId}</code>：{(fields as string[]).map((field) => METRIC_LABELS[field]).join(", ")}</p>
      ))}
      {missingFields.length > 10 && <p>共 {missingFields.length} 个快照存在缺失指标，仅显示前 10 个快照的详情。</p>}
    </details>
  );
}

/**
 * Present data readiness and factual caveats without interpreting page performance.
 * 展示数据就绪程度及事实限制，不解释页面表现的价值。
 */
export function PageDataQuality({ quality }: { quality: DataQuality }) {
  return (
    <section className="card" aria-labelledby="quality-heading">
      <h2 id="quality-heading">数据质量</h2>
      <p>就绪状态描述周期对比所需证据是否完整。“证据不足”表示对比所需证据尚不可用，并不表示导入无效。</p>
      <dl className="summary-grid">
        <div><dt>证据就绪状态</dt><dd data-readiness={quality.readiness}>{readinessLabels[quality.readiness]}</dd></div>
        <div><dt>描述性周期对比</dt><dd>{quality.comparison_exists ? "可用" : "不可用"}</dd></div>
        {Object.entries(QUALITY_COUNT_LABELS).map(([key, label]) => (
          <div key={key}><dt>{label}</dt><dd>{quality.counts[key as keyof typeof QUALITY_COUNT_LABELS]}</dd></div>
        ))}
      </dl>
      {(quality.readiness_reasons.length > 0 || quality.selected_snapshot_ids.length > 0) && (
        <details className="quality-details">
          <summary>就绪状态的分析依据</summary>
          {quality.readiness_reasons.length > 0 && <p>原因代码：<code>{quality.readiness_reasons.join(", ")}</code></p>}
          {quality.selected_snapshot_ids.length > 0 && <p>所选来源快照（上一周期、当前周期）：<code>{quality.selected_snapshot_ids.join(", ")}</code></p>}
        </details>
      )}
      <h3>数据质量观察</h3>
      {quality.observations.length === 0 ? <p>未报告需要说明的数据质量情况。</p> : (
        <ul className="quality-observations">
          {quality.observations.map((observation, index) => (
            <li key={`${observation.code}-${index}`} data-observation-code={observation.code}>
              <p><strong>{severityLabels[observation.severity]}</strong> · <strong>{qualityReasonLabel(observation.code)}</strong></p>
              <p>{qualityObservationMessage(observation)}</p>
              <EvidenceContext evidence={observation.evidence} />
              <ObservationEvidence observation={observation} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
