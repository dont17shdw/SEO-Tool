import { formatMetric, type PageMetrics } from "@/lib/gsc-api";
import { metricLabel } from "@/lib/zh-cn";
import Link from "next/link";

export function PageMetricsTable({
  rows,
  showRowNumber = false,
  linkToHistory = false,
}: {
  rows: (PageMetrics & { row?: number; id?: string })[];
  showRowNumber?: boolean;
  linkToHistory?: boolean;
}) {
  return (
    <div className="table-scroll" tabIndex={0} role="region" aria-label="页面指标">
      <table>
        <thead>
          <tr>
            {showRowNumber && <th scope="col">行号</th>}
            <th scope="col">URL</th>
            <th scope="col">{metricLabel("clicks_28d")}</th>
            <th scope="col">{metricLabel("impressions_28d")}</th>
            <th scope="col">{metricLabel("ctr")}</th>
            <th scope="col">{metricLabel("average_position")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id ?? row.row ?? row.url}>
              {showRowNumber && <td>{row.row}</td>}
              <td className="url-cell">{linkToHistory && row.id ? <Link href={`/pages/${row.id}`}>{row.url}<br /><small>查看表现历史 →</small></Link> : row.url}</td>
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
