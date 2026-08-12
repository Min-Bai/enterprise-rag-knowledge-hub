from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(
    String(20),
    default="user",
    server_default="user",
    nullable=False,
)
    tasks: Mapped[list["TaskORM"]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
    token_version: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    documents: Mapped[list["DocumentORM"]] = relationship(
    back_populates="user",
    passive_deletes=True,
)
    knowledge_bases: Mapped[list["KnowledgeBaseORM"]] = relationship(
        back_populates="owner",
        passive_deletes=True,
    )
