"""Verify bounded custom export labels without inventing source dates or coverage.
验证有明确边界的自定义导出标签，不编造来源日期或覆盖。
"""

from datetime import date, timedelta

import pytest
from test_gsc_period import workbook_file

from app.imports.gsc.parser import ImportFileError, parse_gsc_pages

START = date(2026, 1, 1)
DATES = [[START + timedelta(days=offset)] for offset in range(28)]


def custom_file(label, dates=DATES, *, extra_sheets=None):
    """Build independent synthetic Filters and daily-date evidence.
    生成相互独立的合成筛选及每日日期证据。
    """
    return workbook_file(
        {
            "Chart": [["Date"], *dates],
            "Filters": [["Filter", "Value"], ["Date", label]],
            **(extra_sheets or {}),
        }
    )


@pytest.mark.parametrize(
    "label",
    [
        "2026-01-01 - 2026-01-28",
        "2026-01-01 to 2026-01-28",
        "2026-01-01 TO 2026-01-28",
        "2026-01-01 – 2026-01-28",
        "2026-01-01 — 2026-01-28",
        "2026-01-01 至 2026-01-28",
        "2026年1月1日至2026年1月28日",
        "2026年01月01日到2026年01月28日",
        "Custom: 2026-01-01 - 2026-01-28",
        "CUSTOM DATE RANGE: 2026-01-01 to 2026-01-28",
        "自定义：2026年1月1日至2026年1月28日",
        "自定义日期范围：2026-01-01 至 2026-01-28",
        " 2026-01-01 - 2026-01-28 ",
    ],
)
def test_explicit_english_and_chinese_28_day_ranges_preserve_observed_facts(label):
    preview = parse_gsc_pages(custom_file(label), "synthetic.xlsx").preview
    assert preview.can_apply
    assert preview.reporting_window == "latest_28_days"
    assert preview.period_start == START
    assert preview.period_end == date(2026, 1, 28)
    assert preview.observed_date_count == 28
    assert preview.dates_consecutive is True
    assert preview.coverage_status == "complete"


@pytest.mark.parametrize("label", ["Custom", "custom date range", "自定义", "自定义日期范围"])
def test_bare_custom_labels_require_independently_complete_observations(label):
    assert (
        parse_gsc_pages(custom_file(label), "synthetic.xlsx").preview.coverage_status == "complete"
    )
    for dates in ([], DATES[:27], DATES + [[date(2026, 1, 29)]], [DATES[0], DATES[-1]]):
        with pytest.raises(ImportFileError) as caught:
            parse_gsc_pages(custom_file(label, dates), "synthetic.xlsx")
        assert caught.value.code == "unsupported_reporting_window"


@pytest.mark.parametrize(
    "label",
    [
        "2026-01-01 to 2026-01-27",
        "2026-01-01 to 2026-01-29",
        "2026-01-28 to 2026-01-01",
        "2026-02-30 to 2026-03-29",
        "2026年2月30日至2026年3月29日",
        "01/01/2026 - 01/28/2026",
        "2026/01/01 - 2026/01/28",
        "2026-1-1 to 2026-1-28",
        "2026-01-01T00:00:00 to 2026-01-28T00:00:00",
        "Date: 2026-01-01 to 2026-01-28",
        "2026-01-01 to 2026-01-28 trailing",
        "Last 7 days",
        "过去 3 个月",
        '=CONCAT("2026-01-01", " to ", "2026-01-28")',
    ],
)
def test_unsupported_non28_invalid_ambiguous_or_formula_labels_stay_rejected(label):
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(custom_file(label), "synthetic.xlsx")
    assert caught.value.code == "unsupported_reporting_window"


@pytest.mark.parametrize(
    ("dates", "count", "consecutive"),
    [
        ([DATES[0], DATES[9], DATES[-1]], 3, False),
        (DATES[1:-1], 26, True),
        ([DATES[0]] * 28, 1, True),
    ],
)
def test_explicit_range_does_not_complete_sparse_internal_or_duplicate_dates(
    dates, count, consecutive
):
    preview = parse_gsc_pages(custom_file("2026-01-01 to 2026-01-28", dates), "sparse.xlsx").preview
    assert preview.coverage_status == "partial"
    assert preview.observed_date_count == count
    assert preview.dates_consecutive is consecutive
    assert preview.period_start == dates[0][0]
    assert preview.period_end == dates[-1][0]


@pytest.mark.parametrize("dates", [[], [["invalid"]], [DATES[0], [None, 1]]])
def test_explicit_range_never_populates_absent_or_invalid_observed_dates(dates):
    preview = parse_gsc_pages(
        custom_file("2026-01-01 to 2026-01-28", dates), "unknown.xlsx"
    ).preview
    assert preview.can_apply
    assert preview.period_start is preview.period_end is None
    assert preview.observed_date_count is preview.dates_consecutive is None
    assert preview.coverage_status == "unknown"


@pytest.mark.parametrize("outside", [date(2025, 12, 31), date(2026, 1, 29)])
def test_explicit_range_rejects_observed_dates_outside_declared_bounds(outside):
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(
            custom_file("2026-01-01 to 2026-01-28", DATES + [[outside]]), "outside.xlsx"
        )
    assert caught.value.code == "conflicting_reporting_dates"


def test_explicit_range_does_not_resolve_conflicting_daily_worksheets():
    preview = parse_gsc_pages(
        custom_file(
            "2026-01-01 to 2026-01-28",
            extra_sheets={"日期": [["日期"], ["2026-01-01"], ["2026-01-28"]]},
        ),
        "conflicting-daily-evidence.xlsx",
    ).preview
    assert preview.can_apply
    assert preview.period_start is preview.period_end is None
    assert preview.observed_date_count is preview.dates_consecutive is None
    assert preview.coverage_status == "unknown"


def test_multiple_filter_sheets_must_not_declare_different_custom_ranges():
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(
            custom_file(
                "2026-01-01 to 2026-01-28",
                extra_sheets={"过滤器": [["日期", "2026年1月29日至2026年2月25日"]]},
            ),
            "conflicting.xlsx",
        )
    assert caught.value.code == "conflicting_reporting_dates"


def test_equivalent_labels_can_repeat_across_sheets_without_changing_evidence():
    preview = parse_gsc_pages(
        custom_file(
            "2026-01-01 to 2026-01-28",
            extra_sheets={"过滤器": [["日期", "2026年1月1日至2026年1月28日"]]},
        ),
        "consistent.xlsx",
    ).preview
    assert preview.coverage_status == "complete"


@pytest.mark.parametrize("label", ["Last 28 days", "过去 28 天", None, ""])
def test_latest_blank_and_absent_date_metadata_keep_existing_unknown_behavior(label):
    preview = parse_gsc_pages(custom_file(label, []), "unknown.xlsx").preview
    assert preview.can_apply
    assert preview.reporting_window == "latest_28_days"
    assert preview.period_start is preview.period_end is None
    assert preview.coverage_status == "unknown"


def test_custom_filter_physical_row_limit_remains_enforced(monkeypatch):
    monkeypatch.setattr("app.imports.gsc.parser.MAX_ROWS", 2)
    with pytest.raises(ImportFileError) as caught:
        parse_gsc_pages(
            workbook_file(
                {"Filters": [["Date", "Custom"], ["Date", "Custom"], ["Date", "Custom"]]}
            ),
            "large.xlsx",
        )
    assert caught.value.code == "too_many_rows"
