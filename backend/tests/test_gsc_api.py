from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from gsc_helpers import csv_file
from gsc_helpers import gsc_engine as postgres_import_engine  # noqa: F401
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.main import create_app
from app.models import WebsitePage

PREVIEW_PATH = "/api/v1/imports/gsc/pages/preview"
APPLY_PATH = "/api/v1/imports/gsc/pages/apply"


def upload(content: bytes, filename: str = "pages.csv"):
    return {"file": (filename, content, "application/octet-stream")}


@pytest.fixture
def api_client(gsc_engine, isolated_settings):
    application = create_app()

    def override_session():
        with Session(gsc_engine) as session:
            yield session

    application.dependency_overrides[get_session] = override_session
    with TestClient(application) as client:
        yield client


def test_preview_is_database_independent_and_returns_normalized_sample(
    isolated_settings, monkeypatch
):
    def unavailable_engine(*args, **kwargs):
        raise AssertionError("Preview must not create a database engine")

    monkeypatch.setattr("app.db.session.create_engine", unavailable_engine)
    application = create_app()
    application.dependency_overrides[get_session] = unavailable_engine
    with TestClient(application) as client:
        response = client.post(
            PREVIEW_PATH,
            files=upload(csv_file(["https://example.com/page", 0, 100, "2.5%", 5])),
        )
    assert response.status_code == 200
    preview = response.json()
    assert preview["source"] == "gsc_pages"
    assert preview["reporting_window"] == "latest_28_days"
    assert preview["total_rows"] == preview["valid_rows"] == 1
    assert preview["can_apply"] is True
    assert len(preview["preview_hash"]) == 64
    assert preview["sample_rows"][0]["ctr"] == "0.025000"


@pytest.mark.parametrize(
    ("content", "filename", "expected_status"),
    [(b"", "pages.csv", 422), (b"invalid", "pages.pdf", 422), (b"not xlsx", "pages.xlsx", 422)],
)
def test_structural_upload_errors_are_useful(isolated_settings, content, filename, expected_status):
    with TestClient(create_app()) as client:
        response = client.post(PREVIEW_PATH, files=upload(content, filename))
    assert response.status_code == expected_status
    assert response.json()["detail"]["code"]
    assert response.json()["detail"]["message"]


def test_file_size_limit_is_enforced(isolated_settings):
    with TestClient(create_app()) as client:
        response = client.post(PREVIEW_PATH, files=upload(b"x" * (5 * 1024 * 1024 + 1)))
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "file_too_large"


@pytest.mark.parametrize("mode", ["unconfirmed", "changed", "invalid", "duplicate"])
def test_rejected_apply_does_not_resolve_database_dependency(isolated_settings, mode):
    application = create_app()

    def unavailable_session():
        raise AssertionError("A rejected apply must not resolve the database dependency")

    application.dependency_overrides[get_session] = unavailable_session
    rows = [["https://example.com/page", 10, 100, "10%", 5]]
    if mode == "invalid":
        rows[0][1] = -1
    if mode == "duplicate":
        rows.append(rows[0])
    content = csv_file(*rows)
    with TestClient(application) as client:
        preview = client.post(PREVIEW_PATH, files=upload(content)).json()
        response = client.post(
            APPLY_PATH,
            files=upload(content if mode != "changed" else content + b"\n"),
            data={
                "confirmed": "false" if mode == "unconfirmed" else "true",
                "preview_hash": preview["preview_hash"],
            },
        )
    assert response.status_code == (409 if mode == "changed" else 422)


def test_preview_does_not_persist_then_confirmed_apply_creates_and_reimport_skips(api_client):
    content = csv_file(["https://example.com/page", 10, 100, "10%", 5])
    preview = api_client.post(PREVIEW_PATH, files=upload(content)).json()
    assert api_client.get("/api/v1/pages").json()["total"] == 0
    data = {"confirmed": "true", "preview_hash": preview["preview_hash"]}
    response = api_client.post(APPLY_PATH, files=upload(content), data=data)
    assert response.status_code == 200
    assert response.json() == {
        "created_count": 1,
        "updated_count": 0,
        "skipped_count": 0,
        "error_count": 0,
    }
    repeated = api_client.post(APPLY_PATH, files=upload(content), data=data)
    assert repeated.json()["skipped_count"] == 1
    pages = api_client.get("/api/v1/pages").json()
    assert pages["total"] == 1
    assert pages["items"][0]["clicks_28d"] == 10
    assert pages["items"][0]["ctr"] == "0.100000"


def test_confirmed_apply_updates_existing_page_and_preserves_unknown_import_values(
    api_client, gsc_engine
):
    with Session(gsc_engine) as session:
        session.add(
            WebsitePage(
                url="https://example.com/existing",
                title="Retained title",
                clicks_28d=1,
                impressions_28d=100,
                clicks_7d=4,
            )
        )
        session.commit()
    content = csv_file(["https://example.com/existing", 20, "", "", ""])
    preview = api_client.post(PREVIEW_PATH, files=upload(content)).json()
    response = api_client.post(
        APPLY_PATH,
        files=upload(content),
        data={"confirmed": "true", "preview_hash": preview["preview_hash"]},
    )
    assert response.status_code == 200
    assert response.json()["updated_count"] == 1
    with Session(gsc_engine) as session:
        page = session.scalars(select(WebsitePage)).one()
        assert page.clicks_28d == 20
        assert page.impressions_28d == 100
        assert page.clicks_7d == 4
        assert page.title == "Retained title"


def test_database_failure_response_is_generic_and_transaction_rolls_back(
    api_client, gsc_engine, monkeypatch
):
    content = csv_file(
        ["https://example.com/a", 1, 10, "10%", 5],
        ["https://example.com/b", 2, 20, "10%", 5],
    )
    preview = api_client.post(PREVIEW_PATH, files=upload(content)).json()
    original_execute = Session.execute
    calls = 0

    def fail_second_insert(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise SQLAlchemyError("private hostname and stack trace must not leak")
        return original_execute(self, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Session, "execute", fail_second_insert)
        response = api_client.post(
            APPLY_PATH,
            files=upload(content),
            data={"confirmed": "true", "preview_hash": preview["preview_hash"]},
        )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "database_unavailable"
    assert "private hostname" not in response.text
    with Session(gsc_engine) as verification:
        assert verification.scalars(select(WebsitePage)).all() == []


def test_paginated_listing_has_stable_order_and_metadata(api_client, gsc_engine):
    same_time = datetime(2026, 1, 1, tzinfo=UTC)
    with Session(gsc_engine) as session:
        session.add_all(
            WebsitePage(
                id=UUID(int=number),
                url=f"https://example.com/{number}",
                clicks_28d=number,
                created_at=same_time,
            )
            for number in (3, 1, 2)
        )
        session.commit()
    first = api_client.get("/api/v1/pages?page=1&page_size=2").json()
    second = api_client.get("/api/v1/pages?page=2&page_size=2").json()
    assert first["page"] == 1
    assert first["page_size"] == 2
    assert first["total"] == 3
    assert first["total_pages"] == 2
    assert [item["clicks_28d"] for item in first["items"]] == [1, 2]
    assert [item["clicks_28d"] for item in second["items"]] == [3]
    assert api_client.get("/api/v1/pages?page=3&page_size=2").json()["items"] == []


def test_empty_list_and_pagination_bounds(api_client):
    assert api_client.get("/api/v1/pages").json() == {
        "items": [],
        "page": 1,
        "page_size": 50,
        "total": 0,
        "total_pages": 0,
    }
    assert api_client.get("/api/v1/pages?page=0").status_code == 422
    assert api_client.get("/api/v1/pages?page_size=101").status_code == 422
    assert api_client.get("/api/v1/pages?page_size=0").status_code == 422
