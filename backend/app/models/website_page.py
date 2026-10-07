from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.seo_opportunity import SEOOpportunity


class WebsitePage(Base):
    """Store page identity and optional observed metrics, without deriving SEO judgments.
    存储页面标识及可选的观测指标，不在模型中推导 SEO 判断。

    NULL means unknown; zero means an observed zero. CTR is stored as a 0–1 fraction.
    NULL 表示未知；零表示观测值为零。CTR 以 0–1 的比例存储。
    """

    __tablename__ = "website_pages"
    __table_args__ = (
        UniqueConstraint("url"),
        *(
            CheckConstraint(f"{column} >= 0", name=f"{column}_nonnegative")
            for column in (
                "clicks_7d",
                "clicks_28d",
                "clicks_previous_28d",
                "impressions_7d",
                "impressions_28d",
                "impressions_previous_28d",
                "average_position",
                "word_count",
                "internal_links_in",
                "internal_links_out",
                "backlinks",
                "business_value",
            )
        ),
        CheckConstraint("ctr >= 0 AND ctr <= 1", name="ctr_fraction"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    page_type: Mapped[str | None] = mapped_column(String(50))
    title: Mapped[str | None] = mapped_column(Text)
    primary_keyword: Mapped[str | None] = mapped_column(Text)
    clicks_7d: Mapped[int | None] = mapped_column(BigInteger)
    clicks_28d: Mapped[int | None] = mapped_column(BigInteger)
    clicks_previous_28d: Mapped[int | None] = mapped_column(BigInteger)
    impressions_7d: Mapped[int | None] = mapped_column(BigInteger)
    impressions_28d: Mapped[int | None] = mapped_column(BigInteger)
    impressions_previous_28d: Mapped[int | None] = mapped_column(BigInteger)
    ctr: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    average_position: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    indexed: Mapped[bool | None] = mapped_column(Boolean)
    index_status: Mapped[str | None] = mapped_column(String(50))
    word_count: Mapped[int | None] = mapped_column(Integer)
    internal_links_in: Mapped[int | None] = mapped_column(Integer)
    internal_links_out: Mapped[int | None] = mapped_column(Integer)
    backlinks: Mapped[int | None] = mapped_column(Integer)
    business_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Retain opportunities unless they are explicitly removed before deleting a page.
    # 保留机会记录，删除页面前需要显式删除关联的机会记录。
    opportunities: Mapped[list[SEOOpportunity]] = relationship(
        back_populates="page", passive_deletes="all"
    )
