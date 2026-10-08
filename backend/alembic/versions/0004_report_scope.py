"""Add explicit property scope and observed coverage without inferring legacy evidence.
添加明确属性范围及已观察覆盖，不推断旧数据证据。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_report_scope"
down_revision: str | Sequence[str] | None = "0003_current_metric_provenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Freeze the canonical unknown fingerprint so future application changes cannot alter migration.
# 固定规范未知范围指纹，防止未来应用变化影响此迁移。
# Hash compact sorted JSON: filters=[], filters_complete=false, null property/search, version=1.
# 对紧凑排序 JSON 计算 SHA-256：filters=[]、filters_complete=false、属性及搜索为空、version=1。
UNKNOWN_SCOPE_FINGERPRINT = "a965b425ddf7be68f5b0aa31a332bd7a004d70e2908b09dfcbcf6883a265b877"

DATE_COVERAGE_CHECK = (
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
    "AND period_end - period_start + 1 = 28))"
)


def upgrade() -> None:
    """Extend identity safely; old values, timestamps, snapshots, and links remain untouched.
    安全扩展身份；旧值、时间戳、快照及关联保持不变。
    """
    op.create_table(
        "sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identifier", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(identifier)) > 0", name=op.f("ck_sites_identifier_not_blank")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sites")),
        sa.UniqueConstraint("identifier", name=op.f("uq_sites_identifier")),
    )
    for table in ("website_pages", "import_runs"):
        op.add_column(table, sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            op.f(f"fk_{table}_site_id_sites"),
            table,
            "sites",
            ["site_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(op.f(f"ix_{table}_site_id"), table, ["site_id"])
    op.drop_constraint(op.f("uq_website_pages_url"), "website_pages", type_="unique")
    op.create_unique_constraint(
        op.f("uq_website_pages_site_id"),
        "website_pages",
        ["site_id", "url"],
        postgresql_nulls_not_distinct=True,
    )
    op.add_column("import_runs", sa.Column("report_scope", postgresql.JSONB(none_as_null=True)))
    op.add_column(
        "import_runs",
        sa.Column(
            "scope_fingerprint",
            sa.String(64),
            server_default=sa.text(f"'{UNKNOWN_SCOPE_FINGERPRINT}'"),
            nullable=False,
        ),
    )
    op.add_column("import_runs", sa.Column("observed_date_count", sa.Integer(), nullable=True))
    op.add_column("import_runs", sa.Column("dates_consecutive", sa.Boolean(), nullable=True))
    op.add_column(
        "import_runs",
        sa.Column(
            "coverage_status", sa.String(10), server_default=sa.text("'unknown'"), nullable=False
        ),
    )
    op.create_check_constraint(
        op.f("ck_import_runs_scope_fingerprint_sha256"),
        "import_runs",
        "scope_fingerprint ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        op.f("ck_import_runs_report_scope_object"),
        "import_runs",
        "report_scope IS NULL OR jsonb_typeof(report_scope) = 'object'",
    )
    op.create_check_constraint(
        op.f("ck_import_runs_date_coverage"), "import_runs", DATE_COVERAGE_CHECK
    )
    op.drop_constraint("uq_import_runs_source_source_type_file_hash", "import_runs", type_="unique")
    op.create_unique_constraint(
        "uq_import_runs_source_type_file_scope",
        "import_runs",
        ["source", "source_type", "file_hash", "scope_fingerprint"],
    )


def downgrade() -> None:
    """Refuse destructive identity collapse before removing only Phase 6 additions.
    在仅删除第六阶段新增内容前，拒绝具有破坏性的身份合并。

    Different site/scope rows may collide with old uniqueness; never delete or rewrite them.
    不同站点或范围的行可能违反旧唯一性；绝不删除或改写这些行。
    """
    connection = op.get_bind()
    if connection.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM website_pages GROUP BY url HAVING count(*) > 1)")
    ):
        raise RuntimeError(
            "Cannot downgrade Phase 6: scoped pages collide with legacy URL uniqueness. "
            "第六阶段无法降级：按范围区分的页面与旧 URL 唯一性冲突。"
        )
    if connection.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM import_runs "
            "GROUP BY source, source_type, file_hash HAVING count(*) > 1)"
        )
    ):
        raise RuntimeError(
            "Cannot downgrade Phase 6: scoped imports collide with legacy file uniqueness. "
            "第六阶段无法降级：按范围区分的导入与旧文件唯一性冲突。"
        )
    op.drop_constraint("uq_import_runs_source_type_file_scope", "import_runs", type_="unique")
    op.create_unique_constraint(
        "uq_import_runs_source_source_type_file_hash",
        "import_runs",
        ["source", "source_type", "file_hash"],
    )
    op.drop_constraint(op.f("uq_website_pages_site_id"), "website_pages", type_="unique")
    op.create_unique_constraint(op.f("uq_website_pages_url"), "website_pages", ["url"])
    for name in ("date_coverage", "report_scope_object", "scope_fingerprint_sha256"):
        op.drop_constraint(op.f(f"ck_import_runs_{name}"), "import_runs", type_="check")
    for column in (
        "coverage_status",
        "dates_consecutive",
        "observed_date_count",
        "scope_fingerprint",
        "report_scope",
    ):
        op.drop_column("import_runs", column)
    for table in ("import_runs", "website_pages"):
        op.drop_index(op.f(f"ix_{table}_site_id"), table_name=table)
        op.drop_constraint(op.f(f"fk_{table}_site_id_sites"), table, type_="foreignkey")
        op.drop_column(table, "site_id")
    op.drop_table("sites")
