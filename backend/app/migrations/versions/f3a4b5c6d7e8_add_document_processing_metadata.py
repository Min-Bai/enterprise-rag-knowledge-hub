"""add document processing metadata

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
"""

from alembic import op
import sqlalchemy as sa

revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("documents", sa.Column("processed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "processed_at")
    op.drop_column("documents", "chunk_count")
