import pytest

from app.config.settings import get_settings
from app.db.session import dispose_engine


@pytest.fixture
def isolated_settings(monkeypatch):
    """Keep API tests independent of a developer's environment and PostgreSQL service.
    使 API 测试独立于开发者的环境配置和 PostgreSQL 服务。
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@127.0.0.1:1/test")
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')
    dispose_engine()
    get_settings.cache_clear()
    yield
    dispose_engine()
    get_settings.cache_clear()
