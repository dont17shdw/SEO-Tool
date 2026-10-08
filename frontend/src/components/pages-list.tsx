"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PageMetricsTable } from "@/components/page-metrics-table";
import { listPages, requestErrorMessage, type PagesResponse } from "@/lib/gsc-api";

/**
 * Show stored metrics through the read-only API without deriving SEO conclusions.
 * 通过只读 API 显示已保存指标，不推导 SEO 结论。
 */
export function PagesList() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [reload, setReload] = useState(0);
  const [data, setData] = useState<PagesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Abort stale page requests so a slower previous response cannot overwrite navigation.
  // 取消过期的分页请求，避免此前较慢的响应覆盖当前导航结果。
  useEffect(() => {
    const controller = new AbortController();
    listPages(page, pageSize, controller.signal)
      .then((response) => {
        if (!controller.signal.aborted) setData(response);
      })
      .catch((error) => {
        if (!controller.signal.aborted) setError(requestErrorMessage(error));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [page, pageSize, reload]);

  function changePage(nextPage: number) {
    setLoading(true);
    setError(null);
    setPage(nextPage);
  }

  return (
    <section className="card" aria-labelledby="pages-heading">
      <h2 id="pages-heading">页面指标</h2>
      <p>显示各页面最新保存的指标；此列表不生成分析结论或操作建议。未知值显示为 —。</p>
      <div className="toolbar">
        <label htmlFor="page-size">每页行数</label>
        <select id="page-size" value={pageSize} disabled={loading} onChange={(event) => {
          setLoading(true);
          setError(null);
          setPage(1);
          setPageSize(Number(event.target.value));
        }}>
          <option value={10}>10</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
        <button type="button" disabled={loading} onClick={() => {
          setLoading(true);
          setError(null);
          setReload((value) => value + 1);
        }}>刷新</button>
      </div>

      {loading && <p role="status">正在加载网站页面……</p>}
      {error && <p className="notice error" role="alert">{error}</p>}
      {!loading && !error && data && (
        <>
          {data.items.length > 0 ? <PageMetricsTable rows={data.items} linkToHistory /> : (
            <p>本页没有页面记录。请先<Link href="/imports/gsc">导入 GSC 数据</Link>。</p>
          )}
          <div className="pagination" aria-label="网站页面分页">
            <button type="button" onClick={() => changePage(page - 1)} disabled={page <= 1}>上一页</button>
            <p role="status">第 {data.page} 页，共 {Math.max(1, data.total_pages)} 页 · 总计 {data.total} 条</p>
            <button type="button" onClick={() => changePage(page + 1)} disabled={page >= data.total_pages}>下一页</button>
          </div>
        </>
      )}
    </section>
  );
}
