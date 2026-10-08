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
      <h2 id="import-history-heading">Completed imports / 已完成导入</h2>
      <p>Newest imports first. Import timestamps use your browser&apos;s time zone; report dates are calendar dates. 最近导入在前。导入时间采用浏览器时区；报告日期为日历日期。</p>
      <HistoryControls {...state} />
      {loading && <p role="status">Loading import history… / 正在加载导入历史……</p>}
      {error && <p className="notice error" role="alert">{error}</p>}
      {!loading && !error && data && (
        <>
          {data.items.length === 0 ? <p>No imports on this page. <Link href="/imports/gsc">Import a GSC report</Link>. 本页没有导入记录，请先导入 GSC 报告。</p> : (
            <div className="table-scroll" tabIndex={0} role="region" aria-label="Import history / 导入历史">
              <table>
                <thead><tr>
                  <th scope="col">Imported / 导入时间</th><th scope="col">File / 文件</th>
                  <th scope="col">Source / 数据源</th><th scope="col">Report period / 报告时间段</th>
                  <th scope="col">Report scope and coverage / 报告范围与覆盖</th>
                  <th scope="col">Rows / 行数</th><th scope="col">Created / 新建</th><th scope="col">Updated / 更新</th><th scope="col">Skipped / 跳过</th><th scope="col">Status / 状态</th>
                </tr></thead>
                <tbody>{data.items.map((run) => (
                  <tr key={run.id}>
                    <td><time dateTime={run.imported_at}>{formatImportTime(run.imported_at)}</time></td>
                    <td className="url-cell">{run.filename}<br /><small>Import ID / 导入 ID：{run.id}</small></td>
                    <td>GSC · Pages / 网页</td>
                    <td>Latest 28 days / 最近 28 天<br />{formatPeriod(run)}</td>
                    <td className="url-cell">
                      <p>{run.report_scope.property_id ?? "Unknown property / 属性未知"}<br />{formatCoverage(run)}</p>
                      <details className="quality-details"><summary>Inspect report scope / 查看报告范围</summary>
                        <ReportScopeSummary scope={run.report_scope} coverage={run} showEvidence />
                        <p>Site ID / 站点 ID：<code>{run.site_id ?? "Unknown / 未知"}</code></p>
                      </details>
                    </td>
                    <td>{run.total_rows}</td><td>{run.created_count}</td><td>{run.updated_count}</td><td>{run.skipped_count}</td>
                    <td>Completed / 已完成</td>
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
