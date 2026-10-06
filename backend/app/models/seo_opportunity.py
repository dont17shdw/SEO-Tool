from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.website_page import WebsitePage


class SEOOpportunity(Base):
    """Store a future recommendation and its evidence without calculating scores here.
    存储未来的推荐及其依据，不在此处计算评分。

    Classification strings remain open; no SEO rules or execution behavior are defined.
    分类字符串保持开放；此处不定义 SEO 规则或执行行为。
    """

    __tablename__ = "seo_opportunities"
    __table_args__ = (
        CheckConstraint("opportunity_score >= 0", name="opportunity_score_nonnegative"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_fraction"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    page_id: Mapped[UUID] = mapped_column(
        ForeignKey("website_pages.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    opportunity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(30))
    opportunity_score: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expected_impact: Mapped[str | None] = mapped_column(Text)
    estimated_effort: Mapped[str | None] = mapped_column(Text)
    risk_level: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(
        String(30), server_default=text("'pending'"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    page: Mapped[WebsitePage] = relationship(back_populates="opportunities")
