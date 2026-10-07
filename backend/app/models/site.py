from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Site(Base):
    """Identify a GSC property only from explicit observed or declared evidence.
    仅根据明确观察或声明的证据标识 GSC 属性。

    A canonical property identifier is an identity, not proof of authenticated ownership.
    规范属性标识是身份标识，不证明已通过身份认证的归属。
    """

    __tablename__ = "sites"
    __table_args__ = (
        UniqueConstraint("identifier"),
        CheckConstraint("length(btrim(identifier)) > 0", name="identifier_not_blank"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    identifier: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
