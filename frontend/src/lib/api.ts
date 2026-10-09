import { apiErrorMessage, ChineseUiError } from "@/lib/zh-cn";

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

export type HealthResponse = {
  status: "ok";
  service: string;
};

/**
 * Check the V1 service health without depending on SEO or database operations.
 * 检查 V1 服务健康状态，不依赖 SEO 业务或数据库操作。
 */
export async function checkBackendHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/health`, {
    cache: "no-store",
    signal: AbortSignal.timeout(5_000),
  });

  if (!response.ok) {
    throw new ChineseUiError(apiErrorMessage(null, response.status));
  }

  const payload: unknown = await response.json();

  // Validate the response at the network boundary before showing a healthy state.
  // 在网络边界验证响应，确认有效后再显示健康状态。
  if (
    typeof payload !== "object" ||
    payload === null ||
    !("status" in payload) ||
    payload.status !== "ok" ||
    !("service" in payload) ||
    typeof payload.service !== "string"
  ) {
    throw new ChineseUiError("后端健康检查响应格式异常，请检查后端连接与版本。");
  }

  return { status: payload.status, service: payload.service };
}
