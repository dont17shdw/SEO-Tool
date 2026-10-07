"use client";

import { useEffect, useState } from "react";
import { requestErrorMessage } from "@/lib/gsc-api";

/**
 * Share read-only pagination state while cancelling stale requests on navigation.
 * 共享只读分页状态，并在导航时取消过期请求。
 */
export function usePaginatedResource<T>(load: (page: number, pageSize: number, signal: AbortSignal) => Promise<T>) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [reload, setReload] = useState(0);
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    load(page, pageSize, controller.signal)
      .then((response) => { if (!controller.signal.aborted) setData(response); })
      .catch((error) => { if (!controller.signal.aborted) setError(requestErrorMessage(error)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [load, page, pageSize, reload]);

  function changePage(nextPage: number) {
    setLoading(true);
    setError(null);
    setPage(nextPage);
  }

  function changePageSize(nextSize: number) {
    setLoading(true);
    setError(null);
    setPage(1);
    setPageSize(nextSize);
  }

  function refresh() {
    setLoading(true);
    setError(null);
    setReload((value) => value + 1);
  }

  return { data, loading, error, page, pageSize, changePage, changePageSize, refresh };
}
