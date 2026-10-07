"""Describe this schema migration in English and Chinese.
请使用英文和中文说明此数据库结构迁移。

Message: ${message}
Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | Sequence[str] | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    """Apply this schema revision.
    应用此数据库结构版本。
    """
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Revert this schema revision.
    撤销此数据库结构版本。
    """
    ${downgrades if downgrades else "pass"}
