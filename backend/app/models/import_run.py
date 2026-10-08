from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.normalization.report_scope import UNKNOWN_SCOPE_FINGERPRINT

if TYPE_CHECKING:
    from app.models.page_performance_snapshot import PagePerformanceSnapshot


class ImportRun(Base):
    """Record a completed import; failed imports leave no persistent history.
    记录已完成的导入；失败的导入不会留下持久化历史。

    File bytes and canonical scope jointly identify an import; the scope excludes dates.
    文件字节及规范范围共同标识一次导入；范围不包含日期。
    """

    __tablename__ = "import_runs"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_type",
            "file_hash",
            "scope_fingerprint",
            name="uq_import_runs_source_type_file_scope",
        ),
        CheckConstraint("file_hash ~ '^[0-9a-f]{64}$'", name="file_hash_sha256"),
        CheckConstraint("scope_fingerprint ~ '^[0-9a-f]{64}$'", name="scope_fingerprint_sha256"),
        CheckConstraint(
            "report_scope IS NULL OR jsonb_typeof(report_scope) = 'object'",
            name="report_scope_object",
        ),
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
        CheckConstraint(
            "(coverage_status = 'unknown' AND observed_date_count IS NULL "
            "AND dates_consecutive IS NULL) OR "
            "(coverage_status IN ('complete', 'partial') "
            "AND period_start IS NOT NULL AND period_end IS NOT NULL "
            "AND observed_date_count IS NOT NULL AND observed_date_count > 0 "
            "AND observed_date_count <= period_end - period_start + 1 "
            "AND dates_consecutive IS NOT NULL "
            "AND dates_consecutive = (observed_date_count = period_end - period_start + 1) "
            "AND (coverage_status = 'complete') = "
            "(observed_date_count = 28 AND dates_consecutive "
            "AND period_end - period_start + 1 = 28))",
            name="date_coverage",
        ),
        Index("ix_import_runs_period", "period_start", "period_end"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    site_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("sites.id", ondelete="RESTRICT"), index=True
    )
    source: Mapped[str] = mapped_column(String(30), server_default=text("'gsc'"), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50), server_default=text("'pages_performance'"), nullable=False
    )
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # NULL preserves legacy uncertainty; the fingerprint encodes canonical unknown scope.
    # NULL 保留旧数据的不确定性；指纹编码规范的未知范围。
    report_scope: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    scope_fingerprint: Mapped[str] = mapped_column(
        String(64),
        default=UNKNOWN_SCOPE_FINGERPRINT,
        server_default=text(f"'{UNKNOWN_SCOPE_FINGERPRINT}'"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    reporting_window: Mapped[str] = mapped_column(
        String(30), server_default=text("'latest_28_days'"), nullable=False
    )
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    observed_date_count: Mapped[int | None] = mapped_column(Integer)
    dates_consecutive: Mapped[bool | None] = mapped_column(Boolean)
    coverage_status: Mapped[str] = mapped_column(
        String(10), server_default=text("'unknown'"), nullable=False
    )
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
