import { formatMetric, type PageMetrics } from "@/lib/gsc-api";

export function PageMetricsTable({
  rows,
  showRowNumber = false,
}: {
  rows: (PageMetrics & { row?: number; id?: string })[];
  showRowNumber?: boolean;
}) {
  return (
    <div className="table-scroll" tabIndex={0} role="region" aria-label="Page metrics / 页面指标">
      <table>
        <thead>
          <tr>
            {showRowNumber && <th scope="col">Row / 行</th>}
            <th scope="col">URL</th>
            <th scope="col">Clicks 28d / 28 天点击</th>
            <th scope="col">Impressions 28d / 28 天展示</th>
            <th scope="col">CTR / 点击率</th>
            <th scope="col">Average position / 平均排名</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id ?? row.row ?? row.url}>
              {showRowNumber && <td>{row.row}</td>}
              <td className="url-cell">{row.url}</td>
              <td>{formatMetric(row.clicks_28d)}</td>
              <td>{formatMetric(row.impressions_28d)}</td>
              <td>{formatMetric(row.ctr, true)}</td>
              <td>{formatMetric(row.average_position)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
