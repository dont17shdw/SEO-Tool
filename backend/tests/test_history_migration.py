"""Verify history migration against existing Phase 2 data in an isolated PostgreSQL schema.
在隔离的 PostgreSQL 模式中，针对现有第二阶段数据验证历史迁移。
"""

import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


def test_history_migration_preserves_existing_pages_and_opportunities():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL migration verification")
    if make_url(database_url).drivername != "postgresql+psycopg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+psycopg://")
    schema_name = f"phase3_migration_{uuid4().hex}"
    engine = create_engine(database_url, connect_args={"options": "-c timezone=UTC"})
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema_name}"')
        with engine.connect() as connection:
            connection.exec_driver_sql(f'SET search_path TO "{schema_name}"')
            connection.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            command.upgrade(config, "0001_initial_schema")
            page_id, opportunity_id = uuid4(), uuid4()
            connection.execute(
                text(
                    "INSERT INTO website_pages "
                    "(id, url, title, clicks_28d, impressions_28d, ctr, indexed, backlinks) "
                    "VALUES (:id, 'https://example.com/retained', 'Synthetic retained title', "
                    "17, 340, 0.05, true, 3)"
                ),
                {"id": page_id},
            )
            connection.execute(
                text(
                    "INSERT INTO seo_opportunities "
                    "(id, page_id, opportunity_type, recommended_action, reason) "
                    "VALUES (:id, :page_id, 'synthetic', 'Synthetic placeholder', "
                    "'Migration preservation fixture')"
                ),
                {"id": opportunity_id, "page_id": page_id},
            )
            connection.commit()
            original_page = connection.execute(text("SELECT * FROM website_pages")).mappings().one()
            original_opportunity = (
                connection.execute(text("SELECT * FROM seo_opportunities")).mappings().one()
            )
            connection.commit()

            command.upgrade(config, "0002_import_history")
            assert {"import_runs", "page_performance_snapshots"} <= set(
                inspect(connection).get_table_names()
            )
            assert connection.execute(text("SELECT * FROM website_pages")).mappings().one() == (
                original_page
            )
            assert connection.execute(text("SELECT * FROM seo_opportunities")).mappings().one() == (
                original_opportunity
            )
            assert connection.scalar(text("SELECT count(*) FROM import_runs")) == 0
            assert connection.scalar(text("SELECT count(*) FROM page_performance_snapshots")) == 0
            connection.commit()

            # Downgrade only empty new tables; legacy data must survive both directions.
            # 仅回退空的新表；旧数据必须在两个迁移方向均保持不变。
            command.downgrade(config, "0001_initial_schema")
            assert "import_runs" not in inspect(connection).get_table_names()
            assert connection.execute(text("SELECT * FROM website_pages")).mappings().one() == (
                original_page
            )
            assert connection.execute(text("SELECT * FROM seo_opportunities")).mappings().one() == (
                original_opportunity
            )
            connection.commit()
            command.upgrade(config, "0002_import_history")
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
        engine.dispose()
