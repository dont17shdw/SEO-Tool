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
import { comparisonUnavailableMessage } from "@/lib/zh-cn";

/**
 * Display the backend's compatible report pair without assigning SEO judgments.
 * 显示后端选择的兼容报告时间段，不作 SEO 价值判断。
 */
function PeriodComparison({ comparison }: { comparison: PerformanceComparison }) {
  return (
    <section className="card" aria-labelledby="comparison-heading">
      <h2 id="comparison-heading">周期对比</h2>
      <p>上一周期：{comparison.previous_period_start} → {comparison.previous_period_end}<br />当前周期：{comparison.current_period_start} → {comparison.current_period_end}</p>
      <p>所选报告周期已通过日期兼容性检查，且没有明确的报告范围冲突。对比选择独立于快照分页和当前已应用指标；较旧报告后来导入时，当前指标可能与此对比的当前周期不同。</p>
      <p data-scope-compatibility={comparison.scope_compatibility}><strong>报告范围兼容性：</strong>
        {comparison.scope_compatibility === "compatible" ? "报告范围兼容" : "报告范围兼容性未知"}</p>
      {comparison.scope_compatibility === "unknown" && <p className="notice">
        当前仅可进行描述性对比。报告范围证据不足，无法确认两个周期的资源、搜索类型和筛选条件一致，分析证据有限。
      </p>}
      <details className="quality-details">
        <summary>所选报告的范围与日期覆盖</summary>
        <h3>上一周期报告</h3>
        <ReportScopeSummary scope={comparison.previous_report_scope} coverage={{
          coverage_status: comparison.previous_coverage_status,
          observed_date_count: comparison.previous_observed_date_count,
          dates_consecutive: comparison.previous_dates_consecutive,
        }} showEvidence />
        <h3>当前周期报告</h3>
        <ReportScopeSummary scope={comparison.current_report_scope} coverage={{
          coverage_status: comparison.current_coverage_status,
          observed_date_count: comparison.current_observed_date_count,
          dates_consecutive: comparison.current_dates_consecutive,
        }} showEvidence />
      </details>
      <p>上一周期日期覆盖：{formatCoverage({ coverage_status: comparison.previous_coverage_status, observed_date_count: comparison.previous_observed_date_count, dates_consecutive: comparison.previous_dates_consecutive })}<br />
        当前周期日期覆盖：{formatCoverage({ coverage_status: comparison.current_coverage_status, observed_date_count: comparison.current_observed_date_count, dates_consecutive: comparison.current_dates_consecutive })}</p>
      {comparison.periods_overlap && <p className="notice">两个报告周期存在日期重叠，不能视为彼此独立的连续周期。</p>}
      <div className="table-scroll" tabIndex={0} role="region" aria-label="周期指标变化">
        <table>
          <thead><tr><th scope="col">指标</th><th scope="col">变化量</th><th scope="col">百分比变化</th></tr></thead>
          <tbody>
            <tr><th scope="row">点击量</th><td>{formatChange(comparison.clicks.absolute_change)}</td><td>{formatChange(comparison.clicks.percentage_change, "%")}</td></tr>
            <tr><th scope="row">展示量</th><td>{formatChange(comparison.impressions.absolute_change)}</td><td>{formatChange(comparison.impressions.percentage_change, "%")}</td></tr>
            <tr><th scope="row">点击率（CTR）</th><td>{formatChange(comparison.ctr_percentage_point_change, " 个百分点")}</td><td>—</td></tr>
            <tr><th scope="row">平均排名</th><td>{formatChange(comparison.average_position_change)}</td><td>—</td></tr>
          </tbody>
        </table>
      </div>
      <p>变化量均为当前周期减去上一周期。平均排名数值增大通常表示排名变差，数值减小表示排名提升。点击率变化以百分点表示，与百分比变化不同。以上数值仅作描述；输入缺失或百分比基准为零时显示“不可计算”。</p>
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
        {loading && <p role="status">正在加载页面表现历史……</p>}
        {error && <p className="notice error" role="alert">{error}</p>}
        <Link href="/pages">← 返回网站页面</Link>
      </section>
      {!loading && !error && data && (
        <>
          <section className="card" aria-labelledby="current-heading">
            <h2 id="current-heading">当前已应用指标</h2>
            <p>以下指标来自按导入顺序最近一次成功应用的 28 天 GSC 报告。空白指标保留此前值，因此当前已应用指标不一定来自最新报告周期。</p>
            <PageMetricsTable rows={[data.current_page]} />
          </section>

          <PageMetricProvenance provenance={data.provenance} />

          <PageDataQuality quality={data.quality} />

          {data.comparison ? <PeriodComparison comparison={data.comparison} /> : (
            <section className="card" aria-labelledby="comparison-heading">
              <h2 id="comparison-heading">周期对比</h2>
              <p>{comparisonUnavailableMessage()}</p>
              <p>具体限制可在上方的数据质量中查看。</p>
            </section>
          )}

          <PageOpportunities analysis={data.opportunities} />

          <section className="card" aria-labelledby="snapshots-heading">
            <h2 id="snapshots-heading">表现历史快照</h2>
            <p>按导入时间从早到晚显示。每条快照仅包含对应文件中的观察值，未知值显示为“—”。导入时间采用浏览器时区。</p>
            {data.items.length === 0 ? <p>当前结果页没有历史快照。</p> : (
              <div className="table-scroll" tabIndex={0} role="region" aria-label="表现历史快照">
                <table>
                  <thead><tr><th scope="col">导入时间</th><th scope="col">报告周期</th><th scope="col">报告范围与日期覆盖</th><th scope="col">点击量</th><th scope="col">展示量</th><th scope="col">点击率（CTR）</th><th scope="col">平均排名</th><th scope="col">导入 UUID</th></tr></thead>
                  <tbody>{data.items.map((snapshot) => (
                    <tr key={snapshot.id}>
                      <td><time dateTime={snapshot.imported_at}>{formatImportTime(snapshot.imported_at)}</time></td>
                      <td>28 天报告<br />{formatPeriod(snapshot)}</td>
                      <td className="url-cell"><p>{snapshot.report_scope.property_id ?? "资源身份未知"}<br />{formatCoverage(snapshot)}</p>
                        <details className="quality-details"><summary>查看报告范围</summary>
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
