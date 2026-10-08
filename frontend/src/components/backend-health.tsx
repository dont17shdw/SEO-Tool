"use client";

import { useState } from "react";
import { API_BASE_URL, checkBackendHealth } from "@/lib/api";
import { requestErrorMessage } from "@/lib/gsc-api";

type ConnectionState = "idle" | "loading" | "connected" | "error";

export function BackendHealth() {
  const [state, setState] = useState<ConnectionState>("idle");
  const [message, setMessage] = useState(
    "可以开始检查后端连接。",
  );

  /**
   * Show connection progress and report a validated backend response or failure.
   * 显示连接进度，并报告经验证的后端响应或连接失败。
   */
  async function checkConnection() {
    setState("loading");
    setMessage("正在检查后端连接……");

    try {
      await checkBackendHealth();
      setState("connected");
      setMessage("后端服务已连接，运行状态正常。");
    } catch (error) {
      setState("error");
      setMessage(requestErrorMessage(error));
    }
  }

  return (
    <section className="card" aria-labelledby="backend-heading">
      <h2 id="backend-heading">后端连接</h2>
      <p>检查后端服务是否正在运行。此检查仅确认服务响应，不确认数据库或数据是否已就绪。</p>
      <p className="endpoint">
        <code>{API_BASE_URL}/api/v1/health</code>
      </p>
      <div className="connection-result" data-state={state} role="status" aria-live="polite">
        {message}
      </div>
      <button type="button" onClick={checkConnection} disabled={state === "loading"}>
        {state === "loading" ? "检查中……" : "检查后端连接"}
      </button>
    </section>
  );
}
