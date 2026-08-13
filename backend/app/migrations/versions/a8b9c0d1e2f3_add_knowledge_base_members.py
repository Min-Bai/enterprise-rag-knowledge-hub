"""add knowledge base members

Revision ID: a8b9c0d1e2f3
Revises: f6a7b8c9d0e1
"""

from alembic import op
import sqlalchemy as sa

revision = "a8b9c0d1e2f3"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_base_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("knowledge_base_id", "user_id", name="uq_knowledge_base_membership"),
    )
    op.create_index("ix_knowledge_base_members_knowledge_base_id", "knowledge_base_members", ["knowledge_base_id"])
    op.create_index("ix_knowledge_base_members_user_id", "knowledge_base_members", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_base_members_user_id", table_name="knowledge_base_members")
    op.drop_index("ix_knowledge_base_members_knowledge_base_id", table_name="knowledge_base_members")
    op.drop_table("knowledge_base_members")
