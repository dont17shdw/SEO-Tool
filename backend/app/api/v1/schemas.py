from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImportResult(BaseModel):
    """Report committed changes; identical supplied values count as skipped.
    报告已提交的变更；提供的值完全相同时计为跳过。
    """

    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error_count: int = 0


class WebsitePageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    clicks_28d: int | None
    impressions_28d: int | None
    ctr: Decimal | None
    average_position: Decimal | None


class WebsitePageList(BaseModel):
    items: list[WebsitePageResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
