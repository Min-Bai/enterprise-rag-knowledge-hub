from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class KnowledgeBaseMemberORM(Base):
    __tablename__ = "knowledge_base_members"
    __table_args__ = (UniqueConstraint("knowledge_base_id", "user_id", name="uq_knowledge_base_membership"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
