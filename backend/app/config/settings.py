from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load database and browser access settings from the environment.
    从环境中加载数据库和浏览器访问配置。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: PostgresDsn = Field(
        default="postgresql+psycopg://seo_tool:seo_tool_dev@localhost:5432/seo_tool",
        repr=False,
    )
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @field_validator("database_url")
    @classmethod
    def require_psycopg(cls, value: PostgresDsn) -> PostgresDsn:
        """Keep runtime and migrations on the configured PostgreSQL driver.
        确保运行时和迁移使用指定的 PostgreSQL 驱动。
        """
        if value.scheme != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use postgresql+psycopg://")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        """Accept browser origins rather than arbitrary URLs or wildcard access.
        接受浏览器来源，而非任意 URL 或通配符访问。
        """
        for value in values:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS_ORIGINS must contain HTTP(S) origins without paths")
        return [value.rstrip("/") for value in values]


@lru_cache
def get_settings() -> Settings:
    return Settings()
