from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.config.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    """Create the connection pool on demand, without opening a startup connection.
    按需创建连接池，不在启动时打开数据库连接。
    """
    return create_engine(
        str(get_settings().database_url),
        pool_pre_ping=True,
        connect_args={"options": "-c timezone=UTC"},
    )


def get_session() -> Generator[Session, None, None]:
    """Provide a request-scoped session; the service owns explicit transactions.
    提供请求范围的会话；由服务显式管理事务。
    """
    with Session(get_engine()) as session:
        yield session


def dispose_engine() -> None:
    """Release only an existing pool, preserving database-independent liveness.
    仅释放已存在的连接池，保持健康检查独立于数据库。
    """
    if get_engine.cache_info().currsize:
        get_engine().dispose()
        get_engine.cache_clear()
