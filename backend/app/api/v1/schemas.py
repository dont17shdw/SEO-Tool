from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field


class ImportResult(BaseModel):
    """Identify the committed import or original run for an already-processed file.
    标识已提交的导入，或已处理文件对应的原始导入记录。
    """

    import_run_id: UUID
    already_processed: bool = False
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


class ReportingPeriod(BaseModel):
    period_start: date | None
    period_end: date | None

    @computed_field
    @property
    def period_status(self) -> Literal["exact", "unknown"]:
        return (
            "exact" if self.period_start is not None and self.period_end is not None else "unknown"
        )


class ImportRunResponse(ReportingPeriod):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    source_type: str
    file_hash: str
    filename: str
    reporting_window: str
    imported_at: datetime
    total_rows: int
    created_count: int
    updated_count: int
    skipped_count: int
    status: str


class ImportRunList(BaseModel):
    items: list[ImportRunResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class PerformanceSnapshotResponse(ReportingPeriod):
    id: UUID
    import_run_id: UUID
    page_id: UUID
    url: str
    source: str
    source_type: str
    reporting_window: str
    imported_at: datetime
    created_at: datetime
    clicks: int | None
    impressions: int | None
    ctr: Decimal | None
    average_position: Decimal | None


class MetricChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    absolute_change: int | None
    percentage_change: Decimal | None


class PerformanceComparisonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    previous_snapshot_id: UUID
    current_snapshot_id: UUID
    previous_period_start: date
    previous_period_end: date
    current_period_start: date
    current_period_end: date
    periods_overlap: bool
    clicks: MetricChangeResponse
    impressions: MetricChangeResponse
    ctr_percentage_point_change: Decimal | None
    average_position_change: Decimal | None


class PagePerformanceHistory(BaseModel):
    current_page: WebsitePageResponse
    items: list[PerformanceSnapshotResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
    comparison: PerformanceComparisonResponse | None
    comparison_unavailable_reason: str | None
