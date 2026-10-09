"use client";

import { useCallback } from "react";
import { HistoryControls, HistoryPagination } from "@/components/history-pagination";
import { OpportunityCandidates } from "@/components/opportunity-candidates";
import { listOpportunities } from "@/lib/opportunities-api";
import { usePaginatedResource } from "@/lib/use-paginated-resource";

/**
 * Browse runtime candidates with pagination on candidates and neutral URL/type/page ordering.
 * 浏览运行时候选，对候选分页，并按 URL、类型和页面中性排序。
 */
export function OpportunitiesList() {
  const load = useCallback((page: number, pageSize: number, signal: AbortSignal) => listOpportunities(page, pageSize, signal), []);
  const state = usePaginatedResource(load);
  const { data, loading, error } = state;
  return <section className="card" data-opportunity-view="neutral" aria-labelledby="candidate-list-heading">
    <h2 id="candidate-list-heading">原始 SEO 机会</h2>
    <p>按 URL、机会类型与页面 ID 排列，不按优先级排序。分页按 SEO 机会计数，同一页面的多个信号分别显示。</p>
    <HistoryControls {...state} />
    {loading && <p role="status">正在加载 SEO 机会……</p>}
    {error && <p className="notice error" role="alert">{error}</p>}
    {!loading && !error && data && <>
      {data.items.length === 0 ? <p data-opportunity-empty>当前结果页没有 SEO 机会。检测需要分析证据已就绪、报告范围兼容、观察日期覆盖完整，并达到 v1 检测规则阈值。请切换到优先级视图，查看证据就绪情况与检测摘要。</p> : <OpportunityCandidates candidates={data.items} />}
      <HistoryPagination data={data} loading={loading} changePage={state.changePage} />
    </>}
  </section>;
}
