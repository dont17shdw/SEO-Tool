from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.import_run import ImportRun
    from app.models.website_page import WebsitePage


class PagePerformanceSnapshot(Base):
    """Preserve one source row's observations, separate from merged current-page values.
    保存一个来源行的观测值，与合并后的当前页面值相互独立。

    Source blanks and unavailable exact reporting dates remain NULL; no judgments are stored.
    来源空值及无法确定的准确报告日期保持 NULL；不存储判断结论。
    """

    __tablename__ = "page_performance_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "import_run_id", "page_id", name="uq_page_performance_snapshots_import_run_id_page_id"
        ),
        *(
            CheckConstraint(f"{column} >= 0", name=f"{column}_nonnegative")
            for column in ("clicks", "impressions", "average_position")
        ),
        CheckConstraint("ctr >= 0 AND ctr <= 1", name="ctr_fraction"),
        CheckConstraint(
            "(period_start IS NULL AND period_end IS NULL) OR "
            "(period_start IS NOT NULL AND period_end IS NOT NULL AND period_end >= period_start)",
            name="period_dates",
        ),
        Index("ix_page_performance_snapshots_page_period", "page_id", "period_end", "period_start"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    import_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("import_runs.id", ondelete="RESTRICT"), nullable=False
    )
    page_id: Mapped[UUID] = mapped_column(
        ForeignKey("website_pages.id", ondelete="RESTRICT"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    clicks: Mapped[int | None] = mapped_column(BigInteger)
    impressions: Mapped[int | None] = mapped_column(BigInteger)
    ctr: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    average_position: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    import_run: Mapped[ImportRun] = relationship(back_populates="snapshots")
    page: Mapped[WebsitePage] = relationship(back_populates="performance_snapshots")
