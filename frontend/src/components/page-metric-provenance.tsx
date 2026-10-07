import { CURRENT_METRIC_LABELS, type CurrentProvenance } from "@/lib/current-provenance";
import { formatMetric } from "@/lib/gsc-api";
import { formatImportTime, formatPeriod } from "@/lib/history-api";

const STATUS_LABELS = {
  known: "Known source / 已知来源",
  unknown: "Unknown source / 未知来源",
  unavailable: "Unavailable / 指标不可用",
};

const SEVERITY_LABELS = {
  info: "Info / 信息",
  warning: "Warning / 警告",
  blocking: "Blocking evidence / 证据不足",
};

/**
 * Show only explicitly recorded per-field sources, separate from historical comparison readiness.
 * 仅显示明确记录的逐字段来源，与历史对比就绪度分开。
 */
export function PageMetricProvenance({ provenance }: { provenance: CurrentProvenance }) {
  return (
    <section className="card" aria-labelledby="provenance-heading">
      <h2 id="provenance-heading">Current metric provenance / 当前指标来源</h2>
      <p>Sources refer to the latest successfully applied nonblank value for each field. An older reporting period imported later can supply a current value. Matching historical values do not establish a source. 来源对应每个字段最近成功应用的非空白值。较旧报告后来导入时也可提供当前值。历史值相同不能证明来源。</p>
      <dl className="summary-grid">
        <div><dt>Known provenance / 已知来源</dt><dd>{provenance.known_provenance_count}</dd></div>
        <div><dt>Unknown provenance / 未知来源</dt><dd>{provenance.unknown_provenance_count}</dd></div>
        <div><dt>Unavailable metrics / 不可用指标</dt><dd>{provenance.unavailable_metric_count}</dd></div>
      </dl>
      <p>
        {provenance.all_known_metrics_share_one_snapshot === null
          ? "No current metrics have a proven source. 当前没有指标具有可证明的来源。"
          : provenance.all_known_metrics_share_one_snapshot
            ? "All metrics with known provenance share one snapshot; other metric sources may remain unknown or unavailable. 所有已知来源指标共用一个快照；其他指标来源可能仍未知或不可用。"
            : "Metrics with known provenance reference different snapshots. 已知来源指标指向不同快照。"}
      </p>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Current metric provenance / 当前指标来源">
        <table>
          <thead><tr>
            <th scope="col">Metric / 指标</th><th scope="col">Current value / 当前值</th><th scope="col">Source status / 来源状态</th>
            <th scope="col">Snapshot / 快照</th><th scope="col">Import / 导入</th><th scope="col">Report period / 报告时间段</th><th scope="col">Imported / 导入时间</th>
          </tr></thead>
          <tbody>{provenance.metrics.map((metric) => (
            <tr key={metric.metric_name} data-metric-name={metric.metric_name}>
              <th scope="row">{CURRENT_METRIC_LABELS[metric.metric_name]}</th>
              <td>{formatMetric(metric.current_value, metric.metric_name === "ctr")}</td>
              <td data-provenance-status={metric.status}>
                {STATUS_LABELS[metric.status]}
                {metric.status === "unknown" && <p><small>Current value without proven provenance. 当前值没有可证明的来源。</small></p>}
              </td>
              <td className="url-cell"><small>{metric.snapshot_id ?? "—"}</small></td>
              <td className="url-cell"><small>{metric.import_run_id ?? "—"}</small></td>
              <td>{metric.status === "known" ? formatPeriod(metric) : "—"}</td>
              <td>{metric.imported_at ? <time dateTime={metric.imported_at}>{formatImportTime(metric.imported_at)}</time> : "—"}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <p>Import timestamps use your browser&apos;s time zone. Current-source observations do not change historical comparison readiness. 导入时间采用浏览器时区。当前来源观察不会改变历史对比就绪度。</p>
      {provenance.observations.length > 0 && (
        <>
          <h3>Current-source observations / 当前来源观察</h3>
          <ul className="quality-observations">
            {provenance.observations.map((observation, index) => (
              <li key={`${observation.code}-${index}`} data-observation-code={observation.code}>
                <p><strong>{SEVERITY_LABELS[observation.severity]}</strong> · <code>{observation.code}</code></p>
                <p>{observation.message}</p>
                {observation.snapshot_ids.length > 0 && <details className="quality-details">
                  <summary>Source snapshots / 来源快照</summary>
                  <p><code>{observation.snapshot_ids.join(", ")}</code></p>
                </details>}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
