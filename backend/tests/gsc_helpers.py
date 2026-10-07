"""Build synthetic GSC data and isolate PostgreSQL tests in disposable schemas.
生成合成 GSC 数据，并将 PostgreSQL 测试隔离在临时模式中。
"""

import csv
import io
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.db.base import Base
from app.models import SEOOpportunity, WebsitePage  # noqa: F401


def csv_file(*rows: list[str | int]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["Page", "Clicks", "Impressions", "CTR", "Position"])
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


@pytest.fixture(name="gsc_engine")
def gsc_engine():
    """Never read or change a developer's existing application tables.
    不读取或更改开发者现有的应用表。
    """
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL import integration tests")
    if make_url(database_url).drivername != "postgresql+psycopg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+psycopg://")
    schema_name = f"phase2_test_{uuid4().hex}"
    engine = create_engine(
        database_url,
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
