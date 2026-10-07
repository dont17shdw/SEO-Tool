import type { PaginationMetadata } from "@/lib/history-api";

export function HistoryPagination({ data, loading, changePage }: {
  data: PaginationMetadata;
  loading: boolean;
  changePage: (page: number) => void;
}) {
  return (
    <div className="pagination" aria-label="Pagination / 分页">
      <button type="button" onClick={() => changePage(data.page - 1)} disabled={loading || data.page <= 1}>Previous / 上一页</button>
      <p role="status">Page / 页 {data.page} of / 共 {Math.max(1, data.total_pages)} · Total / 总计 {data.total}</p>
      <button type="button" onClick={() => changePage(data.page + 1)} disabled={loading || data.page >= data.total_pages}>Next / 下一页</button>
    </div>
  );
}

export function HistoryControls({ pageSize, loading, changePageSize, refresh }: {
  pageSize: number;
  loading: boolean;
  changePageSize: (size: number) => void;
  refresh: () => void;
}) {
  return (
    <div className="toolbar">
      <label htmlFor="history-page-size">Rows per page / 每页行数</label>
      <select id="history-page-size" value={pageSize} disabled={loading} onChange={(event) => changePageSize(Number(event.target.value))}>
        <option value={10}>10</option><option value={50}>50</option><option value={100}>100</option>
      </select>
      <button type="button" disabled={loading} onClick={refresh}>Refresh / 刷新</button>
    </div>
  );
}
