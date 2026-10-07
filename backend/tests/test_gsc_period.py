"""Verify reporting-period evidence with synthetic spreadsheets, never private exports.
使用合成电子表格验证报告日期证据，不使用私人导出文件。
"""

import io
from datetime import date, datetime, timedelta

import pytest
from openpyxl import Workbook
from pydantic import ValidationError

from app.imports.gsc.parser import ImportFileError, parse_gsc_pages
from app.imports.gsc.schemas import ImportPreview

PAGE_ROWS = [
    ["Page", "Clicks", "Impressions", "CTR", "Position"],
    ["https://example.test/page", 3, 30, 0.1, 5],
]


def workbook_file(date_sheets: dict[str, list[list]] | None = None) -> bytes:
    """Build only synthetic page and metadata worksheets in memory.
    仅在内存中生成合成的网页及元数据工作表。
    """
    workbook = Workbook()
    page_sheet = workbook.active
    page_sheet.title = "Pages"
    for row in PAGE_ROWS:
        page_sheet.append(row)
    for name, rows in (date_sheets or {}).items():
        sheet = workbook.create_sheet(name)
        for row in rows:
            sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("sheet", "header"),
    [("Chart", "Date"), ("Dates", "Dates"), ("Date", "Date"), ("图表", "日期"), ("日期", "日期")],
)
def test_english_and_chinese_28_day_metadata_provides_exact_observed_bounds(sheet, header):
    dates = [date(2026, 1, 1) + timedelta(days=offset) for offset in range(28)]
    result = parse_gsc_pages(
        workbook_file({sheet: [[header, "Clicks"], *[[value.isoformat(), 1] for value in dates]]}),
        "synthetic.xlsx",
    )
    assert result.preview.can_apply
    assert result.preview.period_start == dates[0]
    assert result.preview.period_end == dates[-1]
    assert result.preview.period_status == "exact"
    assert result.preview.observed_date_count == 28
    assert result.preview.dates_consecutive is True
    assert result.preview.coverage_status == "complete"
    assert result.preview.model_dump(mode="json")["period_start"] == "2026-01-01"
    assert result.preview.model_dump(mode="json")["period_status"] == "exact"
    assert result.rows[0].clicks_28d == 3


def test_unsorted_duplicate_and_nonconsecutive_dates_use_only_observed_bounds():
    result = parse_gsc_pages(
        workbook_file(
            {
                "  CHART  ": [
                    ["Date", "Clicks"],
                    ["2026-02-20", 1],
                    ["2026-02-01", 2],
                    ["2026-02-20", 3],
                    [None, None],
                    ["2026-02-10", 4],
                ]
            }
        ),
        "synthetic.xlsx",
    )
    assert result.preview.period_start == date(2026, 2, 1)
    assert result.preview.period_end == date(2026, 2, 20)
    assert result.preview.period_status == "exact"
    assert result.preview.reporting_window == "latest_28_days"
    assert result.preview.observed_date_count == 3
    assert result.preview.dates_consecutive is False
    assert result.preview.coverage_status == "partial"


def test_native_excel_date_and_datetime_cells_are_calendar_dates():
    result = parse_gsc_pages(
        workbook_file(
            {
                "Chart": [
                    ["Clicks", "Date"],
                    [1, datetime(2026, 3, 28, 18, 30)],
                    [2, date(2026, 3, 1)],
                ]
            }
        ),
        "native.xlsx",
    )
    assert result.preview.period_start == date(2026, 3, 1)
    assert result.preview.period_end == date(2026, 3, 28)


@pytest.mark.parametrize(
    "sheets",
    [
        {},
        {"Chart": [["Date", "Clicks"]]},
        {"Dates": [["Unrecognized", "Clicks"], ["2026-01-01", 1]]},
        {"Unrecognized": [["Date", "Clicks"], ["2026-01-01", 1]]},
        {"Chart": [[None], [None]]},
    ],
)
def test_absent_or_unrecognized_evidence_does_not_infer_dates_from_filename(sheets):
    result = parse_gsc_pages(workbook_file(sheets), "export-2026-10-07.xlsx")
    assert result.preview.can_apply
    assert result.preview.period_start is None
    assert result.preview.period_end is None
    assert result.preview.period_status == "unknown"
    assert result.preview.observed_date_count is None
    assert result.preview.dates_consecutive is None
    assert result.preview.coverage_status == "unknown"


def test_csv_dates_remain_unknown_even_when_extra_date_columns_are_present():
    result = parse_gsc_pages(
        b"Page,Clicks,Impressions,CTR,Position,Date\n"
        b"https://example.test/page,3,30,0.1,5,2026-01-01\n",
        "/exports/2026-01-28.csv",
    )
    assert result.preview.can_apply
    assert result.preview.period_start is None
    assert result.preview.period_end is None
    assert result.preview.period_status == "unknown"


@pytest.mark.parametrize(
    "invalid_date",
    [
        "2026-02-30",
        "2026-1-01",
        "20260101",
        "01/01/2026",
        "2026-01-01T00:00:00",
        "=DATE(2026,1,1)",
        "not a date",
        "#VALUE!",
        46000,
        True,
        None,
        " ",
    ],
)
def test_invalid_nonblank_reporting_row_makes_period_unknown_without_blocking_import(invalid_date):
    result = parse_gsc_pages(
        workbook_file({"Chart": [["Date", "Clicks"], ["2026-01-01", 1], [invalid_date, 2]]}),
        "bad-evidence.xlsx",
    )
    assert result.preview.can_apply
    assert result.preview.period_start is None
    assert result.preview.period_end is None
    assert result.preview.period_status == "unknown"
    assert result.preview.errors == []


def test_non_date_metadata_cells_are_ignored_and_iso_text_allows_surrounding_whitespace():
    result = parse_gsc_pages(
        workbook_file({"Chart": [["Date", "Other"], [" 2026-04-01 ", "=1+1"]]}),
        "synthetic.xlsx",
    )
    assert result.preview.period_start == date(2026, 4, 1)
    assert result.preview.period_end == date(2026, 4, 1)
    assert result.preview.period_status == "exact"


def test_ambiguous_duplicate_date_headers_make_period_unknown():
    result = parse_gsc_pages(
        workbook_file({"Chart": [["Date", "日期"], ["2026-01-01", "2026-01-28"]]}),
        "ambiguous.xlsx",
    )
    assert result.preview.can_apply
    assert result.preview.period_status == "unknown"
    assert result.preview.period_start is None
    assert result.preview.period_end is None


def test_matching_recognized_date_sheets_are_accepted_with_different_order_and_duplicates():
    result = parse_gsc_pages(
        workbook_file(
            {
                "Chart": [["Date"], ["2026-01-01"], ["2026-01-28"]],
                "日期": [["日期"], ["2026-01-28"], ["2026-01-01"], ["2026-01-01"]],
            }
        ),
        "consistent.xlsx",
    )
    assert result.preview.period_start == date(2026, 1, 1)
    assert result.preview.period_end == date(2026, 1, 28)
    assert result.preview.period_status == "exact"


@pytest.mark.parametrize(
    "second_rows",
    [
        [["日期"], ["2026-02-01"], ["2026-02-28"]],
        [["日期"], ["2026-01-01"], ["2026-01-10"], ["2026-01-28"]],
        [["日期"], ["2026-01-01"], ["invalid"]],
        [["Date", "日期"], ["2026-01-01", "2026-01-28"]],
    ],
)
def test_conflicting_or_malformed_recognized_date_sheets_make_period_unknown(second_rows):
    result = parse_gsc_pages(
        workbook_file(
            {
                "Chart": [["Date"], ["2026-01-01"], ["2026-01-28"]],
                "Dates": second_rows,
            }
        ),
        "conflicting.xlsx",
    )
    assert result.preview.can_apply
    assert result.preview.period_start is None
    assert result.preview.period_end is None
    assert result.preview.period_status == "unknown"


@pytest.mark.parametrize("invalid_header", [False, True])
def test_date_metadata_worksheet_scan_is_bounded_even_when_evidence_is_unusable(
    monkeypatch, invalid_header
):
    monkeypatch.setattr("app.imports.gsc.parser.MAX_ROWS", 2)
    header = "Unknown" if invalid_header else "Date"
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(
            workbook_file({"Chart": [[header], ["2026-01-01"], ["2026-01-02"]]}),
            "oversized-metadata.xlsx",
        )
    assert caught.value.code == "too_many_rows"


@pytest.mark.parametrize(
    ("filename", "basename"),
    [
        ("/private/export.xlsx", "export.xlsx"),
        (r"C:\private\export.xlsx", "export.xlsx"),
        (r"/private\mixed/export.xlsx", "export.xlsx"),
        ("simple.xlsx", "simple.xlsx"),
    ],
)
def test_parsed_filename_keeps_basename_without_client_directory_information(filename, basename):
    result = parse_gsc_pages(workbook_file(), filename)
    assert result.filename == basename


def test_public_period_status_is_computed_and_rejects_inconsistent_bounds():
    payload = parse_gsc_pages(workbook_file(), "synthetic.xlsx").preview.model_dump()
    payload.update(
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 28), period_status="unknown"
    )
    assert ImportPreview.model_validate(payload).period_status == "exact"
    payload["period_end"] = None
    with pytest.raises(ValidationError):
        ImportPreview.model_validate(payload)
    payload["period_end"] = date(2025, 12, 31)
    with pytest.raises(ValidationError):
        ImportPreview.model_validate(payload)


def test_existing_reporting_window_validation_still_rejects_conflicting_filters():
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(
            workbook_file(
                {
                    "Chart": [["Date"], ["2026-01-01"], ["2026-01-28"]],
                    "Filters": [["Date", "Last 7 days"]],
                }
            ),
            "wrong-window.xlsx",
        )
    assert caught.value.code == "unsupported_reporting_window"


def test_sparse_observed_dates_with_28_day_endpoints_are_not_complete():
    result = parse_gsc_pages(
        workbook_file({"Chart": [["Date"], ["2026-09-01"], ["2026-09-10"], ["2026-09-28"]]}),
        "sparse.xlsx",
    )
    assert result.preview.period_start == date(2026, 9, 1)
    assert result.preview.period_end == date(2026, 9, 28)
    assert result.preview.observed_date_count == 3
    assert result.preview.dates_consecutive is False
    assert result.preview.coverage_status == "partial"


@pytest.mark.parametrize("count", [1, 7, 27, 29])
def test_consecutive_dates_only_establish_complete_coverage_for_exactly_28_days(count):
    values = [date(2026, 9, 1) + timedelta(days=offset) for offset in range(count)]
    result = parse_gsc_pages(
        workbook_file({"Chart": [["Date"], *[[value] for value in values]]}), "consecutive.xlsx"
    )
    assert result.preview.observed_date_count == count
    assert result.preview.dates_consecutive is True
    assert result.preview.coverage_status == "partial"


def test_duplicate_dates_do_not_inflate_complete_observed_date_count():
    values = [date(2026, 9, 1) + timedelta(days=offset) for offset in range(28)]
    result = parse_gsc_pages(
        workbook_file(
            {
                "Chart": [
                    ["Date"],
                    *[[value] for value in reversed(values)],
                    [values[0]],
                    [values[-1]],
                ]
            }
        ),
        "duplicates.xlsx",
    )
    assert result.preview.observed_date_count == 28
    assert result.preview.dates_consecutive is True
    assert result.preview.coverage_status == "complete"


def test_csv_cannot_supply_observed_coverage_from_page_rows_or_filename():
    result = parse_gsc_pages(
        b"Page,Clicks,Impressions,CTR,Position,Date\n"
        b"https://example.test/page,3,30,0.1,5,2026-09-01\n",
        "complete-2026-09-28.csv",
    )
    assert result.preview.observed_date_count is None
    assert result.preview.dates_consecutive is None
    assert result.preview.coverage_status == "unknown"
