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
    <h2 id="candidate-list-heading">Detected candidates / 已检测候选</h2>
    <p>Ordered by URL, opportunity type, and page ID. Pagination counts candidates, including multiple signals for one page. 按 URL、机会类型及页面 ID 排序。分页统计候选，包括同一页面的多个信号。</p>
    <HistoryControls {...state} />
    {loading && <p role="status">Loading opportunity candidates… / 正在加载机会候选……</p>}
    {error && <p className="notice error" role="alert">{error}</p>}
    {!loading && !error && data && <>
      {data.items.length === 0 ? <p data-opportunity-empty>No opportunity candidates on this page. Detection requires ready evidence, compatible scope, complete observed periods, and a met v1 rule threshold. The prioritized view provides import-readiness summary counts. 本页没有机会候选。检测要求证据就绪、范围兼容、已观察时间段完整，且满足 v1 规则门槛。优先级视图提供导入就绪度摘要计数。</p> : <OpportunityCandidates candidates={data.items} />}
      <HistoryPagination data={data} loading={loading} changePage={state.changePage} />
    </>}
  </section>;
}
