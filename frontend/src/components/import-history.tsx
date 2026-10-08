"use client";

import Link from "next/link";
import { HistoryControls, HistoryPagination } from "@/components/history-pagination";
import { ReportScopeSummary } from "@/components/report-scope-summary";
import { formatImportTime, formatPeriod, listImportHistory } from "@/lib/history-api";
import { formatCoverage } from "@/lib/report-scope";
import { usePaginatedResource } from "@/lib/use-paginated-resource";

/**
 * Show immutable completed import events, including explicitly unknown report dates.
 * 显示不可变的已完成导入事件，并明确标识未知报告日期。
 */
export function ImportHistory() {
  const state = usePaginatedResource(listImportHistory);
  const { data, loading, error } = state;
  return (
    <section className="card" aria-labelledby="import-history-heading">
      <h2 id="import-history-heading">已完成导入</h2>
      <p>按导入时间从新到旧排列。导入时间采用浏览器时区，报告日期按原始日历日期显示。</p>
      <HistoryControls {...state} />
      {loading && <p role="status">正在加载导入历史……</p>}
      {error && <p className="notice error" role="alert">{error}</p>}
      {!loading && !error && data && (
        <>
          {data.items.length === 0 ? <p>本页没有导入记录。请先<Link href="/imports/gsc">导入 GSC 数据</Link>。</p> : (
            <div className="table-scroll" tabIndex={0} role="region" aria-label="导入历史">
              <table>
                <thead><tr>
                  <th scope="col">导入时间</th><th scope="col">文件</th>
                  <th scope="col">数据源</th><th scope="col">报告周期</th>
                  <th scope="col">报告范围与日期覆盖</th>
                  <th scope="col">总行数</th><th scope="col">新建</th><th scope="col">更新</th><th scope="col">跳过</th><th scope="col">状态</th>
                </tr></thead>
                <tbody>{data.items.map((run) => (
                  <tr key={run.id}>
                    <td><time dateTime={run.imported_at}>{formatImportTime(run.imported_at)}</time></td>
                    <td className="url-cell">{run.filename}<br /><small>导入 ID：{run.id}</small></td>
                    <td>GSC · 网页表现</td>
                    <td>28 天报告<br />{formatPeriod(run)}</td>
                    <td className="url-cell">
                      <p>{run.report_scope.property_id ?? "资源标识未知"}<br />{formatCoverage(run)}</p>
                      <details className="quality-details"><summary>查看报告范围</summary>
                        <ReportScopeSummary scope={run.report_scope} coverage={run} showEvidence />
                        <p>站点 ID：<code>{run.site_id ?? "未知"}</code></p>
                      </details>
                    </td>
                    <td>{run.total_rows}</td><td>{run.created_count}</td><td>{run.updated_count}</td><td>{run.skipped_count}</td>
                    <td>已完成</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
          <HistoryPagination data={data} loading={loading} changePage={state.changePage} />
        </>
      )}
    </section>
  );
}
