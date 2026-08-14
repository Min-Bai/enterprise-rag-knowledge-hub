from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class KnowledgeBaseORM(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    owner: Mapped["UserORM"] = relationship(back_populates="knowledge_bases")
    documents: Mapped[list["DocumentORM"]] = relationship(
        back_populates="knowledge_base",
        passive_deletes=True,
    )
    members: Mapped[list["KnowledgeBaseMemberORM"]] = relationship(passive_deletes=True)
