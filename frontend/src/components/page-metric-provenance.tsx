import { CURRENT_METRIC_LABELS, type CurrentProvenance } from "@/lib/current-provenance";
import { formatMetric } from "@/lib/gsc-api";
import { formatImportTime, formatPeriod } from "@/lib/history-api";
import { provenanceStatusLabels, qualityObservationMessage, qualityReasonLabel, severityLabels } from "@/lib/zh-cn";

/**
 * Show only explicitly recorded per-field sources, separate from historical comparison readiness.
 * 仅显示明确记录的逐字段来源，与历史对比就绪度分开。
 */
export function PageMetricProvenance({ provenance }: { provenance: CurrentProvenance }) {
  return (
    <section className="card" aria-labelledby="provenance-heading">
      <h2 id="provenance-heading">当前指标来源</h2>
      <p>来源记录对应每个字段最近一次成功应用的非空白值。较旧报告后来导入时，也可能提供当前值；历史快照的数值相同，不能据此确定来源。</p>
      <dl className="summary-grid">
        <div><dt>已知来源的指标数</dt><dd>{provenance.known_provenance_count}</dd></div>
        <div><dt>来源未知的指标数</dt><dd>{provenance.unknown_provenance_count}</dd></div>
        <div><dt>不可用指标数</dt><dd>{provenance.unavailable_metric_count}</dd></div>
      </dl>
      <p>
        {provenance.all_known_metrics_share_one_snapshot === null
          ? "当前没有指标具有明确记录的来源。"
          : provenance.all_known_metrics_share_one_snapshot
            ? "所有已知来源的指标均来自同一个快照；其他指标的来源可能仍然未知或不可用。"
            : "已知来源的指标来自不同快照。"}
      </p>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="当前指标来源">
        <table>
          <thead><tr>
            <th scope="col">指标</th><th scope="col">当前值</th><th scope="col">来源状态</th>
            <th scope="col">来源快照</th><th scope="col">来源导入</th><th scope="col">报告周期</th><th scope="col">导入时间</th>
          </tr></thead>
          <tbody>{provenance.metrics.map((metric) => (
            <tr key={metric.metric_name} data-metric-name={metric.metric_name}>
              <th scope="row">{CURRENT_METRIC_LABELS[metric.metric_name]}</th>
              <td>{formatMetric(metric.current_value, metric.metric_name === "ctr")}</td>
              <td data-provenance-status={metric.status}>
                {provenanceStatusLabels[metric.status]}
                {metric.status === "unknown" && <p><small>当前值尚无明确记录的来源。</small></p>}
              </td>
              <td className="url-cell"><small>{metric.snapshot_id ?? "—"}</small></td>
              <td className="url-cell"><small>{metric.import_run_id ?? "—"}</small></td>
              <td>{metric.status === "known" ? formatPeriod(metric) : "—"}</td>
              <td>{metric.imported_at ? <time dateTime={metric.imported_at}>{formatImportTime(metric.imported_at)}</time> : "—"}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <p>导入时间采用浏览器时区。当前指标来源的观察结果不会改变历史周期对比的就绪状态。</p>
      {provenance.observations.length > 0 && (
        <>
          <h3>当前指标来源的观察结果</h3>
          <ul className="quality-observations">
            {provenance.observations.map((observation, index) => (
              <li key={`${observation.code}-${index}`} data-observation-code={observation.code}>
                <p><strong>{severityLabels[observation.severity]}</strong> · <strong>{qualityReasonLabel(observation.code)}</strong></p>
                <p>{qualityObservationMessage(observation)}</p>
                <details className="quality-details">
                  <summary>来源快照与原因代码</summary>
                  <p>原因代码：<code>{observation.code}</code></p>
                  {observation.snapshot_ids.length > 0 && <p>来源快照：<code>{observation.snapshot_ids.join(", ")}</code></p>}
                </details>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
