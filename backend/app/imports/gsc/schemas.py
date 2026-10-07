"""Separate the public preview contract from the complete in-memory parsed rows.
将公开的预览契约与内存中的完整解析行分离。
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


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


@dataclass(frozen=True)
class ParsedImport:
    """Keep all validated rows internal; API previews expose only the bounded sample.
    将所有已校验行保留在内部；API 预览仅公开数量受限的样本。
    """

    preview: ImportPreview
    rows: list[NormalizedGSCRow]
