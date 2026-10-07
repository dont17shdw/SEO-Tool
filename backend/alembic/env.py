"""Run explicit schema migrations; application startup never creates database tables.
执行显式的数据库结构迁移；应用启动时不会创建数据库表。
"""

from logging.config import fileConfig

from alembic import context

from app import models
from app.config.settings import get_settings
from app.db.session import dispose_engine, get_engine

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# Importing the model package registers both tables with the shared metadata.
# 导入模型包会将两张表注册到共享元数据中。
target_metadata = models.WebsitePage.metadata


def run_migrations_offline() -> None:
    """Render PostgreSQL migration SQL without opening a database connection.
    在不打开数据库连接的情况下生成 PostgreSQL 迁移 SQL。
    """
    context.configure(
        url=str(get_settings().database_url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply versioned schema changes using the same settings as the application.
    使用与应用相同的配置应用版本化数据库结构变更。
    """
    engine = get_engine()
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        dispose_engine()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
