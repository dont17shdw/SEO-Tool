"use client";

import { useState } from "react";
import { API_BASE_URL, checkBackendHealth } from "@/lib/api";

type ConnectionState = "idle" | "loading" | "connected" | "error";

export function BackendHealth() {
  const [state, setState] = useState<ConnectionState>("idle");
  const [message, setMessage] = useState(
    "Ready to check the backend. 可以开始检查后端连接。",
  );

  /**
   * Show connection progress and report a validated backend response or failure.
   * 显示连接进度，并报告经验证的后端响应或连接失败。
   */
  async function checkConnection() {
    setState("loading");
    setMessage("Checking backend connection… 正在检查后端连接……");

    try {
      const health = await checkBackendHealth();
      setState("connected");
      setMessage(`Connected to ${health.service}. 已连接到 ${health.service}。`);
    } catch (error) {
      setState("error");
      setMessage(
        error instanceof Error && !["TypeError", "TimeoutError"].includes(error.name)
          ? error.message
          : "Could not reach the backend. Start FastAPI and check the API URL. 无法连接后端，请启动 FastAPI 并检查 API 地址。",
      );
    }
  }

  return (
    <section className="card" aria-labelledby="backend-heading">
      <h2 id="backend-heading">Backend connection / 后端连接</h2>
      <p>
        Check the FastAPI service when it is running.
        <span lang="zh"> 在 FastAPI 服务启动后检查连接。</span>
      </p>
      <p className="endpoint">
        <code>{API_BASE_URL}/api/v1/health</code>
      </p>
      <div className="connection-result" data-state={state} role="status" aria-live="polite">
        {message}
      </div>
      <button type="button" onClick={checkConnection} disabled={state === "loading"}>
        {state === "loading" ? "Checking… / 检查中……" : "Check backend / 检查后端"}
      </button>
    </section>
  );
}
