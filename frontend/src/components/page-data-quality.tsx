import { QUALITY_COUNT_LABELS, type DataQuality, type QualityObservation } from "@/lib/data-quality";
import { isCount, isRecord } from "@/lib/gsc-api";

const READINESS_LABELS = {
  insufficient: "Insufficient / 不足",
  limited: "Limited / 有限",
  ready: "Ready / 就绪",
};

const SEVERITY_LABELS = {
  info: "Info / 信息",
  warning: "Warning / 警告",
  blocking: "Blocking evidence / 证据不足",
};

const EVIDENCE_COUNT_LABELS: Record<string, string> = {
  snapshot_count: "Affected snapshots / 受影响快照",
  import_count: "Affected imports / 受影响导入",
  revision_period_count: "Periods with revisions / 存在修订的时间段",
  revision_import_count: "Period revision imports / 时间段修订导入",
  affected_snapshot_count: "Older-period snapshots imported later / 后导入的较旧时间段快照",
  earlier_imported_newer_period_count: "Earlier imports with newer periods / 较早导入的较新时间段",
};

const METRIC_LABELS: Record<string, string> = {
  clicks: "Clicks / 点击",
  impressions: "Impressions / 展示",
  ctr: "CTR / 点击率",
  average_position: "Average position / 平均排名",
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
        Previous period / 前期：{String(evidence.previous_period_start)} → {String(evidence.previous_period_end)}<br />
        Current period / 当期：{String(evidence.current_period_start)} → {String(evidence.current_period_end)}<br />
        Overlap / 重叠：{String(evidence.overlap_start)} → {String(evidence.overlap_end)}
      </p>}
      {baselines.map(([field, metric]) => (
        <p key={field}>{METRIC_LABELS[field]} · Previous / 前期：0 · Current / 当期：{String((metric as Record<string, unknown>).current)}</p>
      ))}
    </>
  );
}

function EvidenceIds({ ids, label }: { ids: string[]; label: string }) {
  return ids.length > 0 && <p>{label}：<code>{ids.slice(0, 10).join(", ")}</code>
    {ids.length > 10 && <span> · Showing 10 of {ids.length} / 显示 {ids.length} 条中的 10 条</span>}
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
      <summary>Evidence records / 证据记录 · {observation.scope === "page" ? "Page / 页面" : "Import / 导入"}</summary>
      <EvidenceIds ids={observation.snapshot_ids} label="Snapshot IDs / 快照 ID" />
      <EvidenceIds ids={observation.import_run_ids} label="Import IDs / 导入 ID" />
      {missingFields.slice(0, 10).map(([snapshotId, fields]) => (
        <p key={snapshotId}>Missing fields / 缺失字段 · <code>{snapshotId}</code>：{(fields as string[]).map((field) => METRIC_LABELS[field]).join(", ")}</p>
      ))}
      {missingFields.length > 10 && <p>Showing missing fields for 10 of {missingFields.length} snapshots. 显示 {missingFields.length} 个快照中的 10 个的缺失字段。</p>}
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
      <h2 id="quality-heading">Data quality / 数据质量</h2>
      <p>Readiness describes evidence for comparison. “Blocking” refers to unavailable comparison evidence and does not invalidate an import. 就绪程度描述用于对比的证据。“证据不足”指对比所需证据不可用，不表示导入无效。</p>
      <dl className="summary-grid">
        <div><dt>Data readiness / 数据就绪程度</dt><dd data-readiness={quality.readiness}>{READINESS_LABELS[quality.readiness]}</dd></div>
        <div><dt>Compatible comparison / 兼容对比</dt><dd>{quality.comparison_exists ? "Available / 可用" : "Unavailable / 不可用"}</dd></div>
        {Object.entries(QUALITY_COUNT_LABELS).map(([key, label]) => (
          <div key={key}><dt>{label}</dt><dd>{quality.counts[key as keyof typeof QUALITY_COUNT_LABELS]}</dd></div>
        ))}
      </dl>
      {(quality.readiness_reasons.length > 0 || quality.selected_snapshot_ids.length > 0) && (
        <details className="quality-details">
          <summary>Readiness evidence / 就绪证据</summary>
          {quality.readiness_reasons.length > 0 && <p>Reason codes / 原因代码：<code>{quality.readiness_reasons.join(", ")}</code></p>}
          {quality.selected_snapshot_ids.length > 0 && <p>Selected snapshots (previous, current) / 选中快照（前期、当期）：<code>{quality.selected_snapshot_ids.join(", ")}</code></p>}
        </details>
      )}
      <h3>Observations / 观察结果</h3>
      {quality.observations.length === 0 ? <p>No evidence conditions reported. 未报告证据条件。</p> : (
        <ul className="quality-observations">
          {quality.observations.map((observation, index) => (
            <li key={`${observation.code}-${index}`} data-observation-code={observation.code}>
              <p><strong>{SEVERITY_LABELS[observation.severity]}</strong> · <code>{observation.code}</code></p>
              <p>{observation.message}</p>
              <EvidenceContext evidence={observation.evidence} />
              <ObservationEvidence observation={observation} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
