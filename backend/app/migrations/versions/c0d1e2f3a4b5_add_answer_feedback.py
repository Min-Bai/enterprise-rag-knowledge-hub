"""add answer feedback

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
"""

from alembic import op
import sqlalchemy as sa

revision = "c0d1e2f3a4b5"
down_revision = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversation_messages", sa.Column("feedback", sa.String(length=20), nullable=True))
    op.add_column("conversation_messages", sa.Column("feedback_comment", sa.Text(), nullable=True))
    op.add_column("conversation_messages", sa.Column("feedback_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("conversation_messages", "feedback_at")
    op.drop_column("conversation_messages", "feedback_comment")
    op.drop_column("conversation_messages", "feedback")
