"use client";

import Link from "next/link";
import { useCallback } from "react";
import { HistoryControls, HistoryPagination } from "@/components/history-pagination";
import { PageMetricsTable } from "@/components/page-metrics-table";
import { PageDataQuality } from "@/components/page-data-quality";
import { formatMetric } from "@/lib/gsc-api";
import { formatChange, formatImportTime, formatPeriod, getPagePerformance, type PerformanceComparison } from "@/lib/history-api";
import { usePaginatedResource } from "@/lib/use-paginated-resource";

/**
 * Display the backend's compatible report pair without assigning SEO judgments.
 * 显示后端选择的兼容报告时间段，不作 SEO 价值判断。
 */
function PeriodComparison({ comparison }: { comparison: PerformanceComparison }) {
  return (
    <section className="card" aria-labelledby="comparison-heading">
      <h2 id="comparison-heading">Report-period comparison / 报告时间段对比</h2>
      <p>Previous / 前期：{comparison.previous_period_start} → {comparison.previous_period_end}<br />Current / 当期：{comparison.current_period_start} → {comparison.current_period_end}</p>
      <p>These are the two newest compatible exact report periods, selected independently of snapshot pagination. They may differ from the latest applied page values when an older report is imported later. 对比选取最新的两个兼容精确报告时间段，与快照分页无关。较旧报告后来导入时，对比可能与最新写入的页面值不同。</p>
      {comparison.periods_overlap && <p className="notice">The report periods overlap; these are overlapping windows, not independent consecutive periods. 报告时间段存在重叠；它们是重叠窗口，而非独立的连续时间段。</p>}
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Period changes / 时间段变化">
        <table>
          <thead><tr><th scope="col">Metric / 指标</th><th scope="col">Change / 变化</th><th scope="col">Percentage change / 百分比变化</th></tr></thead>
          <tbody>
            <tr><th scope="row">Clicks / 点击</th><td>{formatChange(comparison.clicks.absolute_change)}</td><td>{formatChange(comparison.clicks.percentage_change, "%")}</td></tr>
            <tr><th scope="row">Impressions / 展示</th><td>{formatChange(comparison.impressions.absolute_change)}</td><td>{formatChange(comparison.impressions.percentage_change, "%")}</td></tr>
            <tr><th scope="row">CTR / 点击率</th><td>{formatChange(comparison.ctr_percentage_point_change, " pp / 百分点")}</td><td>—</td></tr>
            <tr><th scope="row">Average position / 平均排名</th><td>{formatChange(comparison.average_position_change)}</td><td>—</td></tr>
          </tbody>
        </table>
      </div>
      <p>Changes use current − previous. A lower position number means a higher search-result position. Values are descriptive only. Missing inputs or a zero percentage baseline show “Unavailable”. 变化采用当期减前期。排名数字越小表示搜索结果位置越靠前。数值仅作描述。输入缺失或百分比基准为零时显示“不可计算”。</p>
    </section>
  );
}

/**
 * Keep current stored state, immutable observations and report comparisons visibly separate.
 * 在界面中明确区分当前已保存状态、不可变观察快照及报告时间段对比。
 */
export function PagePerformance({ pageId }: { pageId: string }) {
  const load = useCallback((page: number, pageSize: number, signal: AbortSignal) => getPagePerformance(pageId, page, pageSize, signal), [pageId]);
  const state = usePaginatedResource(load);
  const { data, loading, error } = state;

  return (
    <>
      <section className="card">
        <HistoryControls {...state} />
        {loading && <p role="status">Loading page history… / 正在加载页面历史……</p>}
        {error && <p className="notice error" role="alert">{error}</p>}
        <Link href="/pages">← Back to pages / 返回页面列表</Link>
      </section>
      {!loading && !error && data && (
        <>
          <section className="card" aria-labelledby="current-heading">
            <h2 id="current-heading">Current stored 28-day metrics / 当前已保存的 28 天指标</h2>
            <p>Latest successfully supplied values, following import order. Blank metrics preserve earlier values. This row may combine imports and is not a dated snapshot. 按导入顺序显示最新成功提供的值。空白指标保留此前值。此行可能组合多个导入，并非带日期的快照。</p>
            <PageMetricsTable rows={[data.current_page]} />
          </section>

          <PageDataQuality quality={data.quality} />

          {data.comparison ? <PeriodComparison comparison={data.comparison} /> : (
            <section className="card" aria-labelledby="comparison-heading">
              <h2 id="comparison-heading">Report-period comparison / 报告时间段对比</h2>
              <p>{data.comparison_unavailable_reason ?? "Comparison unavailable. 对比不可用。"}</p>
              <p>A comparison requires two distinct compatible exact report periods. 对比需要两个不同且兼容的精确报告时间段。</p>
            </section>
          )}

          <section className="card" aria-labelledby="snapshots-heading">
            <h2 id="snapshots-heading">Historical snapshots / 历史快照</h2>
            <p>Oldest import first. Each snapshot contains only that file&apos;s observations; unknown values stay —. Import timestamps use your browser&apos;s time zone. 按导入时间从早到晚排序。每条快照仅包含该文件的观察值；未知值保持 —。导入时间采用浏览器时区。</p>
            {data.items.length === 0 ? <p>No snapshots on this page. 本页没有快照。</p> : (
              <div className="table-scroll" tabIndex={0} role="region" aria-label="Historical snapshots / 历史快照">
                <table>
                  <thead><tr><th scope="col">Imported / 导入时间</th><th scope="col">Report period / 报告时间段</th><th scope="col">Clicks / 点击</th><th scope="col">Impressions / 展示</th><th scope="col">CTR / 点击率</th><th scope="col">Average position / 平均排名</th><th scope="col">Import ID / 导入 ID</th></tr></thead>
                  <tbody>{data.items.map((snapshot) => (
                    <tr key={snapshot.id}>
                      <td><time dateTime={snapshot.imported_at}>{formatImportTime(snapshot.imported_at)}</time></td>
                      <td>Latest 28 days / 最近 28 天<br />{formatPeriod(snapshot)}</td>
                      <td>{formatMetric(snapshot.clicks)}</td><td>{formatMetric(snapshot.impressions)}</td>
                      <td>{formatMetric(snapshot.ctr, true)}</td><td>{formatMetric(snapshot.average_position)}</td>
                      <td className="url-cell"><small>{snapshot.import_run_id}</small></td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )}
            <HistoryPagination data={data} loading={loading} changePage={state.changePage} />
          </section>
        </>
      )}
    </>
  );
}
