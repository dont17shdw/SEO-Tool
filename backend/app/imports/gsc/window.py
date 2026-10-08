"""Validate 28-day export labels without creating reporting dates or daily coverage.
校验 28 天导出标签，不创建报告日期或每日覆盖。
"""

import re
from datetime import date
from typing import Any

from app.imports.gsc.mapping import FILTER_SHEET_NAMES, normalize_label
from app.imports.gsc.period import ReportingEvidence
from app.normalization.gsc import is_blank

LATEST_LABELS = {"last28days", "past28days", "28days", "过去28天", "最近28天"}
CUSTOM_LABELS = {"custom", "custom date range", "自定义", "自定义日期范围"}
DATE_LABELS = {"date", "dates", "date range", "日期"}
CALENDAR_TOKEN = r"(?:[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)"
CUSTOM_RANGE = re.compile(
    rf"(?:custom(?: date range)?|自定义(?:日期范围)?)?\s*[:：]?\s*"
    rf"(?P<start>{CALENDAR_TOKEN})\s*(?:to|至|到|[-–—])\s*"
    rf"(?P<end>{CALENDAR_TOKEN})\Z",
    re.IGNORECASE,
)


class ReportingWindowError(ValueError):
    """Keep workbook validation independent of HTTP and persistence behavior.
    使工作簿校验独立于 HTTP 与持久化行为。
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _calendar_date(value: str) -> date:
    """Parse only explicit ISO or unambiguous Chinese calendar dates.
    仅解析明确的 ISO 日期或无歧义的中文日历日期。
    """
    if "年" in value:
        year, month, day = re.fullmatch(r"([0-9]{4})年([0-9]{1,2})月([0-9]{1,2})日", value).groups()
        return date(int(year), int(month), int(day))
    return date.fromisoformat(value)


def validate_reporting_window(workbook: Any, evidence: ReportingEvidence, max_rows: int) -> None:
    """Accept latest labels or bounded custom reports while preserving observed-date facts.
    接受最近日期标签或有明确边界的自定义报告，同时保留已观察日期事实。

    Explicit ranges prove only the declared 28-day window, never missing daily observations.
    明确范围仅证明声明的 28 天窗口，绝不证明缺失的每日观察。
    Bare custom labels need independently complete observed coverage before acceptance.
    仅有自定义标签时，接受前需要独立且完整的已观察覆盖。
    The legacy latest_28_days identifier remains the existing 28-day metric family.
    旧 latest_28_days 标识仍表示现有的 28 天指标类别。
    """
    ranges: set[tuple[date, date]] = set()
    bare_custom = False
    for name in workbook.sheetnames:
        if normalize_label(name) not in FILTER_SHEET_NAMES:
            continue
        sheet = workbook[name]
        sheet.reset_dimensions()
        for count, row in enumerate(sheet.iter_rows(values_only=True), start=1):
            if count > max_rows:
                raise ReportingWindowError("too_many_rows", "The Filters worksheet is too large.")
            if not row or normalize_label(row[0]) not in DATE_LABELS:
                continue
            value = row[1] if len(row) > 1 else None
            if is_blank(value):
                continue
            label = normalize_label(value)
            if re.sub(r"[\s_-]+", "", label) in LATEST_LABELS:
                continue
            if label in CUSTOM_LABELS:
                bare_custom = True
                continue
            matched = CUSTOM_RANGE.fullmatch(str(value).strip()) if isinstance(value, str) else None
            if matched is not None:
                try:
                    start = _calendar_date(matched["start"])
                    end = _calendar_date(matched["end"])
                except ValueError:
                    pass
                else:
                    if (end - start).days == 27:
                        ranges.add((start, end))
                        continue
            raise ReportingWindowError(
                "unsupported_reporting_window",
                "Use a latest-28-days label or an explicit custom range of exactly 28 days. / "
                "请使用最近 28 天标签，或明确且恰为 28 天的自定义范围。",
            )

    if len(ranges) > 1:
        raise ReportingWindowError(
            "conflicting_reporting_dates",
            "Workbook date labels declare conflicting custom ranges. / "
            "工作簿日期标签声明了冲突的自定义范围。",
        )
    if ranges and evidence.period_start is not None:
        start, end = next(iter(ranges))
        if evidence.period_start < start or evidence.period_end > end:
            raise ReportingWindowError(
                "conflicting_reporting_dates",
                "Observed reporting dates fall outside the declared custom range. / "
                "已观察报告日期超出了声明的自定义范围。",
            )
    if bare_custom and evidence.coverage_status != "complete":
        raise ReportingWindowError(
            "unsupported_reporting_window",
            "A bare Custom label requires 28 distinct consecutive observed dates. / "
            "仅有自定义标签时，需要 28 个不同且连续的已观察日期。",
        )
