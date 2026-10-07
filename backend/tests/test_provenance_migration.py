"""Verify Phase 5 schema integrity and legacy preservation in disposable PostgreSQL schemas.
在临时 PostgreSQL 模式中验证第五阶段数据库结构完整性及旧数据保留。
"""

import os
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

LEGACY_TABLES = (
    "website_pages",
    "import_runs",
    "page_performance_snapshots",
    "seo_opportunities",
)
METRICS = ("clicks_28d", "impressions_28d", "ctr", "average_position")
PROVENANCE_TABLE = "page_metric_provenance"


@pytest.fixture
def migration_connection():
    """Supply Alembic a connection whose search path excludes application public tables.
    为 Alembic 提供搜索路径不包含应用 public 表的连接。
    """
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL migration verification")
    if make_url(database_url).drivername != "postgresql+psycopg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+psycopg://")
    schema_name = f"phase5_migration_{uuid4().hex}"
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


def seed_phase4_rows(connection):
    """Populate every old column, including NULLs, zeros, and distinct historical timestamps.
    填充每个旧字段，包括 NULL、零及不同的历史时间戳。

    Matching current and snapshot values deliberately provide no evidence of their source.
    有意让当前值与快照值匹配；相等的值不构成来源证据。
    """
    page_id, second_page_id = uuid4(), uuid4()
    run_id, second_run_id = uuid4(), uuid4()
    snapshot_id, second_snapshot_id = uuid4(), uuid4()
    page = {
        "id": page_id,
        "url": "https://example.com/legacy-provenance",
        "page_type": "synthetic",
        "title": "Synthetic retained title / 合成保留标题",
        "primary_keyword": "synthetic fixture",
        "clicks_7d": 4,
        "clicks_28d": 17,
        "clicks_previous_28d": 11,
        "impressions_7d": 80,
        "impressions_28d": 340,
        "impressions_previous_28d": 220,
        "ctr": Decimal("0.050000"),
        "average_position": Decimal("8.2500"),
        "indexed": True,
        "index_status": "synthetic retained status",
        "word_count": 1200,
        "internal_links_in": 6,
        "internal_links_out": 8,
        "backlinks": 3,
        "business_value": Decimal("12.3456"),
        "last_updated": datetime(2025, 1, 3, 10, 11, 12, 123456, UTC),
        "created_at": datetime(2025, 1, 4, 9, 8, 7, 234567, UTC),
        "updated_at": datetime(2025, 3, 1, 4, 5, 6, 345678, UTC),
    }
    second_page = {
        field: None
        for field in page
        if field not in {"id", "url", "created_at", "updated_at", "clicks_28d"}
    } | {
        "id": second_page_id,
        "url": "https://example.com/legacy-zero-and-unknown",
        "clicks_28d": 0,
        "created_at": datetime(2025, 1, 5, 0, 0, 0, 456789, UTC),
        "updated_at": datetime(2025, 3, 2, 0, 0, 0, 567890, UTC),
    }
    run = {
        "id": run_id,
        "source": "gsc",
        "source_type": "pages_performance",
        "file_hash": "a" * 64,
        "filename": "synthetic-legacy.xlsx",
        "reporting_window": "latest_28_days",
        "period_start": date(2025, 2, 1),
        "period_end": date(2025, 2, 28),
        "imported_at": datetime(2025, 3, 1, 4, 5, 6, 678901, UTC),
        "total_rows": 1,
        "created_count": 0,
        "updated_count": 1,
        "skipped_count": 0,
        "status": "completed",
    }
    second_run = run | {
        "id": second_run_id,
        "file_hash": "b" * 64,
        "filename": "synthetic-unknown.csv",
        "period_start": None,
        "period_end": None,
        "imported_at": datetime(2025, 3, 2, 4, 5, 6, 789012, UTC),
        "updated_count": 0,
        "skipped_count": 1,
    }
    snapshot = {
        "id": snapshot_id,
        "import_run_id": run_id,
        "page_id": page_id,
        "url": page["url"],
        "clicks": page["clicks_28d"],
        "impressions": page["impressions_28d"],
        "ctr": page["ctr"],
        "average_position": page["average_position"],
        "period_start": run["period_start"],
        "period_end": run["period_end"],
        "created_at": datetime(2025, 3, 1, 4, 5, 7, 890123, UTC),
    }
    second_snapshot = snapshot | {
        "id": second_snapshot_id,
        "import_run_id": second_run_id,
        "page_id": second_page_id,
        "url": second_page["url"],
        "clicks": 0,
        "impressions": None,
        "ctr": None,
        "average_position": None,
        "period_start": None,
        "period_end": None,
        "created_at": datetime(2025, 3, 2, 4, 5, 7, 901234, UTC),
    }
    opportunity = {
        "id": uuid4(),
        "page_id": page_id,
        "opportunity_type": "synthetic retained fixture",
        "severity": "synthetic",
        "opportunity_score": Decimal("2.3456"),
        "confidence": Decimal("0.750000"),
        "recommended_action": "Synthetic placeholder / 合成占位内容",
        "reason": "Migration preservation fixture / 迁移保留测试数据",
        "expected_impact": "Synthetic retained impact",
        "estimated_effort": "Synthetic retained effort",
        "risk_level": "synthetic",
        "status": "pending",
        "created_at": datetime(2025, 1, 6, 7, 8, 9, 123456, UTC),
    }
    second_opportunity = opportunity | {
        "id": uuid4(),
        "page_id": second_page_id,
        "severity": None,
        "opportunity_score": None,
        "confidence": None,
        "expected_impact": None,
        "estimated_effort": None,
        "risk_level": None,
    }
    rows_by_table = {
        "website_pages": [page, second_page],
        "import_runs": [run, second_run],
        "page_performance_snapshots": [snapshot, second_snapshot],
        "seo_opportunities": [opportunity, second_opportunity],
    }
    for name, rows in rows_by_table.items():
        table = Table(name, MetaData(), autoload_with=connection)
        assert all(set(row) == set(table.columns.keys()) for row in rows)
        connection.execute(table.insert(), rows)
    connection.commit()
    return {
        "page_id": page_id,
        "second_page_id": second_page_id,
        "snapshot_id": snapshot_id,
        "second_snapshot_id": second_snapshot_id,
    }


def legacy_rows(connection):
    """Capture every value and timestamp, without relying on current ORM defaults.
    捕获每个值与时间戳，不依赖当前 ORM 默认值。
    """
    return {
        name: [
            dict(row)
            for row in connection.execute(text(f"SELECT * FROM {name} ORDER BY id")).mappings()
        ]
        for name in LEGACY_TABLES
    }


@pytest.fixture
def populated_head(migration_connection):
    connection, config = migration_connection
    command.upgrade(config, "0002_import_history")
    identifiers = seed_phase4_rows(connection)
    command.upgrade(config, "0003_current_metric_provenance")
    return connection, identifiers


def insert_provenance(connection, **fields):
    connection.execute(
        text(
            "INSERT INTO page_metric_provenance (page_id, metric_name, snapshot_id) "
            "VALUES (:page_id, :metric_name, :snapshot_id)"
        ),
        fields,
    )


def test_provenance_upgrade_downgrade_preserves_every_legacy_row(migration_connection):
    connection, config = migration_connection
    command.upgrade(config, "0002_import_history")
    identifiers = seed_phase4_rows(connection)
    original_rows = legacy_rows(connection)
    original_tables = set(inspect(connection).get_table_names())
    connection.commit()

    command.upgrade(config, "0003_current_metric_provenance")
    assert set(inspect(connection).get_table_names()) == original_tables | {PROVENANCE_TABLE}
    assert legacy_rows(connection) == original_rows
    assert connection.scalar(text("SELECT count(*) FROM page_metric_provenance")) == 0
    assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
        "0003_current_metric_provenance"
    )
    connection.commit()

    for metric in METRICS:
        insert_provenance(
            connection,
            page_id=identifiers["page_id"],
            metric_name=metric,
            snapshot_id=identifiers["snapshot_id"],
        )
    connection.commit()

    # Only source links are discarded on downgrade; all old values remain exact.
    # 降级仅丢弃来源关联；所有旧值仍保持完全相同。
    command.downgrade(config, "0002_import_history")
    assert set(inspect(connection).get_table_names()) == original_tables
    assert legacy_rows(connection) == original_rows
    assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
        "0002_import_history"
    )
    connection.commit()

    command.upgrade(config, "0003_current_metric_provenance")
    assert legacy_rows(connection) == original_rows
    assert connection.scalar(text("SELECT count(*) FROM page_metric_provenance")) == 0
    connection.commit()


def test_fresh_provenance_schema_matches_metadata(migration_connection):
    connection, config = migration_connection
    command.upgrade(config, "head")
    inspector = inspect(connection)
    assert set(inspector.get_table_names()) == set(LEGACY_TABLES) | {
        PROVENANCE_TABLE,
        "alembic_version",
        "sites",
    }
    columns = inspector.get_columns(PROVENANCE_TABLE)
    assert {column["name"] for column in columns} == {"page_id", "metric_name", "snapshot_id"}
    assert all(not column["nullable"] for column in columns)
    assert inspector.get_pk_constraint(PROVENANCE_TABLE)["constrained_columns"] == [
        "page_id",
        "metric_name",
    ]
    foreign_keys = inspector.get_foreign_keys(PROVENANCE_TABLE)
    assert {
        (
            tuple(key["constrained_columns"]),
            key["referred_table"],
            tuple(key["referred_columns"]),
            key["options"].get("ondelete"),
        )
        for key in foreign_keys
    } == {
        (("page_id",), "website_pages", ("id",), "RESTRICT"),
        (("snapshot_id",), "page_performance_snapshots", ("id",), "RESTRICT"),
    }
    assert any(
        index["column_names"] == ["snapshot_id"]
        for index in inspector.get_indexes(PROVENANCE_TABLE)
    )
    assert connection.scalar(text("SELECT count(*) FROM page_metric_provenance")) == 0
    connection.commit()
    command.check(config)


def test_migrated_schema_accepts_all_four_metrics_and_one_source_per_page(populated_head):
    connection, identifiers = populated_head
    for metric in METRICS:
        insert_provenance(
            connection,
            page_id=identifiers["page_id"],
            metric_name=metric,
            snapshot_id=identifiers["snapshot_id"],
        )
    insert_provenance(
        connection,
        page_id=identifiers["second_page_id"],
        metric_name="clicks_28d",
        snapshot_id=identifiers["second_snapshot_id"],
    )
    assert connection.scalar(text("SELECT count(*) FROM page_metric_provenance")) == 5
    with pytest.raises(IntegrityError) as error, connection.begin_nested():
        insert_provenance(
            connection,
            page_id=identifiers["page_id"],
            metric_name="clicks_28d",
            snapshot_id=identifiers["second_snapshot_id"],
        )
    assert error.value.orig.sqlstate == "23505"


@pytest.mark.parametrize("metric_name", ["clicks", "impressions", "title", "CTR", ""])
def test_migrated_schema_rejects_unsupported_metric_names(populated_head, metric_name):
    connection, identifiers = populated_head
    with pytest.raises(IntegrityError) as error, connection.begin_nested():
        insert_provenance(
            connection,
            page_id=identifiers["page_id"],
            metric_name=metric_name,
            snapshot_id=identifiers["snapshot_id"],
        )
    assert error.value.orig.sqlstate == "23514"


@pytest.mark.parametrize("field", ["page_id", "snapshot_id"])
def test_migrated_schema_rejects_missing_references(populated_head, field):
    connection, identifiers = populated_head
    fields = {
        "page_id": identifiers["page_id"],
        "metric_name": "clicks_28d",
        "snapshot_id": identifiers["snapshot_id"],
    }
    fields[field] = uuid4()
    with pytest.raises(IntegrityError) as error, connection.begin_nested():
        insert_provenance(connection, **fields)
    assert error.value.orig.sqlstate == "23503"


@pytest.mark.parametrize("field", ["page_id", "metric_name", "snapshot_id"])
def test_migrated_schema_rejects_null_source_fields(populated_head, field):
    connection, identifiers = populated_head
    fields = {
        "page_id": identifiers["page_id"],
        "metric_name": "clicks_28d",
        "snapshot_id": identifiers["snapshot_id"],
    }
    fields[field] = None
    with pytest.raises(IntegrityError) as error, connection.begin_nested():
        insert_provenance(connection, **fields)
    assert error.value.orig.sqlstate == "23502"


def test_migrated_schema_restricts_deletion_of_referenced_snapshot(populated_head):
    connection, identifiers = populated_head
    insert_provenance(
        connection,
        page_id=identifiers["page_id"],
        metric_name="clicks_28d",
        snapshot_id=identifiers["snapshot_id"],
    )
    with pytest.raises(IntegrityError) as error, connection.begin_nested():
        connection.execute(
            text("DELETE FROM page_performance_snapshots WHERE id = :id"),
            {"id": identifiers["snapshot_id"]},
        )
    assert error.value.orig.sqlstate == "23503"
    # PostgreSQL identifier limits may shorten generated names; inspect the actual snapshot FK.
    # PostgreSQL 标识符长度限制可能缩短生成名称；检查实际的快照外键。
    snapshot_fk = next(
        constraint["name"]
        for constraint in inspect(connection).get_foreign_keys(PROVENANCE_TABLE)
        if constraint["referred_table"] == "page_performance_snapshots"
    )
    assert error.value.orig.diag.constraint_name == snapshot_fk


def test_migrated_schema_page_fk_restricts_even_without_other_dependents(populated_head):
    connection, identifiers = populated_head
    page_id = uuid4()
    connection.execute(
        text("INSERT INTO website_pages (id, url) VALUES (:id, :url)"),
        {"id": page_id, "url": "https://example.com/provenance-fk-only"},
    )
    # Cross-page consistency belongs to the application; SQL FKs enforce existence only.
    # 跨页面一致性由应用校验；SQL 外键仅确保引用存在。
    insert_provenance(
        connection,
        page_id=page_id,
        metric_name="clicks_28d",
        snapshot_id=identifiers["snapshot_id"],
    )
    with pytest.raises(IntegrityError) as error, connection.begin_nested():
        connection.execute(text("DELETE FROM website_pages WHERE id = :id"), {"id": page_id})
    assert error.value.orig.sqlstate == "23503"
    assert error.value.orig.diag.constraint_name == (
        "fk_page_metric_provenance_page_id_website_pages"
    )
