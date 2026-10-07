"""Extract observed reporting dates from GSC-specific worksheet evidence only.
仅从 GSC 专用工作表证据中提取观察到的报告日期。
"""

import re
from datetime import date, datetime
from typing import Any

from app.imports.gsc.mapping import normalize_label
from app.normalization.gsc import is_blank

DATE_SHEET_NAMES = {"chart", "date", "dates", "图表", "日期"}
DATE_HEADERS = {"date", "dates", "日期"}
ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")


class PeriodWorksheetTooLarge(ValueError):
    """Signal metadata size limits without coupling date extraction to HTTP errors.
    表示元数据超过大小限制，避免将日期提取与 HTTP 错误耦合。
    """


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


def extract_reporting_period(workbook: Any, max_rows: int) -> tuple[date | None, date | None]:
    """Use matching date sets to establish observed bounds; uncertain evidence stays unknown.
    使用一致的日期集合确定观察范围；不确定的证据保持未知。

    Duplicate and unsorted days are valid; no missing days or 28-day coverage are invented.
    允许重复或未排序的日期；不补造缺失日期，也不假定覆盖完整的 28 天。
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
        return None, None
    return min(evidence), max(evidence)
