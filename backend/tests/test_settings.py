import pytest
from pydantic import ValidationError

from app.config.settings import Settings


def test_settings_load_json_origins_and_database_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:password@localhost:5432/test")
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000/", "https://seo.example"]')
    settings = Settings(_env_file=None)
    assert str(settings.database_url) == "postgresql+psycopg://user:password@localhost:5432/test"
    assert settings.cors_origins == ["http://localhost:3000", "https://seo.example"]
    assert "password" not in repr(settings)


@pytest.mark.parametrize("database_url", ["sqlite:///:memory:", "postgresql://user:pass@host/db"])
def test_settings_require_postgresql_and_the_psycopg_driver(database_url):
    with pytest.raises(ValidationError):
        Settings(database_url=database_url, _env_file=None)


@pytest.mark.parametrize(
    "origin", ["*", "https://example.com/path", "https://user:pass@example.com"]
)
def test_settings_reject_wildcard_paths_and_credentials_in_origins(origin):
    with pytest.raises(ValidationError):
        Settings(cors_origins=[origin], _env_file=None)
