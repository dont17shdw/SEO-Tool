"use client";

import Link from "next/link";
import { useCallback } from "react";
import { HistoryControls, HistoryPagination } from "@/components/history-pagination";
import { PageMetricsTable } from "@/components/page-metrics-table";
import { PageDataQuality } from "@/components/page-data-quality";
import { PageMetricProvenance } from "@/components/page-metric-provenance";
import { ReportScopeSummary } from "@/components/report-scope-summary";
import { PageOpportunities } from "@/components/opportunity-candidates";
import { formatMetric } from "@/lib/gsc-api";
import { formatChange, formatImportTime, formatPeriod, getPagePerformance, type PerformanceComparison } from "@/lib/history-api";
import { usePaginatedResource } from "@/lib/use-paginated-resource";
import { formatCoverage } from "@/lib/report-scope";

/**
 * Display the backend's compatible report pair without assigning SEO judgments.
 * 显示后端选择的兼容报告时间段，不作 SEO 价值判断。
 */
function PeriodComparison({ comparison }: { comparison: PerformanceComparison }) {
  return (
    <section className="card" aria-labelledby="comparison-heading">
      <h2 id="comparison-heading">Report-period comparison / 报告时间段对比</h2>
      <p>Previous / 前期：{comparison.previous_period_start} → {comparison.previous_period_end}<br />Current / 当期：{comparison.current_period_start} → {comparison.current_period_end}</p>
      <p>These reporting periods pass date compatibility checks and have no proven scope conflict. Selection is independent of snapshot pagination and current applied values. These may differ when an older report is imported later. 这些报告时间段通过日期兼容检查，且没有已证明的范围冲突。选择独立于快照分页及当前应用值；较旧报告后来导入时，两者可能不同。</p>
      <p data-scope-compatibility={comparison.scope_compatibility}><strong>Scope compatibility / 范围兼容性：</strong>
        {comparison.scope_compatibility === "compatible" ? "Compatible / 兼容" : "Unknown / 未知"}</p>
      {comparison.scope_compatibility === "unknown" && <p className="notice">
        This descriptive comparison has insufficient scope evidence to prove equivalent properties, search types, and filters. Evidence readiness is limited. 此描述性对比的范围证据不足，无法证明属性、搜索类型及筛选相等。证据就绪度为有限。
      </p>}
      <details className="quality-details">
        <summary>Selected reports: scope and coverage / 所选报告：范围与覆盖</summary>
        <h3>Previous report / 前期报告</h3>
        <ReportScopeSummary scope={comparison.previous_report_scope} coverage={{
          coverage_status: comparison.previous_coverage_status,
          observed_date_count: comparison.previous_observed_date_count,
          dates_consecutive: comparison.previous_dates_consecutive,
        }} showEvidence />
        <h3>Current report / 当期报告</h3>
        <ReportScopeSummary scope={comparison.current_report_scope} coverage={{
          coverage_status: comparison.current_coverage_status,
          observed_date_count: comparison.current_observed_date_count,
          dates_consecutive: comparison.current_dates_consecutive,
        }} showEvidence />
      </details>
      <p>Previous date coverage / 前期日期覆盖：{formatCoverage({ coverage_status: comparison.previous_coverage_status, observed_date_count: comparison.previous_observed_date_count, dates_consecutive: comparison.previous_dates_consecutive })}<br />
        Current date coverage / 当期日期覆盖：{formatCoverage({ coverage_status: comparison.current_coverage_status, observed_date_count: comparison.current_observed_date_count, dates_consecutive: comparison.current_dates_consecutive })}</p>
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
            <h2 id="current-heading">Current applied metrics / 当前已应用指标</h2>
            <p>Latest successfully applied nonblank values from 28-day GSC imports, following import order. Blank metrics preserve earlier values. These are current applied values, not necessarily values from the newest reporting period. 按导入顺序显示 28 天 GSC 导入最近成功应用的非空白值。空白指标保留此前值。这是当前已应用的值，不一定来自最新报告时间段。</p>
            <PageMetricsTable rows={[data.current_page]} />
          </section>

          <PageMetricProvenance provenance={data.provenance} />

          <PageDataQuality quality={data.quality} />

          {data.comparison ? <PeriodComparison comparison={data.comparison} /> : (
            <section className="card" aria-labelledby="comparison-heading">
              <h2 id="comparison-heading">Report-period comparison / 报告时间段对比</h2>
              <p>{data.comparison_unavailable_reason ?? "Comparison unavailable. 对比不可用。"}</p>
              <p>A comparison requires two distinct date-compatible exact periods without a proven report-scope conflict. 对比需要两个不同、日期兼容且没有已证明报告范围冲突的精确时间段。</p>
            </section>
          )}

          <PageOpportunities analysis={data.opportunities} />

          <section className="card" aria-labelledby="snapshots-heading">
            <h2 id="snapshots-heading">Historical snapshots / 历史快照</h2>
            <p>Oldest import first. Each snapshot contains only that file&apos;s observations; unknown values stay —. Import timestamps use your browser&apos;s time zone. 按导入时间从早到晚排序。每条快照仅包含该文件的观察值；未知值保持 —。导入时间采用浏览器时区。</p>
            {data.items.length === 0 ? <p>No snapshots on this page. 本页没有快照。</p> : (
              <div className="table-scroll" tabIndex={0} role="region" aria-label="Historical snapshots / 历史快照">
                <table>
                  <thead><tr><th scope="col">Imported / 导入时间</th><th scope="col">Report period / 报告时间段</th><th scope="col">Report scope and coverage / 报告范围与覆盖</th><th scope="col">Clicks / 点击</th><th scope="col">Impressions / 展示</th><th scope="col">CTR / 点击率</th><th scope="col">Average position / 平均排名</th><th scope="col">Import ID / 导入 ID</th></tr></thead>
                  <tbody>{data.items.map((snapshot) => (
                    <tr key={snapshot.id}>
                      <td><time dateTime={snapshot.imported_at}>{formatImportTime(snapshot.imported_at)}</time></td>
                      <td>28-day report / 28 天报告<br />{formatPeriod(snapshot)}</td>
                      <td className="url-cell"><p>{snapshot.report_scope.property_id ?? "Unknown property / 属性未知"}<br />{formatCoverage(snapshot)}</p>
                        <details className="quality-details"><summary>Inspect report scope / 查看报告范围</summary>
                          <ReportScopeSummary scope={snapshot.report_scope} coverage={snapshot} showEvidence />
                        </details>
                      </td>
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
