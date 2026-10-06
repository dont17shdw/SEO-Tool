"""Create the initial page and opportunity storage.
创建初始的页面和机会存储结构。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create domain tables with basic data integrity constraints and indexes.
    创建领域表，并添加基本的数据完整性约束和索引。
    """
    op.create_table(
        "website_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("page_type", sa.String(50), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("primary_keyword", sa.Text(), nullable=True),
        sa.Column("clicks_7d", sa.BigInteger(), nullable=True),
        sa.Column("clicks_28d", sa.BigInteger(), nullable=True),
        sa.Column("clicks_previous_28d", sa.BigInteger(), nullable=True),
        sa.Column("impressions_7d", sa.BigInteger(), nullable=True),
        sa.Column("impressions_28d", sa.BigInteger(), nullable=True),
        sa.Column("impressions_previous_28d", sa.BigInteger(), nullable=True),
        sa.Column("ctr", sa.Numeric(7, 6), nullable=True),
        sa.Column("average_position", sa.Numeric(10, 4), nullable=True),
        sa.Column("indexed", sa.Boolean(), nullable=True),
        sa.Column("index_status", sa.String(50), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("internal_links_in", sa.Integer(), nullable=True),
        sa.Column("internal_links_out", sa.Integer(), nullable=True),
        sa.Column("backlinks", sa.Integer(), nullable=True),
        sa.Column("business_value", sa.Numeric(12, 4), nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("clicks_7d >= 0", name=op.f("ck_website_pages_clicks_7d_nonnegative")),
        sa.CheckConstraint("clicks_28d >= 0", name=op.f("ck_website_pages_clicks_28d_nonnegative")),
        sa.CheckConstraint(
            "clicks_previous_28d >= 0",
            name=op.f("ck_website_pages_clicks_previous_28d_nonnegative"),
        ),
        sa.CheckConstraint(
            "impressions_7d >= 0", name=op.f("ck_website_pages_impressions_7d_nonnegative")
        ),
        sa.CheckConstraint(
            "impressions_28d >= 0", name=op.f("ck_website_pages_impressions_28d_nonnegative")
        ),
        sa.CheckConstraint(
            "impressions_previous_28d >= 0",
            name=op.f("ck_website_pages_impressions_previous_28d_nonnegative"),
        ),
        sa.CheckConstraint("ctr >= 0 AND ctr <= 1", name=op.f("ck_website_pages_ctr_fraction")),
        sa.CheckConstraint(
            "average_position >= 0", name=op.f("ck_website_pages_average_position_nonnegative")
        ),
        sa.CheckConstraint("word_count >= 0", name=op.f("ck_website_pages_word_count_nonnegative")),
        sa.CheckConstraint(
            "internal_links_in >= 0", name=op.f("ck_website_pages_internal_links_in_nonnegative")
        ),
        sa.CheckConstraint(
            "internal_links_out >= 0", name=op.f("ck_website_pages_internal_links_out_nonnegative")
        ),
        sa.CheckConstraint("backlinks >= 0", name=op.f("ck_website_pages_backlinks_nonnegative")),
        sa.CheckConstraint(
            "business_value >= 0", name=op.f("ck_website_pages_business_value_nonnegative")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_website_pages")),
        sa.UniqueConstraint("url", name=op.f("uq_website_pages_url")),
    )
    op.create_table(
        "seo_opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_type", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(30), nullable=True),
        sa.Column("opportunity_score", sa.Numeric(12, 4), nullable=True),
        sa.Column("confidence", sa.Numeric(7, 6), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("expected_impact", sa.Text(), nullable=True),
        sa.Column("estimated_effort", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(30), nullable=True),
        sa.Column("status", sa.String(30), server_default=sa.text("'pending'"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "opportunity_score >= 0",
            name=op.f("ck_seo_opportunities_opportunity_score_nonnegative"),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_seo_opportunities_confidence_fraction"),
        ),
        sa.ForeignKeyConstraint(
            ["page_id"],
            ["website_pages.id"],
            ondelete="RESTRICT",
            name=op.f("fk_seo_opportunities_page_id_website_pages"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_seo_opportunities")),
    )
    op.create_index(op.f("ix_seo_opportunities_page_id"), "seo_opportunities", ["page_id"])
    op.create_index(op.f("ix_seo_opportunities_status"), "seo_opportunities", ["status"])


def downgrade() -> None:
    """Remove dependent opportunities before removing pages.
    先删除依赖页面的机会表，再删除页面表。
    """
    op.drop_index(op.f("ix_seo_opportunities_status"), table_name="seo_opportunities")
    op.drop_index(op.f("ix_seo_opportunities_page_id"), table_name="seo_opportunities")
    op.drop_table("seo_opportunities")
    op.drop_table("website_pages")
