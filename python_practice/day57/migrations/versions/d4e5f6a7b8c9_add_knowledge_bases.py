"""add knowledge bases

Revision ID: d4e5f6a7b8c9
Revises: 226fd4f7591d
Create Date: 2026-08-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "226fd4f7591d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_bases_owner_user_id", "knowledge_bases", ["owner_user_id"])

    op.add_column(
        "documents",
        sa.Column("knowledge_base_id", sa.Integer(), nullable=True),
    )

    connection = op.get_bind()
    users = connection.execute(sa.text("SELECT id FROM users")).mappings()
    for user in users:
        connection.execute(
            sa.text(
                "INSERT INTO knowledge_bases (owner_user_id, name, created_at) "
                "VALUES (:user_id, :name, CURRENT_TIMESTAMP)"
            ),
            {"user_id": user["id"], "name": "Default knowledge base"},
        )
        knowledge_base_id = connection.scalar(
            sa.text(
                "SELECT id FROM knowledge_bases "
                "WHERE owner_user_id = :user_id AND name = :name"
            ),
            {"user_id": user["id"], "name": "Default knowledge base"},
        )
        connection.execute(
            sa.text(
                "UPDATE documents SET knowledge_base_id = :knowledge_base_id "
                "WHERE user_id = :user_id"
            ),
            {"knowledge_base_id": knowledge_base_id, "user_id": user["id"]},
        )

    with op.batch_alter_table("documents") as batch_op:
        batch_op.alter_column("knowledge_base_id", nullable=False)
        batch_op.create_foreign_key(
            "fk_documents_knowledge_base_id_knowledge_bases",
            "knowledge_bases",
            ["knowledge_base_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_documents_knowledge_base_id", ["knowledge_base_id"])


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_index("ix_documents_knowledge_base_id")
        batch_op.drop_constraint(
            "fk_documents_knowledge_base_id_knowledge_bases",
            type_="foreignkey",
        )
        batch_op.drop_column("knowledge_base_id")

    op.drop_index("ix_knowledge_bases_owner_user_id", table_name="knowledge_bases")
    op.drop_table("knowledge_bases")
