from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.page_performance_snapshot import PagePerformanceSnapshot


class ImportRun(Base):
    """Record a completed import; failed imports leave no persistent history.
    记录已完成的导入；失败的导入不会留下持久化历史。

    The SHA-256 fingerprint identifies source bytes, independently of the filename.
    SHA-256 指纹用于识别来源字节，不依赖文件名。
    """

    __tablename__ = "import_runs"
    __table_args__ = (
        UniqueConstraint(
            "source", "source_type", "file_hash", name="uq_import_runs_source_source_type_file_hash"
        ),
        CheckConstraint("file_hash ~ '^[0-9a-f]{64}$'", name="file_hash_sha256"),
        *(
            CheckConstraint(f"{column} >= 0", name=f"{column}_nonnegative")
            for column in ("total_rows", "created_count", "updated_count", "skipped_count")
        ),
        CheckConstraint(
            "created_count + updated_count + skipped_count = total_rows", name="counts_sum"
        ),
        CheckConstraint(
            "(period_start IS NULL AND period_end IS NULL) OR "
            "(period_start IS NOT NULL AND period_end IS NOT NULL AND period_end >= period_start)",
            name="period_dates",
        ),
        Index("ix_import_runs_period", "period_start", "period_end"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(30), server_default=text("'gsc'"), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50), server_default=text("'pages_performance'"), nullable=False
    )
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    reporting_window: Mapped[str] = mapped_column(
        String(30), server_default=text("'latest_28_days'"), nullable=False
    )
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    created_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    updated_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), server_default=text("'completed'"), nullable=False
    )

    snapshots: Mapped[list[PagePerformanceSnapshot]] = relationship(
        back_populates="import_run", passive_deletes="all"
    )
