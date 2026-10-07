"""Verify Phase 6 facts, safe identity changes, and all five legacy tables in PostgreSQL.
在 PostgreSQL 中验证第六阶段事实、安全身份变更及全部五个旧表。
"""

import os
from datetime import date
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from test_provenance_migration import METRICS, seed_phase4_rows

from app.db.base import Base
from app.normalization.report_scope import UNKNOWN_SCOPE_FINGERPRINT

LEGACY_REVISION = "0003_current_metric_provenance"
SCOPE_REVISION = "0004_report_scope"
LEGACY_TABLES = (
    "website_pages",
    "import_runs",
    "page_performance_snapshots",
    "page_metric_provenance",
    "seo_opportunities",
)


@pytest.fixture
def scope_migration_connection():
    """Run migrations only in a disposable schema, without application public tables.
    仅在临时模式中运行迁移，不使用应用 public 表。
    """
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL migration verification")
    if make_url(database_url).drivername != "postgresql+psycopg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+psycopg://")
    schema_name = f"phase6_migration_{uuid4().hex}"
    engine = create_engine(database_url, connect_args={"options": "-c timezone=UTC"})
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema_name}"')
        with engine.connect() as connection:
            connection.exec_driver_sql(f'SET search_path TO "{schema_name}"')
            connection.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            yield connection, config
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
        engine.dispose()


def capture_rows(connection, columns):
    """Compare every old value, including timestamps and existing source links.
    比较每个旧值，包括时间戳及已有来源关联。
    """
    return {
        name: [
            dict(row)
            for row in connection.execute(
                text(
                    f"SELECT {', '.join(fields)} FROM {name} ORDER BY "
                    + ("page_id, metric_name" if name == "page_metric_provenance" else "id")
                )
            ).mappings()
        ]
        for name, fields in columns.items()
    }


@pytest.fixture
def legacy_scope_data(scope_migration_connection):
    connection, config = scope_migration_connection
    command.upgrade(config, "0002_import_history")
    identifiers = seed_phase4_rows(connection)
    command.upgrade(config, LEGACY_REVISION)
    rows = [
        {
            "page_id": identifiers["page_id"],
            "metric_name": metric,
            "snapshot_id": identifiers["snapshot_id"],
        }
        for metric in METRICS
    ] + [
        {
            "page_id": identifiers["second_page_id"],
            "metric_name": "clicks_28d",
            "snapshot_id": identifiers["second_snapshot_id"],
        }
    ]
    table = Table("page_metric_provenance", MetaData(), autoload_with=connection)
    connection.execute(table.insert(), rows)
    columns = {
        name: [column["name"] for column in inspect(connection).get_columns(name)]
        for name in LEGACY_TABLES
    }
    original = capture_rows(connection, columns)
    connection.commit()
    return connection, config, columns, original


def test_scope_upgrade_downgrade_preserves_every_legacy_value_and_link(legacy_scope_data):
    connection, config, columns, original = legacy_scope_data
    command.upgrade(config, "head")
    assert connection.scalar(text("SELECT version_num FROM alembic_version")) == SCOPE_REVISION
    assert capture_rows(connection, columns) == original
    assert connection.scalar(text("SELECT count(*) FROM sites")) == 0
    assert connection.scalar(text("SELECT count(*) FROM page_metric_provenance")) == 5
    assert all(
        row.site_id is None for row in connection.execute(text("SELECT site_id FROM website_pages"))
    )
    for row in connection.execute(
        text(
            "SELECT site_id, report_scope, scope_fingerprint, observed_date_count, "
            "dates_consecutive, coverage_status FROM import_runs"
        )
    ).mappings():
        assert dict(row) == {
            "site_id": None,
            "report_scope": None,
            "scope_fingerprint": UNKNOWN_SCOPE_FINGERPRINT,
            "observed_date_count": None,
            "dates_consecutive": None,
            "coverage_status": "unknown",
        }
    connection.commit()
    command.check(config)

    command.downgrade(config, LEGACY_REVISION)
    assert capture_rows(connection, columns) == original
    assert set(inspect(connection).get_table_names()) == set(LEGACY_TABLES) | {"alembic_version"}
    connection.commit()
    command.upgrade(config, "head")
    assert capture_rows(connection, columns) == original
    assert connection.scalar(text("SELECT count(*) FROM sites")) == 0
    assert connection.scalar(text("SELECT count(*) FROM page_metric_provenance")) == 5
    connection.commit()
    command.check(config)


@pytest.fixture
def scope_head(scope_migration_connection):
    connection, config = scope_migration_connection
    command.upgrade(config, "head")
    return connection, config


def insert_site(connection, identifier):
    site_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO sites (id, identifier, display_name) "
            "VALUES (:id, :identifier, :identifier)"
        ),
        {"id": site_id, "identifier": identifier},
    )
    return site_id


def insert_page(connection, url, site_id=None):
    page_id = uuid4()
    connection.execute(
        text("INSERT INTO website_pages (id, url, site_id) VALUES (:id, :url, :site_id)"),
        {"id": page_id, "url": url, "site_id": site_id},
    )
    return page_id


def insert_run(connection, **fields):
    fields = {
        "id": uuid4(),
        "file_hash": uuid4().hex * 2,
        "filename": "synthetic.csv",
        "total_rows": 0,
    } | fields
    table = Table("import_runs", MetaData(), autoload_with=connection)
    connection.execute(table.insert(), fields)
    return fields["id"]


def test_fresh_scope_schema_matches_metadata(scope_head):
    connection, config = scope_head
    inspector = inspect(connection)
    assert set(inspector.get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
    assert {column["name"] for column in inspector.get_columns("sites")} == {
        "id",
        "identifier",
        "display_name",
        "created_at",
    }
    assert all(not column["nullable"] for column in inspector.get_columns("sites"))
    for table in ("website_pages", "import_runs"):
        assert any(
            key["constrained_columns"] == ["site_id"]
            and key["referred_table"] == "sites"
            and key["options"].get("ondelete") == "RESTRICT"
            for key in inspector.get_foreign_keys(table)
        )
    unique = next(
        constraint
        for constraint in inspector.get_unique_constraints("website_pages")
        if constraint["column_names"] == ["site_id", "url"]
    )
    assert unique["dialect_options"]["postgresql_nulls_not_distinct"] is True
    assert any(
        constraint["column_names"] == ["source", "source_type", "file_hash", "scope_fingerprint"]
        for constraint in inspector.get_unique_constraints("import_runs")
    )
    connection.commit()
    command.check(config)


def test_page_identity_separates_sites_and_preserves_unknown_namespace(scope_head):
    connection, _ = scope_head
    first = insert_site(connection, "sc-domain:example.com")
    second = insert_site(connection, "https://example.com/")
    url = "https://example.com/synthetic-shared-url"
    for site_id in (None, first, second):
        insert_page(connection, url, site_id)
    for site_id in (None, first, second):
        with pytest.raises(IntegrityError) as error, connection.begin_nested():
            insert_page(connection, url, site_id)
        assert error.value.orig.sqlstate == "23505"
    assert connection.scalar(text("SELECT count(*) FROM website_pages")) == 3


def test_import_identity_preserves_same_file_under_distinct_scopes(scope_head):
    connection, _ = scope_head
    file_hash = "a" * 64
    for fingerprint in (UNKNOWN_SCOPE_FINGERPRINT, "b" * 64, "c" * 64):
        insert_run(connection, file_hash=file_hash, scope_fingerprint=fingerprint)
        with pytest.raises(IntegrityError) as error, connection.begin_nested():
            insert_run(connection, file_hash=file_hash, scope_fingerprint=fingerprint)
        assert error.value.orig.sqlstate == "23505"
    assert connection.scalar(text("SELECT count(*) FROM import_runs")) == 3


@pytest.mark.parametrize("collision", ["pages", "imports"])
def test_downgrade_refuses_scope_collisions_without_changing_rows(scope_head, collision):
    connection, config = scope_head
    if collision == "pages":
        first = insert_site(connection, "sc-domain:example.com")
        second = insert_site(connection, "https://example.com/")
        for site_id in (first, second):
            insert_page(connection, "https://example.com/scoped", site_id)
    else:
        insert_run(connection, file_hash="d" * 64, scope_fingerprint="e" * 64)
        insert_run(connection, file_hash="d" * 64, scope_fingerprint="f" * 64)
    columns = {
        name: [column["name"] for column in inspect(connection).get_columns(name)]
        for name in (*LEGACY_TABLES, "sites")
    }
    original = capture_rows(connection, columns)
    connection.commit()
    with pytest.raises(RuntimeError, match="Cannot downgrade Phase 6"):
        command.downgrade(config, LEGACY_REVISION)
    assert connection.scalar(text("SELECT version_num FROM alembic_version")) == SCOPE_REVISION
    assert capture_rows(connection, columns) == original
    assert set(inspect(connection).get_table_names()) == set(columns) | {"alembic_version"}
    connection.commit()
    command.check(config)


@pytest.mark.parametrize(
    "facts",
    [
        {},
        {"period_start": date(2025, 2, 1), "period_end": date(2025, 2, 28)},
        {"observed_date_count": 28, "dates_consecutive": True, "coverage_status": "complete"},
        {"observed_date_count": 3, "dates_consecutive": False, "coverage_status": "partial"},
        {
            "observed_date_count": 26,
            "dates_consecutive": True,
            "coverage_status": "partial",
            "period_end": date(2025, 2, 26),
        },
    ],
)
def test_coverage_constraints_accept_only_coherent_facts(scope_head, facts):
    connection, _ = scope_head
    insert_run(
        connection,
        **({"period_start": date(2025, 2, 1), "period_end": date(2025, 2, 28)} | facts),
    )


@pytest.mark.parametrize(
    "facts",
    [
        {"observed_date_count": 0},
        {"observed_date_count": 29},
        {"observed_date_count": None},
        {"dates_consecutive": None},
        {"dates_consecutive": False},
        {"period_start": None, "period_end": None},
        {"observed_date_count": 3, "dates_consecutive": False},
        {"coverage_status": "partial"},
        {"coverage_status": "unknown"},
        {"coverage_status": "invented"},
    ],
)
def test_coverage_constraints_reject_false_complete_or_unknown_facts(scope_head, facts):
    connection, _ = scope_head
    values = {
        "period_start": date(2025, 2, 1),
        "period_end": date(2025, 2, 28),
        "observed_date_count": 28,
        "dates_consecutive": True,
        "coverage_status": "complete",
    } | facts
    with pytest.raises(IntegrityError) as error, connection.begin_nested():
        insert_run(connection, **values)
    assert error.value.orig.sqlstate == "23514"


@pytest.mark.parametrize(
    "fields", [{"scope_fingerprint": "not-a-fingerprint"}, {"report_scope": []}]
)
def test_scope_constraints_reject_invalid_shape_and_hash(scope_head, fields):
    connection, _ = scope_head
    with pytest.raises(IntegrityError) as error, connection.begin_nested():
        insert_run(connection, **fields)
    assert error.value.orig.sqlstate == "23514"


@pytest.mark.parametrize("table", ["website_pages", "import_runs"])
def test_referenced_site_deletion_is_restricted(scope_head, table):
    connection, _ = scope_head
    site_id = insert_site(connection, "sc-domain:example.com")
    if table == "website_pages":
        insert_page(connection, "https://example.com/scoped", site_id)
    else:
        insert_run(connection, site_id=site_id)
    with pytest.raises(IntegrityError) as error, connection.begin_nested():
        connection.execute(text("DELETE FROM sites WHERE id = :id"), {"id": site_id})
    assert error.value.orig.sqlstate == "23503"
