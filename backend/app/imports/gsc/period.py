"""Extract observed reporting dates from GSC-specific worksheet evidence only.
仅从 GSC 专用工作表证据中提取观察到的报告日期。
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal

from app.imports.gsc.mapping import normalize_label
from app.normalization.gsc import is_blank

DATE_SHEET_NAMES = {"chart", "date", "dates", "图表", "日期"}
DATE_HEADERS = {"date", "dates", "日期"}
ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")


class PeriodWorksheetTooLarge(ValueError):
    """Signal metadata size limits without coupling date extraction to HTTP errors.
    表示元数据超过大小限制，避免将日期提取与 HTTP 错误耦合。
    """


@dataclass(frozen=True)
class ReportingEvidence:
    """Retain trustworthy endpoints and distinct observed daily coverage together.
    一起保留可信起止日期与不同的已观察每日覆盖信息。
    """

    period_start: date | None = None
    period_end: date | None = None
    observed_date_count: int | None = None
    dates_consecutive: bool | None = None
    coverage_status: Literal["complete", "partial", "unknown"] = "unknown"


def _reporting_date(value: Any) -> date | None:
    """Accept native calendar dates and strict ISO text, without guessing other formats.
    接受原生日期及严格的 ISO 文本，不猜测其他格式。
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if ISO_DATE.fullmatch(text):
            try:
                return date.fromisoformat(text)
            except ValueError:
                pass
    return None


def _worksheet_dates(sheet: Any, max_rows: int) -> tuple[set[date], bool]:
    """Reject incomplete or ambiguous date evidence while bounding physical worksheet rows.
    限制工作表物理行数，并拒绝不完整或含糊的日期证据。
    """
    sheet.reset_dimensions()
    header_seen = False
    date_column: int | None = None
    dates: set[date] = set()
    invalid = False
    for row_number, row in enumerate(sheet.iter_rows(values_only=True), start=1):
        if row_number > max_rows:
            raise PeriodWorksheetTooLarge("The reporting-date worksheet is too large.")
        if all(is_blank(value) for value in row):
            continue
        if not header_seen:
            header_seen = True
            columns = [
                index for index, value in enumerate(row) if normalize_label(value) in DATE_HEADERS
            ]
            if len(columns) == 1:
                date_column = columns[0]
            elif len(columns) > 1:
                invalid = True
            continue
        if date_column is None:
            continue
        value = row[date_column] if date_column < len(row) else None
        reporting_date = _reporting_date(value)
        if reporting_date is None:
            invalid = True
        else:
            dates.add(reporting_date)
    return dates, invalid


def extract_reporting_evidence(workbook: Any, max_rows: int) -> ReportingEvidence:
    """Use matching distinct date sets to establish bounds and expected 28-day coverage.
    使用一致的不同日期集合确定范围与预期的 28 天覆盖。

    Only 28 distinct consecutive days establish complete observed coverage; endpoints alone do not.
    仅 28 个不同的连续日期能证明完整的已观察覆盖；单凭起止日期不能证明。
    """
    evidence: set[date] | None = None
    uncertain = False
    for name in workbook.sheetnames:
        if normalize_label(name) not in DATE_SHEET_NAMES:
            continue
        dates, invalid = _worksheet_dates(workbook[name], max_rows)
        uncertain = uncertain or invalid
        if dates:
            if evidence is not None and dates != evidence:
                uncertain = True
            else:
                evidence = dates
    if uncertain or not evidence:
        return ReportingEvidence()
    start, end = min(evidence), max(evidence)
    count = len(evidence)
    consecutive = count == (end - start).days + 1
    return ReportingEvidence(
        period_start=start,
        period_end=end,
        observed_date_count=count,
        dates_consecutive=consecutive,
        coverage_status="complete" if count == 28 and consecutive else "partial",
    )


def extract_reporting_period(workbook: Any, max_rows: int) -> tuple[date | None, date | None]:
    """Preserve the legacy endpoint helper while sharing the coverage extraction.
    保留旧起止日期辅助函数，同时复用覆盖提取。
    """
    evidence = extract_reporting_evidence(workbook, max_rows)
    return evidence.period_start, evidence.period_end
