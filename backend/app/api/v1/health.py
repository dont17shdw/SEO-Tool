from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["seo-tool-api"] = "seo-tool-api"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API liveness / 检查 API 是否运行",
)
def health() -> HealthResponse:
    """Confirm the API process is running; database readiness is a separate concern.
    确认 API 进程正在运行；数据库就绪状态属于独立职责。
    """
    return HealthResponse()
