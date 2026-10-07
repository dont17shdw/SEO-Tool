from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PageMetricProvenance(Base):
    """Link one current GSC metric to the snapshot that explicitly supplied its value.
    将一个当前 GSC 指标关联到明确提供其值的快照。

    Absence means no recorded source; legacy values are never backfilled by value matching.
    缺少记录表示没有已记录来源；绝不通过值匹配回填历史值来源。
    """

    __tablename__ = "page_metric_provenance"
    __table_args__ = (
        CheckConstraint(
            "metric_name IN ('clicks_28d', 'impressions_28d', 'ctr', 'average_position')",
            name="supported_metric",
        ),
    )

    page_id: Mapped[UUID] = mapped_column(
        ForeignKey("website_pages.id", ondelete="RESTRICT"), primary_key=True
    )
    metric_name: Mapped[str] = mapped_column(String(30), primary_key=True)
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("page_performance_snapshots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
