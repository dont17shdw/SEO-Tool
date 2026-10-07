import io
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from gsc_helpers import csv_file
from gsc_helpers import gsc_engine as postgres_import_engine  # noqa: F401
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.main import create_app
from app.models import ImportRun, PagePerformanceSnapshot, WebsitePage

PREVIEW_PATH = "/api/v1/imports/gsc/pages/preview"
APPLY_PATH = "/api/v1/imports/gsc/pages/apply"


@pytest.fixture
def history_client(gsc_engine, isolated_settings):
    application = create_app()

    def override_session():
        with Session(gsc_engine) as session:
            yield session

    application.dependency_overrides[get_session] = override_session
    with TestClient(application) as client:
        yield client


def xlsx_file(start: date, clicks=20, impressions=500, ctr="2.5%", position="8") -> bytes:
    workbook = Workbook()
    pages = workbook.active
    pages.title = "Pages"
    pages.append(["Page", "Clicks", "Impressions", "CTR", "Position"])
    pages.append(["https://example.com/page", clicks, impressions, ctr, position])
    dates = workbook.create_sheet("Dates")
    dates.append(["Date", "Clicks", "Impressions", "CTR", "Position"])
    for day in range(28):
        dates.append([start + timedelta(days=day), 1, 10, "10%", 5])
    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()


def apply_file(client, content: bytes, filename="pages.csv"):
    files = {"file": (filename, content, "application/octet-stream")}
    preview = client.post(PREVIEW_PATH, files=files)
    assert preview.status_code == 200
    response = client.post(
        APPLY_PATH,
        files=files,
        data={"confirmed": "true", "preview_hash": preview.json()["preview_hash"]},
    )
    assert response.status_code == 200
    return response.json()


def test_import_history_pagination_and_stable_newest_first_order(history_client, gsc_engine):
    results = [
        apply_file(history_client, csv_file(["https://example.com/page", number, 100, "1%", 5]))
        for number in range(1, 4)
    ]
    # Deliberately tie timestamps to exercise the documented UUID ordering.
    # 故意设置相同时间戳，以验证文档约定的 UUID 排序。
    with Session(gsc_engine) as session:
        for item in session.scalars(select(ImportRun)):
            item.imported_at = datetime(2026, 1, 1, tzinfo=UTC)
        session.commit()
    expected = sorted([result["import_run_id"] for result in results], reverse=True)
    first = history_client.get("/api/v1/imports?page=1&page_size=2").json()
    second = history_client.get("/api/v1/imports?page=2&page_size=2").json()
    assert first["page"] == 1
    assert first["page_size"] == 2
    assert first["total"] == 3
    assert first["total_pages"] == 2
    assert [item["id"] for item in first["items"]] == expected[:2]
    assert [item["id"] for item in second["items"]] == expected[2:]
    item = first["items"][0]
    assert item["source"] == "gsc"
    assert item["source_type"] == "pages_performance"
    assert item["reporting_window"] == "latest_28_days"
    assert item["period_status"] == "unknown"
    assert item["period_start"] is item["period_end"] is None
    assert item["status"] == "completed"
    assert item["total_rows"] == 1
    assert len(item["file_hash"]) == 64
    assert history_client.get("/api/v1/imports?page=3&page_size=2").json()["items"] == []


def test_page_history_chronology_and_comparison_are_independent_of_pagination(history_client):
    newer_period = apply_file(
        history_client, xlsx_file(date(2026, 2, 1), 30, 300, "4%", "4"), "newer.xlsx"
    )
    older_period = apply_file(
        history_client, xlsx_file(date(2026, 1, 1), 20, 500, "2.5%", "8"), "older.xlsx"
    )
    page_id = history_client.get("/api/v1/pages").json()["items"][0]["id"]
    endpoint = f"/api/v1/pages/{page_id}/performance"
    first = history_client.get(endpoint + "?page=1&page_size=1").json()
    second = history_client.get(endpoint + "?page=2&page_size=1").json()
    assert first["total"] == first["total_pages"] == 2
    assert first["items"][0]["import_run_id"] == newer_period["import_run_id"]
    assert second["items"][0]["import_run_id"] == older_period["import_run_id"]
    assert first["current_page"]["clicks_28d"] == 20
    assert first["items"][0]["period_status"] == "exact"
    assert first["items"][0]["source"] == "gsc"
    assert first["items"][0]["source_type"] == "pages_performance"
    comparison = first["comparison"]
    assert comparison == second["comparison"]
    assert comparison["previous_period_start"] == "2026-01-01"
    assert comparison["current_period_start"] == "2026-02-01"
    assert comparison["previous_snapshot_id"] == second["items"][0]["id"]
    assert comparison["current_snapshot_id"] == first["items"][0]["id"]
    assert comparison["clicks"] == {"absolute_change": 10, "percentage_change": "50.000000"}
    assert comparison["impressions"] == {
        "absolute_change": -200,
        "percentage_change": "-40.000000",
    }
    assert comparison["ctr_percentage_point_change"] == "1.500000"
    assert comparison["average_position_change"] == "-4.0000"
    assert comparison["periods_overlap"] is False
    assert first["comparison_unavailable_reason"] is None
    beyond_end = history_client.get(endpoint + "?page=3&page_size=1").json()
    assert beyond_end["items"] == []
    assert beyond_end["comparison"] == comparison


def test_snapshot_missing_values_are_not_filled_from_current_page(history_client):
    apply_file(history_client, csv_file(["https://example.com/page", 20, 500, "2.5%", 8]))
    apply_file(history_client, csv_file(["https://example.com/page", "", "", "", ""]))
    page_id = history_client.get("/api/v1/pages").json()["items"][0]["id"]
    history = history_client.get(f"/api/v1/pages/{page_id}/performance").json()
    assert history["current_page"]["clicks_28d"] == 20
    last = history["items"][-1]
    assert last["clicks"] is last["impressions"] is last["ctr"] is last["average_position"] is None
    assert last["period_status"] == "unknown"
    assert last["period_start"] is last["period_end"] is None
    assert history["comparison"] is None
    assert history["comparison_unavailable_reason"]


def test_repeat_old_file_does_not_revert_later_page_state_or_create_history(history_client):
    old_file = csv_file(["https://example.com/page", 10, 100, "10%", 5])
    original = apply_file(history_client, old_file, "original.csv")
    apply_file(history_client, csv_file(["https://example.com/page", 30, 300, "10%", 4]))
    repeated = apply_file(history_client, old_file, "renamed.csv")
    assert repeated["already_processed"] is True
    assert repeated["import_run_id"] == original["import_run_id"]
    assert repeated["created_count"] == repeated["updated_count"] == 0
    pages = history_client.get("/api/v1/pages").json()
    assert pages["items"][0]["clicks_28d"] == 30
    page_id = pages["items"][0]["id"]
    assert history_client.get("/api/v1/imports").json()["total"] == 2
    assert history_client.get(f"/api/v1/pages/{page_id}/performance").json()["total"] == 2


def test_same_period_revisions_use_latest_import_but_keep_each_snapshot(history_client):
    apply_file(history_client, xlsx_file(date(2026, 1, 1), clicks=10), "first.xlsx")
    apply_file(history_client, xlsx_file(date(2026, 2, 1), clicks=30), "next.xlsx")
    apply_file(history_client, xlsx_file(date(2026, 1, 1), clicks=15), "revision.xlsx")
    page_id = history_client.get("/api/v1/pages").json()["items"][0]["id"]
    history = history_client.get(f"/api/v1/pages/{page_id}/performance").json()
    assert history["total"] == 3
    assert history["comparison"]["previous_snapshot_id"] == history["items"][2]["id"]
    assert history["comparison"]["clicks"]["absolute_change"] == 15


def test_history_only_returns_snapshots_for_requested_page(history_client):
    apply_file(
        history_client,
        csv_file(
            ["https://example.com/a", 1, 10, "10%", 5],
            ["https://example.com/b", 2, 20, "10%", 5],
        ),
    )
    pages = history_client.get("/api/v1/pages").json()["items"]
    for page in pages:
        history = history_client.get(f"/api/v1/pages/{page['id']}/performance").json()
        assert history["total"] == 1
        assert history["items"][0]["page_id"] == page["id"]
        assert history["items"][0]["url"] == page["url"]


def test_empty_history_existing_page_without_snapshots_and_missing_page(history_client, gsc_engine):
    assert history_client.get("/api/v1/imports").json() == {
        "items": [],
        "page": 1,
        "page_size": 50,
        "total": 0,
        "total_pages": 0,
    }
    missing = history_client.get(f"/api/v1/pages/{uuid4()}/performance")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "page_not_found"
    with Session(gsc_engine) as session:
        identifier = uuid4()
        session.add(WebsitePage(id=identifier, url="https://example.com/legacy"))
        session.commit()
    empty = history_client.get(f"/api/v1/pages/{identifier}/performance").json()
    assert empty["items"] == []
    assert empty["total"] == empty["total_pages"] == 0
    assert empty["comparison"] is None


@pytest.mark.parametrize("query", ["page=0", "page_size=0", "page_size=101"])
def test_history_pagination_bounds(history_client, query):
    assert history_client.get(f"/api/v1/imports?{query}").status_code == 422
    assert history_client.get(f"/api/v1/pages/{UUID(int=1)}/performance?{query}").status_code == 422


@pytest.mark.parametrize(
    "endpoint", ["/api/v1/imports", f"/api/v1/pages/{UUID(int=1)}/performance"]
)
def test_history_database_failure_has_generic_error(isolated_settings, endpoint):
    application = create_app()

    class UnavailableSession:
        def get(self, *args, **kwargs):
            raise SQLAlchemyError("private connection hostname")

        def scalar(self, *args, **kwargs):
            raise SQLAlchemyError("private connection hostname")

    application.dependency_overrides[get_session] = lambda: UnavailableSession()
    with TestClient(application) as client:
        response = client.get(endpoint)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "database_unavailable"
    assert "private connection hostname" not in response.text


def test_history_failure_after_page_lookup_has_generic_error(
    history_client, gsc_engine, monkeypatch
):
    with Session(gsc_engine) as session:
        page_id = uuid4()
        session.add(WebsitePage(id=page_id, url="https://example.com/page"))
        session.commit()

    def fail_history_query(*args, **kwargs):
        raise SQLAlchemyError("private snapshot SQL")

    monkeypatch.setattr(Session, "execute", fail_history_query)
    response = history_client.get(f"/api/v1/pages/{page_id}/performance")
    assert response.status_code == 503
    assert "private snapshot SQL" not in response.text


def test_preview_still_creates_no_import_or_snapshots(history_client, gsc_engine):
    content = xlsx_file(date(2026, 1, 1))
    response = history_client.post(
        PREVIEW_PATH, files={"file": ("pages.xlsx", content, "application/octet-stream")}
    )
    assert response.status_code == 200
    assert response.json()["period_start"] == "2026-01-01"
    assert response.json()["period_end"] == "2026-01-28"
    assert response.json()["period_status"] == "exact"
    with Session(gsc_engine) as session:
        assert session.scalars(select(ImportRun)).all() == []
        assert session.scalars(select(PagePerformanceSnapshot)).all() == []
        assert session.scalars(select(WebsitePage)).all() == []
