"""Add completed GSC import history and page-performance observations.
添加已完成的 GSC 导入历史与页面性能观测记录。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_import_history"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add historical tables without changing existing pages or opportunities.
    添加历史表，不改变已有页面或机会记录。
    """
    op.create_table(
        "import_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(30), server_default=sa.text("'gsc'"), nullable=False),
        sa.Column(
            "source_type",
            sa.String(50),
            server_default=sa.text("'pages_performance'"),
            nullable=False,
        ),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column(
            "reporting_window",
            sa.String(30),
            server_default=sa.text("'latest_28_days'"),
            nullable=False,
        ),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("created_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("updated_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("skipped_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(30), server_default=sa.text("'completed'"), nullable=False),
        sa.CheckConstraint(
            "file_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_import_runs_file_hash_sha256")
        ),
        sa.CheckConstraint("total_rows >= 0", name=op.f("ck_import_runs_total_rows_nonnegative")),
        sa.CheckConstraint(
            "created_count >= 0", name=op.f("ck_import_runs_created_count_nonnegative")
        ),
        sa.CheckConstraint(
            "updated_count >= 0", name=op.f("ck_import_runs_updated_count_nonnegative")
        ),
        sa.CheckConstraint(
            "skipped_count >= 0", name=op.f("ck_import_runs_skipped_count_nonnegative")
        ),
        sa.CheckConstraint(
            "created_count + updated_count + skipped_count = total_rows",
            name=op.f("ck_import_runs_counts_sum"),
        ),
        sa.CheckConstraint(
            "(period_start IS NULL AND period_end IS NULL) OR "
            "(period_start IS NOT NULL AND period_end IS NOT NULL AND period_end >= period_start)",
            name=op.f("ck_import_runs_period_dates"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_runs")),
        sa.UniqueConstraint(
            "source", "source_type", "file_hash", name="uq_import_runs_source_source_type_file_hash"
        ),
    )
    op.create_index(op.f("ix_import_runs_imported_at"), "import_runs", ["imported_at"])
    op.create_index("ix_import_runs_period", "import_runs", ["period_start", "period_end"])
    op.create_table(
        "page_performance_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("clicks", sa.BigInteger(), nullable=True),
        sa.Column("impressions", sa.BigInteger(), nullable=True),
        sa.Column("ctr", sa.Numeric(7, 6), nullable=True),
        sa.Column("average_position", sa.Numeric(10, 4), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "clicks >= 0", name=op.f("ck_page_performance_snapshots_clicks_nonnegative")
        ),
        sa.CheckConstraint(
            "impressions >= 0", name=op.f("ck_page_performance_snapshots_impressions_nonnegative")
        ),
        sa.CheckConstraint(
            "ctr >= 0 AND ctr <= 1", name=op.f("ck_page_performance_snapshots_ctr_fraction")
        ),
        sa.CheckConstraint(
            "average_position >= 0",
            name=op.f("ck_page_performance_snapshots_average_position_nonnegative"),
        ),
        sa.CheckConstraint(
            "(period_start IS NULL AND period_end IS NULL) OR "
            "(period_start IS NOT NULL AND period_end IS NOT NULL AND period_end >= period_start)",
            name=op.f("ck_page_performance_snapshots_period_dates"),
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            ondelete="RESTRICT",
            name=op.f("fk_page_performance_snapshots_import_run_id_import_runs"),
        ),
        sa.ForeignKeyConstraint(
            ["page_id"],
            ["website_pages.id"],
            ondelete="RESTRICT",
            name=op.f("fk_page_performance_snapshots_page_id_website_pages"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_page_performance_snapshots")),
        sa.UniqueConstraint(
            "import_run_id", "page_id", name="uq_page_performance_snapshots_import_run_id_page_id"
        ),
    )
    op.create_index(
        "ix_page_performance_snapshots_page_period",
        "page_performance_snapshots",
        ["page_id", "period_end", "period_start"],
    )


def downgrade() -> None:
    """Remove only Phase 3 history; retain current pages and opportunities.
    仅删除第三阶段历史，保留当前页面及机会记录。
    """
    op.drop_index(
        "ix_page_performance_snapshots_page_period", table_name="page_performance_snapshots"
    )
    op.drop_table("page_performance_snapshots")
    op.drop_index("ix_import_runs_period", table_name="import_runs")
    op.drop_index(op.f("ix_import_runs_imported_at"), table_name="import_runs")
    op.drop_table("import_runs")
