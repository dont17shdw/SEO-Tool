"""Opt-in PostgreSQL tests use a disposable schema, never the application's public tables.
可选的 PostgreSQL 测试使用临时模式，不会使用应用的 public 表。
"""

import os
from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import SEOOpportunity, WebsitePage

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="Set TEST_DATABASE_URL to opt in to live PostgreSQL tests"
)


@pytest.fixture(scope="module")
def postgres_engine():
    """Isolate tables in a unique schema and remove only that schema after testing.
    将表隔离在唯一的模式中，并在测试结束后仅删除该模式。
    """
    if make_url(TEST_DATABASE_URL).drivername != "postgresql+psycopg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+psycopg://")
    schema_name = f"phase1_test_{uuid4().hex}"
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"options": "-c timezone=UTC"},
        execution_options={"schema_translate_map": {None: schema_name}},
    )
    with engine.begin() as connection:
        connection.exec_driver_sql(f'CREATE SCHEMA "{schema_name}"')
    try:
        Base.metadata.create_all(engine)
        yield engine
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA "{schema_name}" CASCADE')
        engine.dispose()


@pytest.fixture
def session(postgres_engine):
    with Session(postgres_engine) as database_session:
        yield database_session


def new_page(**metrics) -> WebsitePage:
    return WebsitePage(url=f"https://example.com/{uuid4().hex}", **metrics)


def new_opportunity(page_id: UUID, **fields) -> SEOOpportunity:
    return SEOOpportunity(
        page_id=page_id,
        opportunity_type="test_candidate",
        recommended_action="Review the supplied data",
        reason="Persistence verification",
        **fields,
    )


def test_postgresql_round_trip_preserves_unknown_zero_decimal_and_defaults(session):
    page = new_page(clicks_7d=0, ctr=Decimal("0.123456"))
    session.add(page)
    session.commit()
    session.refresh(page)
    assert isinstance(page.id, UUID)
    assert page.clicks_7d == 0
    assert page.clicks_28d is None
    assert page.indexed is None
    assert page.ctr == Decimal("0.123456")
    assert page.created_at.utcoffset() == timedelta(0)
    assert page.updated_at.utcoffset() == timedelta(0)

    opportunity = new_opportunity(page.id, confidence=Decimal("0.75"))
    session.add(opportunity)
    session.commit()
    session.refresh(opportunity)
    assert opportunity.status == "pending"
    assert opportunity.opportunity_score is None
    assert opportunity.confidence == Decimal("0.75")
    assert opportunity.page.id == page.id


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("clicks_7d", -1),
        ("word_count", -1),
        ("business_value", Decimal("-0.001")),
        ("average_position", Decimal("-1")),
        ("ctr", Decimal("1.000001")),
        ("ctr", Decimal("-0.000001")),
    ],
)
def test_postgresql_rejects_invalid_page_metric_ranges(session, field, value):
    session.add(new_page(**{field: value}))
    with pytest.raises(IntegrityError) as error:
        session.flush()
    assert error.value.orig.sqlstate == "23514"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("confidence", Decimal("-0.000001")),
        ("confidence", Decimal("1.000001")),
        ("opportunity_score", Decimal("-1")),
    ],
)
def test_postgresql_rejects_invalid_opportunity_metric_ranges(session, field, value):
    page = new_page()
    session.add(page)
    session.flush()
    session.add(new_opportunity(page.id, **{field: value}))
    with pytest.raises(IntegrityError) as error:
        session.flush()
    assert error.value.orig.sqlstate == "23514"


def test_postgresql_rejects_duplicate_page_urls(session):
    page = new_page()
    session.add(page)
    session.flush()
    session.add(WebsitePage(url=page.url))
    with pytest.raises(IntegrityError) as error:
        session.flush()
    assert error.value.orig.sqlstate == "23505"


def test_postgresql_rejects_orphan_opportunities(session):
    session.add(new_opportunity(uuid4()))
    with pytest.raises(IntegrityError) as error:
        session.flush()
    assert error.value.orig.sqlstate == "23503"


def test_deleting_a_page_does_not_silently_delete_loaded_opportunities(session):
    page = new_page()
    session.add(page)
    session.flush()
    opportunity = new_opportunity(page.id)
    session.add(opportunity)
    session.commit()
    assert page.opportunities == [opportunity]
    session.delete(page)
    with pytest.raises(IntegrityError) as error:
        session.flush()
    assert error.value.orig.sqlstate == "23503"


def test_orm_update_advances_updated_at_without_changing_content_timestamp(session):
    page = new_page()
    session.add(page)
    session.commit()
    session.refresh(page)
    original_updated_at = page.updated_at
    original_created_at = page.created_at
    session.commit()

    page.title = "Updated title"
    session.commit()
    session.refresh(page)
    assert page.updated_at > original_updated_at
    assert page.created_at == original_created_at
    assert page.last_updated is None
