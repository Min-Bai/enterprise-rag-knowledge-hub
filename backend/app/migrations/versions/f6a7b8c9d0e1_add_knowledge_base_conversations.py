"""add knowledge base conversations

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
"""

from alembic import op
import sqlalchemy as sa


revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.add_column(sa.Column("knowledge_base_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_conversations_knowledge_base_id",
            "knowledge_bases",
            ["knowledge_base_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_conversations_knowledge_base_id", ["knowledge_base_id"])
        batch_op.alter_column("document_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.alter_column("document_id", existing_type=sa.Integer(), nullable=False)
        batch_op.drop_index("ix_conversations_knowledge_base_id")
        batch_op.drop_constraint("fk_conversations_knowledge_base_id", type_="foreignkey")
        batch_op.drop_column("knowledge_base_id")
