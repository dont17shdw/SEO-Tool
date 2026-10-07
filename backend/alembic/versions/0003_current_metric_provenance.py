"""Track the explicit snapshot source of current GSC metrics without legacy backfill.
追踪当前 GSC 指标的明确快照来源，不回填历史值来源。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_current_metric_provenance"
down_revision: str | Sequence[str] | None = "0002_import_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create an empty provenance table, preserving every pre-existing record and value.
    创建空的来源追踪表，保留所有已有记录及其值。
    """
    op.create_table(
        "page_metric_provenance",
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_name", sa.String(30), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint(
            "metric_name IN ('clicks_28d', 'impressions_28d', 'ctr', 'average_position')",
            name=op.f("ck_page_metric_provenance_supported_metric"),
        ),
        sa.ForeignKeyConstraint(
            ["page_id"],
            ["website_pages.id"],
            ondelete="RESTRICT",
            name=op.f("fk_page_metric_provenance_page_id_website_pages"),
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["page_performance_snapshots.id"],
            ondelete="RESTRICT",
            name=op.f("fk_page_metric_provenance_snapshot_id_page_performance_snapshots"),
        ),
        sa.PrimaryKeyConstraint("page_id", "metric_name", name=op.f("pk_page_metric_provenance")),
    )
    op.create_index(
        op.f("ix_page_metric_provenance_snapshot_id"), "page_metric_provenance", ["snapshot_id"]
    )


def downgrade() -> None:
    """Remove only current provenance links, retaining current values and all history.
    仅删除当前来源关联，保留当前值及全部历史。
    """
    op.drop_index(
        op.f("ix_page_metric_provenance_snapshot_id"), table_name="page_metric_provenance"
    )
    op.drop_table("page_metric_provenance")
