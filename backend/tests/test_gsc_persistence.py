from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from gsc_helpers import csv_file
from gsc_helpers import gsc_engine as postgres_import_engine  # noqa: F401
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.imports.gsc.parser import parse_gsc_pages
from app.imports.gsc.persistence import persist_gsc_pages
from app.models import WebsitePage


def test_import_creates_records_and_keeps_unknown_fields_null(gsc_engine):
    parsed = parse_gsc_pages(
        csv_file(["https://example.com/new/", 0, 100, "2.5%", "6.75"]), "pages.csv"
    )
    with Session(gsc_engine) as session:
        result = persist_gsc_pages(session, parsed)
        assert (result.created_count, result.updated_count, result.error_count) == (1, 0, 0)
        page = session.scalars(select(WebsitePage)).one()
        assert page.url == "https://example.com/new/"
        assert page.clicks_28d == 0
        assert page.impressions_28d == 100
        assert page.ctr == Decimal("0.025")
        assert page.average_position == Decimal("6.75")
        for field in (
            "clicks_7d",
            "clicks_previous_28d",
            "impressions_7d",
            "impressions_previous_28d",
            "page_type",
            "title",
            "primary_keyword",
            "backlinks",
            "indexed",
            "business_value",
        ):
            assert getattr(page, field) is None


def test_import_updates_supplied_metrics_without_erasing_blank_or_unrelated_fields(gsc_engine):
    with Session(gsc_engine) as session:
        page = WebsitePage(
            url="https://example.com/existing",
            clicks_28d=2,
            impressions_28d=250,
            ctr=Decimal("0.012345"),
            average_position=Decimal("8"),
            clicks_7d=1,
            clicks_previous_28d=9,
            impressions_7d=70,
            impressions_previous_28d=600,
            title="Existing title",
            page_type="product",
            primary_keyword="sample product",
            backlinks=5,
            indexed=True,
            word_count=123,
            business_value=Decimal("100"),
        )
        session.add(page)
        session.commit()
        original_id = page.id
        original_created_at = page.created_at
        session.commit()
        parsed = parse_gsc_pages(csv_file([page.url, 10, "", "", "3.5"]), "pages.csv")
        session.commit()
        result = persist_gsc_pages(session, parsed)
        session.refresh(page)
        assert (result.created_count, result.updated_count, result.skipped_count) == (0, 1, 0)
        assert page.id == original_id
        assert page.created_at == original_created_at
        assert page.clicks_28d == 10
        assert page.average_position == Decimal("3.5")
        assert page.impressions_28d == 250
        assert page.ctr == Decimal("0.012345")
        assert page.clicks_7d == 1
        assert page.clicks_previous_28d == 9
        assert page.impressions_7d == 70
        assert page.impressions_previous_28d == 600
        assert page.title == "Existing title"
        assert page.page_type == "product"
        assert page.primary_keyword == "sample product"
        assert page.backlinks == 5
        assert page.indexed is True
        assert page.word_count == 123
        assert page.business_value == Decimal("100")


def test_reimport_unchanged_or_blank_metrics_is_skipped(gsc_engine):
    content = csv_file(["https://example.com/page", 10, 100, "10%", "5"])
    parsed = parse_gsc_pages(content, "pages.csv")
    with Session(gsc_engine) as session:
        assert persist_gsc_pages(session, parsed).created_count == 1
        page = session.scalars(select(WebsitePage)).one()
        original_updated_at = page.updated_at
        session.commit()
        assert persist_gsc_pages(session, parsed).skipped_count == 1
        session.refresh(page)
        assert page.updated_at == original_updated_at
        session.commit()
        blank_parsed = parse_gsc_pages(csv_file([page.url, "", "", "", ""]), "pages.csv")
        session.commit()
        assert persist_gsc_pages(session, blank_parsed).skipped_count == 1
        session.refresh(page)
        assert page.clicks_28d == 10
        assert page.updated_at == original_updated_at


def test_later_database_failure_rolls_back_creates_and_updates(gsc_engine, monkeypatch):
    with Session(gsc_engine) as session:
        existing = WebsitePage(url="https://example.com/a-existing", clicks_28d=1)
        session.add(existing)
        session.commit()
        parsed = parse_gsc_pages(
            csv_file(
                [existing.url, 10, 100, "10%", "5"],
                ["https://example.com/b-new", 20, 200, "10%", "5"],
                ["https://example.com/c-fails", 30, 300, "10%", "5"],
            ),
            "pages.csv",
        )
        session.commit()
        original_execute = session.execute
        calls = 0

        def fail_later(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 4:
                raise SQLAlchemyError("synthetic private database failure")
            return original_execute(*args, **kwargs)

        monkeypatch.setattr(session, "execute", fail_later)
        with pytest.raises(SQLAlchemyError):
            persist_gsc_pages(session, parsed)

    with Session(gsc_engine) as verification:
        saved = verification.scalars(select(WebsitePage)).all()
        assert len(saved) == 1
        assert saved[0].clicks_28d == 1


def test_concurrent_same_url_imports_create_exactly_one_record(gsc_engine):
    content = csv_file(["https://example.com/concurrent", 10, 100, "10%", 5])
    files = [
        parse_gsc_pages(content, "first.csv"),
        parse_gsc_pages(b"\n" + content, "second.csv"),
    ]

    def import_once(parsed):
        with Session(gsc_engine) as session:
            return persist_gsc_pages(session, parsed)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(import_once, files))
    assert sum(result.created_count for result in results) == 1
    assert sum(result.skipped_count for result in results) == 1
    with Session(gsc_engine) as session:
        assert session.scalar(select(func.count()).select_from(WebsitePage)) == 1
