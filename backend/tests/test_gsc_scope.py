"""Exercise bilingual workbook scope and scope-bound previews using synthetic uploads.
使用合成上传验证双语工作簿范围与绑定范围的预览。
"""

import hashlib
import io

import pytest
from openpyxl import Workbook

from app.imports.gsc.parser import ImportFileError, parse_gsc_pages
from app.normalization.report_scope import ScopeDeclaration
from tests.test_gsc_parser import ENGLISH_HEADERS, csv_file, xlsx_file


def scope_workbook(rows, sheet="Filters", extra=None):
    sheets = {"Pages": [ENGLISH_HEADERS, ["https://example.test/a", 1, 10, 0.1, 1]], sheet: rows}
    sheets.update(extra or {})
    return xlsx_file(sheets)


@pytest.mark.parametrize(
    ("sheet", "rows"),
    [
        ("Filters", [["Filter", "Value"], ["Search type", "Web"], ["Date", "Last 28 days"]]),
        ("过滤器", [["过滤器", "值"], ["搜索类型", "网络"], ["日期", "过去 28 天"]]),
    ],
)
def test_observed_search_type_does_not_infer_property_or_an_empty_filter_ledger(sheet, rows):
    result = parse_gsc_pages(scope_workbook(rows, sheet), "production-name-2026-10-07.xlsx")
    scope = result.preview.report_scope
    assert scope.search_type == "web"
    assert scope.workbook_observed.search_type == "web"
    assert scope.property_id is None
    assert scope.site_identifier is None
    assert not scope.filters_complete
    assert scope.status == "unknown"
    assert scope.issues == []


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        (
            [["Property", "sc-domain:EXAMPLE.TEST"], ["Device", "Mobile"], ["Country", "USA"]],
            {"country": "USA", "device": "mobile"},
        ),
        (
            [["资源属性", "sc-domain:example.test"], ["设备", "移动设备"], ["国家/地区", "美国"]],
            {"country": "USA", "device": "mobile"},
        ),
    ],
)
def test_supported_property_and_localized_filter_facts_are_partial_observed_evidence(
    rows, expected
):
    result = parse_gsc_pages(scope_workbook(rows), "export.xlsx")
    scope = result.preview.report_scope
    assert scope.property_id == "sc-domain:example.test"
    assert {item.dimension: item.value for item in scope.filters} == expected
    assert not scope.filters_complete
    assert scope.status == "unknown"


def test_explicit_declaration_fills_missing_identity_without_replacing_observed_search_type():
    declaration = ScopeDeclaration(property_id="sc-domain:example.test", filters=[])
    result = parse_gsc_pages(scope_workbook([["搜索类型", "网络"]]), "export.xlsx", declaration)
    scope = result.preview.report_scope
    assert scope.status == "known"
    assert scope.property_id == declaration.property_id
    assert scope.user_declared.search_type is None
    assert scope.workbook_observed.search_type == "web"
    assert scope.filters_complete


def test_csv_supports_explicit_scope_but_absence_stays_unknown():
    content = csv_file([["https://example.test/a", 1, 10, 0.1, 1]])
    unknown = parse_gsc_pages(content, "example.test.csv")
    assert unknown.preview.report_scope.status == "unknown"
    known = parse_gsc_pages(
        content,
        "example.test.csv",
        ScopeDeclaration(property_id="sc-domain:example.test", search_type="Web", filters=[]),
    )
    assert known.preview.report_scope.status == "known"
    assert known.preview.report_scope.workbook_observed.model_dump() == {
        "property_id": None,
        "search_type": None,
        "filters": None,
    }
    assert known.preview.coverage_status == "unknown"


@pytest.mark.parametrize(
    "row",
    [
        ["Query", "contains lamp"],
        ["Page", "https://example.test/"],
        ["Country", "Ambiguous country name"],
        ["Device", "Watch"],
        ["Search appearance", "Product snippets"],
        ["Unknown filter", "present"],
        ["Search type", "=1+1"],
        ["Property", "example.test"],
        ["Device", "mobile", "extra unsupported cell"],
    ],
)
def test_unsupported_or_ambiguous_workbook_metadata_remains_uncertain(row):
    result = parse_gsc_pages(
        scope_workbook([row]),
        "export.xlsx",
        ScopeDeclaration(property_id="sc-domain:example.test", search_type="web", filters=[]),
    )
    assert result.preview.can_apply
    assert result.preview.report_scope.status == "unknown"
    assert result.preview.report_scope.issues
    assert not result.preview.report_scope.filters_complete


@pytest.mark.parametrize(
    ("row", "operator", "value"),
    [
        (["Query contains", "Brass  Lamp"], "contains", "Brass  Lamp"),
        (["查询不包含", "Brass Lamp"], "not_contains", "Brass Lamp"),
        (["Query regex", " ^Lamp[ ]+$ "], "regex", " ^Lamp[ ]+$ "),
        (["网页等于", "https://example.test/Path/"], "equals", "https://example.test/Path/"),
    ],
)
def test_operator_bearing_text_labels_preserve_the_observed_condition(row, operator, value):
    result = parse_gsc_pages(scope_workbook([row]), "export.xlsx")
    item = result.preview.report_scope.filters[0]
    assert item.operator == operator
    assert item.value == value
    assert not result.preview.report_scope.filters_complete


@pytest.mark.parametrize(
    ("rows", "declaration"),
    [
        ([["Search type", "Image"]], {"search_type": "web"}),
        ([["Property", "sc-domain:other.test"]], {"property_id": "sc-domain:example.test"}),
        ([["Device", "mobile"]], {"filters": []}),
        (
            [["Device", "mobile"]],
            {"filters": [{"dimension": "device", "operator": "equals", "value": "desktop"}]},
        ),
    ],
)
def test_declarations_conflicting_with_supported_source_evidence_are_rejected(rows, declaration):
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(scope_workbook(rows), "export.xlsx", ScopeDeclaration(**declaration))
    assert caught.value.code == "scope_declaration_conflict"


@pytest.mark.parametrize(
    "rows",
    [
        [["Search type", "web"], ["Search type", "image"]],
        [["Property", "sc-domain:example.test"], ["Property", "sc-domain:other.test"]],
        [["Device", "mobile"], ["Device", "desktop"]],
    ],
)
def test_conflicting_workbook_scope_rows_are_not_silently_resolved(rows):
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(scope_workbook(rows), "export.xlsx")
    assert caught.value.code == "conflicting_scope_metadata"


def test_aggregate_country_and_device_sheets_do_not_supply_applied_filters():
    result = parse_gsc_pages(
        scope_workbook(
            [],
            extra={
                "Countries": [["Country", "Clicks"], ["USA", 1]],
                "Devices": [["Device", "Clicks"], ["mobile", 1]],
            },
        ),
        "export.xlsx",
    )
    assert result.preview.report_scope.filters == []
    assert not result.preview.report_scope.filters_complete


def test_confirmation_changes_with_scope_or_evidence_origin_but_not_filename_or_ordering():
    content = csv_file([["https://example.test/a", 1, 10, 0.1, 1]])
    declaration = ScopeDeclaration(
        property_id="sc-domain:example.test",
        search_type="web",
        filters=[
            {"dimension": "country", "operator": "equals", "value": "USA"},
            {"dimension": "device", "operator": "equals", "value": "mobile"},
        ],
    )
    first = parse_gsc_pages(content, "first.csv", declaration).preview
    reordered = declaration.model_copy(update={"filters": list(reversed(declaration.filters))})
    # Revalidate copied objects so equivalent ordering is canonical at the input boundary.
    # 在输入边界重新校验复制对象，使等价顺序规范化。
    reordered = ScopeDeclaration.model_validate(reordered.model_dump())
    second = parse_gsc_pages(content, "renamed.csv", reordered).preview
    assert first.file_hash == second.file_hash == hashlib.sha256(content).hexdigest()
    assert first.preview_hash == second.preview_hash
    assert first.preview_hash != first.file_hash
    changed = parse_gsc_pages(
        content,
        "first.csv",
        ScopeDeclaration(property_id="sc-domain:other.test", search_type="web", filters=[]),
    ).preview
    assert changed.file_hash == first.file_hash
    assert changed.preview_hash != first.preview_hash
    assert changed.report_scope.fingerprint != first.report_scope.fingerprint


def test_confirmed_preview_binds_observed_versus_declared_origin_for_equal_semantic_scope():
    content = scope_workbook([["Search type", "Web"]])
    observed = parse_gsc_pages(
        content, "export.xlsx", ScopeDeclaration(property_id="sc-domain:example.test", filters=[])
    ).preview
    both = parse_gsc_pages(
        content,
        "export.xlsx",
        ScopeDeclaration(property_id="sc-domain:example.test", search_type="web", filters=[]),
    ).preview
    assert observed.report_scope.fingerprint == both.report_scope.fingerprint
    assert observed.preview_hash != both.preview_hash


def test_scope_worksheet_scan_keeps_the_existing_physical_row_limit(monkeypatch):
    monkeypatch.setattr("app.imports.gsc.parser.MAX_ROWS", 2)
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(
            scope_workbook([["Search type", "web"], ["Device", "mobile"], ["Country", "USA"]]),
            "oversized.xlsx",
        )
    assert caught.value.code == "too_many_rows"


@pytest.mark.parametrize(
    "row",
    [
        ["Property", '=CONCAT("sc-domain:","example.test")'],
        ["Search type", '="web"'],
        ["Query equals", "=A1"],
        ["Device", '="mobile"'],
        ['="Query equals"', "lamp"],
    ],
)
def test_formula_metadata_is_not_observed_literal_scope_even_if_the_user_declares_it(row):
    result = parse_gsc_pages(
        scope_workbook([row]),
        "formula-scope.xlsx",
        ScopeDeclaration(
            property_id="sc-domain:example.test",
            search_type="web",
            filters=[{"dimension": "query", "operator": "equals", "value": "=A1"}],
        ),
    )
    scope = result.preview.report_scope
    assert scope.status == "unknown"
    assert not scope.filters_complete
    assert "formula_scope_metadata" in scope.issues
    assert scope.workbook_observed.model_dump() == {
        "property_id": None,
        "search_type": None,
        "filters": None,
    }


def test_explicit_literal_scope_text_beginning_with_equals_is_not_a_formula():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Pages"
    for row in [ENGLISH_HEADERS, ["https://example.test/a", 1, 10, 0.1, 1]]:
        sheet.append(row)
    metadata = workbook.create_sheet("Filters")
    metadata.append(["Query equals", "=A1"])
    metadata["B1"].data_type = "s"
    content = io.BytesIO()
    workbook.save(content)
    workbook.close()
    result = parse_gsc_pages(
        content.getvalue(),
        "literal-scope.xlsx",
        ScopeDeclaration(
            property_id="sc-domain:example.test",
            search_type="web",
            filters=[{"dimension": "query", "operator": "equals", "value": "=A1"}],
        ),
    )
    assert result.preview.report_scope.status == "known"
    assert result.preview.report_scope.issues == []
    assert result.preview.report_scope.workbook_observed.filters[0].value == "=A1"
