"""Read supported workbook scope facts and reconcile explicit user declarations.
读取受支持的工作簿范围事实，并核对明确的用户声明。
"""

from typing import Any

from pydantic import ValidationError

from app.imports.gsc.mapping import FILTER_SHEET_NAMES, normalize_label
from app.normalization.gsc import is_blank
from app.normalization.report_scope import (
    ReportScope,
    ScopeDeclaration,
    ScopeFilter,
    compare_report_scopes,
)

PROPERTY_LABELS = {
    "property",
    "gsc property",
    "property id",
    "gsc property identifier",
    "search console property",
    "属性",
    "资源属性",
    "网站属性",
    "属性标识符",
    "gsc 属性",
    "gsc属性",
}
SEARCH_TYPE_LABELS = {"search type", "搜索类型"}
DATE_LABELS = {"date", "dates", "date range", "日期"}
FILTER_LABELS = {
    "country": "country",
    "country/region": "country",
    "country region": "country",
    "国家": "country",
    "国家/地区": "country",
    "国家 地区": "country",
    "device": "device",
    "设备": "device",
    "search appearance": "search_appearance",
    "搜索结果呈现": "search_appearance",
}
TEXT_FILTER_LABELS = {
    "query equals": ("query", "equals"),
    "查询等于": ("query", "equals"),
    "query not equals": ("query", "not_equals"),
    "查询不等于": ("query", "not_equals"),
    "query contains": ("query", "contains"),
    "查询包含": ("query", "contains"),
    "query not contains": ("query", "not_contains"),
    "查询不包含": ("query", "not_contains"),
    "query regex": ("query", "regex"),
    "查询正则表达式": ("query", "regex"),
    "query not regex": ("query", "not_regex"),
    "查询不匹配正则表达式": ("query", "not_regex"),
    "page equals": ("page", "equals"),
    "网页等于": ("page", "equals"),
    "page not equals": ("page", "not_equals"),
    "网页不等于": ("page", "not_equals"),
    "page contains": ("page", "contains"),
    "网页包含": ("page", "contains"),
    "page not contains": ("page", "not_contains"),
    "网页不包含": ("page", "not_contains"),
    "page regex": ("page", "regex"),
    "网页正则表达式": ("page", "regex"),
    "page not regex": ("page", "not_regex"),
    "网页不匹配正则表达式": ("page", "not_regex"),
}
# Only these unambiguous localized names have a supported ISO identity mapping.
# 仅为这些无歧义的本地化名称提供受支持的 ISO 标识映射。
COUNTRY_NAMES = {
    "united states": "USA",
    "美国": "USA",
    "china": "CHN",
    "中国": "CHN",
    "united kingdom": "GBR",
    "英国": "GBR",
    "canada": "CAN",
    "加拿大": "CAN",
    "australia": "AUS",
    "澳大利亚": "AUS",
    "germany": "DEU",
    "德国": "DEU",
    "france": "FRA",
    "法国": "FRA",
    "india": "IND",
    "印度": "IND",
    "japan": "JPN",
    "日本": "JPN",
}


class ScopeEvidenceError(ValueError):
    """Expose deterministic metadata conflicts independently of HTTP and persistence.
    独立于 HTTP 与持久化，公开确定性的元数据冲突。
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def extract_workbook_scope(workbook: Any, max_rows: int) -> tuple[ScopeDeclaration, list[str]]:
    """Parse reliable supported filter rows without assuming an exhaustive filter ledger.
    解析可靠且受支持的筛选行，不假定筛选清单完整。

    Query/page labels must state their operator; aggregate dimension sheets are not scope evidence.
    查询或网页标签必须明确运算符；聚合维度工作表不是范围证据。
    """
    values: dict[str, str] = {}
    filters: dict[str, ScopeFilter] = {}
    issues: set[str] = set()
    for name in workbook.sheetnames:
        if normalize_label(name) not in FILTER_SHEET_NAMES:
            continue
        sheet = workbook[name]
        sheet.reset_dimensions()
        for count, cells in enumerate(sheet.iter_rows(values_only=False), start=1):
            if count > max_rows:
                raise ScopeEvidenceError("too_many_rows", "The Filters worksheet is too large.")
            row = tuple(cell.value for cell in cells)
            if not row or all(is_blank(value) for value in row):
                continue
            # Cell types distinguish an unevaluated formula from literal text beginning with '='.
            # 单元格类型区分未计算的公式与以 '=' 开头的字面文本。
            if any(getattr(cell, "data_type", None) == "f" for cell in cells):
                issues.add("formula_scope_metadata")
                continue
            label = normalize_label(row[0])
            raw = row[1] if len(row) > 1 else None
            if label in DATE_LABELS:
                continue
            if label in {"filter", "filters", "过滤器", "筛选器"} and normalize_label(raw) in {
                "value",
                "values",
                "值",
            }:
                continue
            if any(not is_blank(value) for value in row[2:]):
                issues.add("unsupported_scope_row_shape")
                continue
            if label in PROPERTY_LABELS or label in SEARCH_TYPE_LABELS:
                field = "property_id" if label in PROPERTY_LABELS else "search_type"
                if not isinstance(raw, str) or not raw.strip():
                    issues.add(f"unparsed_{field}_metadata")
                    continue
                try:
                    normalized = getattr(ScopeDeclaration(**{field: raw}), field)
                except (ValidationError, ValueError):
                    issues.add(f"unparsed_{field}_metadata")
                    continue
                if field in values and values[field] != normalized:
                    raise ScopeEvidenceError(
                        "conflicting_scope_metadata",
                        "Workbook rows provide conflicting scope values. / "
                        "工作簿行提供冲突的范围值。",
                    )
                values[field] = normalized
                continue
            condition = TEXT_FILTER_LABELS.get(label)
            dimension = FILTER_LABELS.get(label)
            if condition is not None:
                dimension, operator = condition
            elif dimension is not None:
                operator = "equals"
            else:
                # A bare Query/Page row does not prove whether its condition is exact or partial.
                # 单独的 Query 或 Page 行不能证明其条件属于精确匹配还是部分匹配。
                issues.add("unsupported_filter_metadata")
                continue
            if not isinstance(raw, str) or not raw.strip():
                issues.add(f"unparsed_{dimension}_filter")
                continue
            value = (
                COUNTRY_NAMES.get(raw.strip().casefold(), raw) if dimension == "country" else raw
            )
            try:
                item = ScopeFilter(dimension=dimension, operator=operator, value=value)
            except ValidationError:
                issues.add(f"unparsed_{dimension}_filter")
                continue
            if dimension in filters and filters[dimension] != item:
                raise ScopeEvidenceError(
                    "conflicting_scope_metadata",
                    "Workbook rows provide conflicting filters. / 工作簿行提供冲突的筛选条件。",
                )
            filters[dimension] = item
    observed = ScopeDeclaration(**values, filters=list(filters.values()) or None)
    return observed, sorted(issues)


def resolve_scope(
    declared: ScopeDeclaration | None = None,
    observed: ScopeDeclaration | None = None,
    issues: list[str] | None = None,
) -> ReportScope:
    """Reconcile observed facts and a complete declared ledger, rejecting explicit conflicts.
    核对观察事实与完整的声明清单，拒绝明确冲突。

    Unsupported source metadata keeps scope uncertain despite an otherwise complete declaration.
    即使声明本身完整，不支持的源元数据仍使范围保持不确定。
    """
    declaration = declared or ScopeDeclaration()
    workbook = observed or ScopeDeclaration()
    workbook_scope = ReportScope(
        property_id=workbook.property_id,
        search_type=workbook.search_type,
        filters=workbook.filters or [],
        filters_complete=False,
    )
    declared_scope = ReportScope(
        property_id=declaration.property_id,
        search_type=declaration.search_type,
        filters=declaration.filters or [],
        filters_complete=declaration.filters is not None,
    )
    compatibility = compare_report_scopes(workbook_scope, declared_scope)
    if compatibility.status == "incompatible":
        raise ScopeEvidenceError(
            "scope_declaration_conflict",
            "Declared scope conflicts with workbook evidence: "
            + ", ".join(compatibility.conflicts)
            + ". / 声明范围与工作簿证据冲突。",
        )
    return ReportScope(
        property_id=declaration.property_id or workbook.property_id,
        search_type=declaration.search_type or workbook.search_type,
        filters=declaration.filters if declaration.filters is not None else workbook.filters or [],
        filters_complete=declaration.filters is not None and not issues,
        workbook_observed=workbook,
        user_declared=declaration,
        issues=sorted(set(issues or [])),
    )
