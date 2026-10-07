"""Exercise localized GSC exports using generated, non-private page performance data.
使用生成的非私密网页表现数据测试本地化 GSC 导出文件。
"""

import csv
import io
from decimal import Decimal

import pytest
from openpyxl import Workbook

from app.imports.gsc.parser import MAX_FILE_SIZE, MAX_ROWS, ImportFileError, parse_gsc_pages
from app.normalization.gsc import MAX_COUNT

ENGLISH_HEADERS = ["Page", "Clicks", "Impressions", "CTR", "Position"]
CHINESE_HEADERS = ["排名靠前的网页", "点击次数", "展示", "点击率", "排名"]


def csv_file(rows, headers=None, delimiter=",") -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=delimiter)
    writer.writerow(headers or ENGLISH_HEADERS)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def xlsx_file(sheets: dict[str, list]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        sheet = workbook.create_sheet(name)
        for row in rows:
            sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()


def test_valid_csv_normalizes_metrics_and_preserves_url_identity():
    content = csv_file([["  HTTPS://example.test/Path/?Q=One  ", "12", "480", "2.5%", "8.125"]])
    result = parse_gsc_pages(content, "export.CSV")
    assert result.preview.can_apply
    assert result.preview.detected_sheet is None
    assert result.preview.reporting_window == "latest_28_days"
    assert result.preview.column_mapping == dict(
        zip(["url", "clicks", "impressions", "ctr", "position"], ENGLISH_HEADERS, strict=True)
    )
    assert result.rows[0].model_dump() == {
        "row": 2,
        "url": "HTTPS://example.test/Path/?Q=One",
        "clicks_28d": 12,
        "impressions_28d": 480,
        "ctr": Decimal("0.025000"),
        "average_position": Decimal("8.1250"),
    }
    assert parse_gsc_pages(content, "export.csv").preview == result.preview


@pytest.mark.parametrize("delimiter", [",", ";", "\t"])
def test_localized_csv_bom_and_common_delimiters(delimiter):
    result = parse_gsc_pages(
        b"\xef\xbb\xbf"
        + csv_file([["https://example.test/page", 2, 20, "10%", 3]], CHINESE_HEADERS, delimiter),
        "localized.csv",
    )
    assert result.preview.can_apply
    assert result.preview.column_mapping["url"] == "排名靠前的网页"
    assert result.rows[0].ctr == Decimal("0.100000")


@pytest.mark.parametrize("page_name", ["Pages", "pAgEs", " PAGES ", "网页"])
def test_xlsx_detects_recognized_page_sheets_with_other_dimensions_present(page_name):
    headers = CHINESE_HEADERS if page_name == "网页" else ENGLISH_HEADERS
    content = xlsx_file(
        {
            "Queries": [["Query", *ENGLISH_HEADERS[1:]], ["synthetic query", 99, 500, 0.198, 2]],
            "图表": [["日期", *CHINESE_HEADERS[1:]], ["2026-01-01", 5, 50, 0.1, 5]],
            page_name: [headers, ["https://example.test/page", 3, 30, 0.1, 4.125]],
            "过滤器": [["筛选器", "值"], ["日期", "过去 28 天"]],
        }
    )
    result = parse_gsc_pages(content, "export.xlsx")
    assert result.preview.detected_sheet == page_name
    assert result.preview.total_rows == 1
    assert result.rows[0].clicks_28d == 3
    assert result.rows[0].ctr == Decimal("0.100000")


def test_pages_is_preferred_over_localized_and_fallback_sheets():
    content = xlsx_file(
        {
            "网页": [CHINESE_HEADERS, ["https://example.test/chinese", 1, 10, 0.1, 1]],
            "Other": [ENGLISH_HEADERS, ["https://example.test/fallback", 2, 20, 0.1, 2]],
            "Pages": [ENGLISH_HEADERS, ["https://example.test/english", 3, 30, 0.1, 3]],
        }
    )
    result = parse_gsc_pages(content, "pages.xlsx")
    assert result.preview.detected_sheet == "Pages"
    assert result.rows[0].url == "https://example.test/english"


def test_named_pages_keeps_invalid_url_as_preview_error():
    result = parse_gsc_pages(
        xlsx_file({"Pages": [ENGLISH_HEADERS, ["synthetic search query", 1, 10, 0.1, 1]]}),
        "pages.xlsx",
    )
    assert result.preview.invalid_rows == 1
    assert result.preview.errors[0].code == "invalid_url"
    assert not result.preview.can_apply


def test_fallback_requires_page_headers_and_url_evidence():
    result = parse_gsc_pages(
        xlsx_file(
            {
                "Export": [
                    ENGLISH_HEADERS,
                    ["https://example.test/a", 1, 10, 0.1, 1],
                    ["bad", 2, 20, 0.1, 2],
                ]
            }
        ),
        "pages.xlsx",
    )
    assert result.preview.detected_sheet == "Export"
    assert result.preview.valid_rows == 1
    assert result.preview.invalid_rows == 1
    assert not result.preview.can_apply


@pytest.mark.parametrize(
    "name",
    [
        "Queries",
        "Countries",
        "Devices",
        "Dates",
        "查询数",
        "国家_地区",
        "设备",
        "搜索结果呈现",
        "图表",
    ],
)
def test_known_unrelated_sheets_are_never_selected_even_with_page_like_columns(name):
    with pytest.raises(ImportFileError, match="No GSC Pages") as caught:
        parse_gsc_pages(
            xlsx_file({name: [ENGLISH_HEADERS, ["https://example.test/not-pages", 1, 10, 0.1, 1]]}),
            "wrong.xlsx",
        )
    assert caught.value.code == "pages_sheet_missing"


@pytest.mark.parametrize("headers", [ENGLISH_HEADERS, ["Query", *ENGLISH_HEADERS[1:]]])
def test_unknown_sheet_of_queries_is_rejected(headers):
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(
            xlsx_file({"Export": [headers, ["synthetic query", 1, 10, 0.1, 1]]}),
            "wrong.xlsx",
        )
    assert caught.value.code == "pages_sheet_missing"


def test_multiple_fallback_candidates_are_rejected():
    sheets = {
        name: [ENGLISH_HEADERS, [f"https://example.test/{name}", 1, 10, 0.1, 1]]
        for name in ["One", "Two"]
    }
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(xlsx_file(sheets), "ambiguous.xlsx")
    assert caught.value.code == "ambiguous_pages_sheet"


@pytest.mark.parametrize("value", ["Last 28 days", "LAST 28 DAYS", "过去 28 天", "最近28天"])
def test_recognized_latest_28_day_metadata_is_accepted(value):
    content = xlsx_file(
        {
            "Pages": [ENGLISH_HEADERS, ["https://example.test/a", 1, 10, 0.1, 1]],
            "Filters": [["Date", value]],
        }
    )
    assert parse_gsc_pages(content, "pages.xlsx").preview.can_apply


@pytest.mark.parametrize("value", ["Last 7 days", "过去 3 个月", "2026-01-01 to 2026-01-28"])
def test_conflicting_date_metadata_is_rejected(value):
    content = xlsx_file(
        {
            "Pages": [ENGLISH_HEADERS, ["https://example.test/a", 1, 10, 0.1, 1]],
            "Filters": [["Date", value]],
        }
    )
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(content, "pages.xlsx")
    assert caught.value.code == "unsupported_reporting_window"


@pytest.mark.parametrize("url_header", ["Page", "Pages", "URL", "Top pages", "排名靠前的网页"])
def test_source_aliases_and_case_insensitive_metrics(url_header):
    result = parse_gsc_pages(
        csv_file(
            [["https://example.test/a", 1, 10, "10%", 1]],
            [url_header, "CLICKS", " impressions ", "ctr", "Average position"],
        ),
        "aliases.csv",
    )
    assert result.preview.can_apply
    assert result.preview.column_mapping["url"] == url_header


@pytest.mark.parametrize("removed", range(5))
def test_missing_required_semantic_column(removed):
    headers = ENGLISH_HEADERS[:removed] + ENGLISH_HEADERS[removed + 1 :]
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(csv_file([["https://example.test/a", 1, 10, 0.1]], headers), "missing.csv")
    assert caught.value.code == (
        "missing_url_column" if removed == 0 else "missing_performance_columns"
    )


def test_duplicate_semantic_columns_are_rejected():
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(
            csv_file([["https://example.test/a", 1, 10, 0.1, 1, 1]], ENGLISH_HEADERS + ["clicks"]),
            "ambiguous.csv",
        )
    assert caught.value.code == "ambiguous_columns"


@pytest.mark.parametrize(
    "url",
    [
        "",
        " ",
        "/relative",
        "ftp://example.test/a",
        "https://",
        "https://exa mple.test/a",
        "https://example.test:70000/a",
        "https://example..test/a",
        "https://example.test/a\npath",
        "https://example.test\\a",
        "https://999.999.999.999/a",
    ],
)
def test_invalid_urls_are_row_errors(url):
    preview = parse_gsc_pages(csv_file([[url, 1, 10, 0.1, 1]]), "invalid.csv").preview
    assert preview.invalid_rows == 1
    assert preview.valid_rows == 0
    assert preview.errors[0].field == "url"
    assert not preview.can_apply


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8000/a",
        "https://[2001:db8::1]/a",
        "https://例子.test/页面",
        "https://example.test/a?x=1&x=2#fragment",
    ],
)
def test_valid_absolute_url_forms_are_preserved(url):
    result = parse_gsc_pages(csv_file([[url, 1, 10, 0.1, 1]]), "valid.csv")
    assert result.preview.can_apply
    assert result.rows[0].url == url


@pytest.mark.parametrize("field,index", [("clicks", 1), ("impressions", 2)])
@pytest.mark.parametrize(
    "value", ["-1", "1.5", "NaN", "Infinity", str(MAX_COUNT + 1), "not a number", "1,2"]
)
def test_invalid_counts_are_rejected(field, index, value):
    row = ["https://example.test/a", 1, 10, 0.1, 1]
    row[index] = value
    preview = parse_gsc_pages(csv_file([row]), "invalid.csv").preview
    assert preview.invalid_rows == 1
    assert preview.errors[0].code == f"invalid_{field}"


def test_count_exact_json_boundary_and_grouping_are_supported():
    result = parse_gsc_pages(
        csv_file([["https://example.test/a", str(MAX_COUNT), "1,234", "0%", 0]]),
        "counts.csv",
    )
    assert result.preview.can_apply
    assert result.rows[0].clicks_28d == MAX_COUNT
    assert result.rows[0].impressions_28d == 1234


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2.5%", "0.025000"),
        ("0.025", "0.025000"),
        ("100%", "1.000000"),
        ("1", "1.000000"),
        ("0.1234565", "0.123457"),
    ],
)
def test_ctr_percent_fraction_and_database_precision(value, expected):
    result = parse_gsc_pages(
        csv_file([["https://example.test/a", 1, 10, value, "1.23445"]]), "ctr.csv"
    )
    assert result.rows[0].ctr == Decimal(expected)
    assert result.rows[0].average_position == Decimal("1.2345")


@pytest.mark.parametrize(
    "value",
    [
        "-0.01",
        "1.0000001",
        "100.0000001%",
        "-1%",
        "2.5",
        "NaN",
        "Infinity",
        "text",
        "1e1000000%",
        "1e999999999999999999999%",
    ],
)
def test_invalid_ctr_is_a_row_error_including_extreme_percent_values(value):
    preview = parse_gsc_pages(
        csv_file([["https://example.test/a", 1, 10, value, 1]]), "invalid.csv"
    ).preview
    assert preview.invalid_rows == 1
    assert preview.errors[0].code == "invalid_ctr"


@pytest.mark.parametrize(
    "value", ["-1", "-0.000001", "NaN", "Infinity", "text", "1000000", "999999.99995"]
)
def test_invalid_position_is_a_row_error(value):
    preview = parse_gsc_pages(
        csv_file([["https://example.test/a", 1, 10, 0.1, value]]), "invalid.csv"
    ).preview
    assert preview.invalid_rows == 1
    assert preview.errors[0].code == "invalid_position"


@pytest.mark.parametrize("extension", ["csv", "xlsx"])
def test_missing_optional_metric_values_remain_null(extension):
    rows = [["https://example.test/a", None, " ", None, None]]
    content = (
        csv_file(rows) if extension == "csv" else xlsx_file({"Pages": [ENGLISH_HEADERS, *rows]})
    )
    result = parse_gsc_pages(content, f"unknown.{extension}")
    assert result.preview.can_apply
    normalized = result.rows[0]
    assert normalized.clicks_28d is None
    assert normalized.impressions_28d is None
    assert normalized.ctr is None
    assert normalized.average_position is None


@pytest.mark.parametrize(
    "column,field", [(1, "clicks"), (2, "impressions"), (3, "ctr"), (4, "position")]
)
def test_xlsx_metric_formulas_are_rejected_instead_of_becoming_null(column, field):
    row = ["https://example.test/a", 1, 10, 0.1, 1]
    row[column] = "=2+2"
    result = parse_gsc_pages(xlsx_file({"Pages": [ENGLISH_HEADERS, row]}), "formula.xlsx")
    assert not result.preview.can_apply
    assert result.preview.invalid_rows == 1
    assert result.preview.errors[0].field == field


def test_xlsx_boolean_metrics_are_rejected():
    result = parse_gsc_pages(
        xlsx_file({"Pages": [ENGLISH_HEADERS, ["https://example.test/a", True, 10, 0.1, 1]]}),
        "boolean.xlsx",
    )
    assert result.preview.errors[0].code == "invalid_clicks"
    assert not result.preview.can_apply


def test_duplicate_urls_mark_all_occurrences_and_do_not_aggregate():
    rows = [
        ["https://example.test/a", 1, 10, 0.1, 1],
        [" https://example.test/a ", 2, 20, 0.1, 2],
        ["https://example.test/a/", 3, 30, 0.1, 3],
        ["https://example.test/A", 4, 40, 0.1, 4],
    ]
    result = parse_gsc_pages(csv_file(rows), "duplicates.csv")
    assert result.preview.total_rows == 4
    assert result.preview.duplicate_rows == 2
    assert result.preview.invalid_rows == 0
    assert result.preview.valid_rows == 2
    assert not result.preview.can_apply
    assert [error.row for error in result.preview.errors if error.code == "duplicate_url"] == [2, 3]
    assert [row.clicks_28d for row in result.rows] == [3, 4]


def test_duplicate_with_invalid_metrics_is_not_double_counted():
    result = parse_gsc_pages(
        csv_file(
            [["https://example.test/a", -1, 10, 0.1, 1], ["https://example.test/a", 2, 20, 0.1, 2]]
        ),
        "duplicates.csv",
    )
    assert result.preview.duplicate_rows == 2
    assert result.preview.invalid_rows == 0
    assert result.preview.valid_rows == 0
    assert {error.code for error in result.preview.errors} == {"invalid_clicks", "duplicate_url"}


def test_preview_caps_samples_and_errors_without_losing_counts():
    rows = [[f"https://example.test/good-{i}", 1, 10, 0.1, 1] for i in range(12)]
    rows += [[f"https://example.test/bad-{i}", -1, 10, 0.1, 1] for i in range(105)]
    result = parse_gsc_pages(csv_file(rows), "large.csv")
    assert result.preview.total_rows == 117
    assert result.preview.valid_rows == 12
    assert result.preview.invalid_rows == 105
    assert len(result.preview.sample_rows) == 10
    assert len(result.rows) == 12
    assert len(result.preview.errors) == 100
    assert not result.preview.can_apply


@pytest.mark.parametrize(
    "content,filename,code",
    [
        (b"", "empty.csv", "empty_file"),
        (b" \n\t", "empty.xlsx", "empty_file"),
        (csv_file([]), "headers.csv", "empty_file"),
        (b'Page,Clicks,Impressions,CTR,Position\n"unclosed,1,2,3,4', "broken.csv", "malformed_csv"),
        (b"\xff\xfe", "encoding.csv", "malformed_csv"),
        (b"\x00", "nul.csv", "malformed_csv"),
        (b"not a workbook", "broken.xlsx", "malformed_xlsx"),
        (b"anything", "wrong.txt", "unsupported_file_type"),
    ],
)
def test_structural_errors_are_clear(content, filename, code):
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(content, filename)
    assert caught.value.code == code
    assert caught.value.message


def test_upload_size_limit_is_enforced_before_parsing():
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(b"x" * (MAX_FILE_SIZE + 1), "large.csv")
    assert caught.value.code == "file_too_large"


def test_row_limit_is_enforced_for_csv():
    content = csv_file([[f"https://example.test/{i}", 1, 10, 0.1, 1] for i in range(MAX_ROWS + 1)])
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(content, "large.csv")
    assert caught.value.code == "too_many_rows"


def test_extra_unquoted_csv_values_are_row_errors():
    result = parse_gsc_pages(
        b"Page,Clicks,Impressions,CTR,Position\nhttps://example.test/a,1,10,0.1,1,extra",
        "broken.csv",
    )
    assert result.preview.errors[0].code == "unexpected_columns"
    assert result.preview.invalid_rows == 1
    assert not result.preview.can_apply
