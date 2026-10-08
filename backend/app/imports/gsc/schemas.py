"""Separate the public preview contract from the complete in-memory parsed rows.
将公开的预览契约与内存中的完整解析行分离。
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from app.normalization.report_scope import ReportScope, unknown_scope


class RowError(BaseModel):
    row: int
    field: str
    code: str
    message: str


class NormalizedGSCRow(BaseModel):
    row: int
    url: str
    clicks_28d: int | None = None
    impressions_28d: int | None = None
    ctr: Decimal | None = None
    average_position: Decimal | None = None


class ImportPreview(BaseModel):
    source: Literal["gsc_pages"] = "gsc_pages"
    reporting_window: Literal["latest_28_days"] = "latest_28_days"
    period_start: date | None = None
    period_end: date | None = None
    observed_date_count: int | None = Field(default=None, ge=1)
    dates_consecutive: bool | None = None
    coverage_status: Literal["complete", "partial", "unknown"] = "unknown"
    report_scope: ReportScope = Field(default_factory=unknown_scope)
    detected_sheet: str | None
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    column_mapping: dict[str, str]
    errors: list[RowError]
    sample_rows: list[NormalizedGSCRow]
    can_apply: bool
    preview_hash: str
    file_hash: str = Field(pattern="^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_period_bounds(self) -> "ImportPreview":
        """Keep reporting bounds paired and ordered; unknown dates must both remain NULL.
        保持报告范围成对且有序；未知日期必须同时保持 NULL。
        """
        if (self.period_start is None) != (self.period_end is None):
            raise ValueError("Reporting dates must both be present or both be unknown.")
        if self.period_start is not None and self.period_end < self.period_start:
            raise ValueError("The reporting period end cannot precede its start.")
        return self

    @computed_field
    @property
    def period_status(self) -> Literal["exact", "unknown"]:
        """Expose whether source evidence supplies exact bounds, rather than inferred dates.
        表示源证据是否提供精确范围，而非推测日期。
        """
        return "exact" if self.period_start is not None else "unknown"


@dataclass(frozen=True)
class ParsedImport:
    """Keep all validated rows internal; API previews expose only the bounded sample.
    将所有已校验行保留在内部；API 预览仅公开数量受限的样本。
    """

    preview: ImportPreview
    rows: list[NormalizedGSCRow]
    filename: str
