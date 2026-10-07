"""Identify only the columns and sheets belonging to GSC page performance.
仅识别属于 GSC 网页表现的列与工作表。
"""

import re
from collections.abc import Sequence
from typing import Any

COLUMN_ALIASES = {
    "url": {"page", "pages", "url", "top pages", "top page", "排名靠前的网页", "网页"},
    "clicks": {"clicks", "click", "点击次数", "点击数"},
    "impressions": {"impressions", "impression", "展示", "展示次数", "展示数"},
    "ctr": {"ctr", "click through rate", "click-through rate", "点击率"},
    "position": {"position", "average position", "avg position", "排名", "平均排名"},
}

PAGE_SHEET_NAMES = ("pages", "网页")
FILTER_SHEET_NAMES = {"filters", "filter", "过滤器"}
NON_PAGE_SHEET_NAMES = {
    "queries",
    "query",
    "countries",
    "country",
    "devices",
    "device",
    "dates",
    "date",
    "chart",
    "search appearance",
    "查询数",
    "查询",
    "国家 地区",
    "国家/地区",
    "国家",
    "设备",
    "图表",
    "日期",
    "搜索结果呈现",
    *FILTER_SHEET_NAMES,
}


def normalize_label(value: Any) -> str:
    """Match source labels case-insensitively with harmless spacing variations.
    忽略来源标签的大小写与无害的空格差异进行匹配。
    """
    return re.sub(r"\s+", " ", str(value or "").strip().replace("_", " ")).casefold()


def map_columns(headers: Sequence[Any]) -> tuple[dict[str, int], dict[str, str]]:
    """Resolve the small GSC-specific alias set and reject ambiguous duplicate columns.
    解析少量 GSC 专用别名，并拒绝含义不明确的重复列。
    """
    indices: dict[str, int] = {}
    labels: dict[str, str] = {}
    for index, header in enumerate(headers):
        normalized = normalize_label(header)
        for field, aliases in COLUMN_ALIASES.items():
            if normalized in aliases:
                if field in indices:
                    raise ValueError(f"Multiple columns match '{field}'.")
                indices[field] = index
                labels[field] = str(header).strip()
    return indices, labels
