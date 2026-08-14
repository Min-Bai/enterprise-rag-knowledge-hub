"""add document tags

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
"""

from alembic import op
import sqlalchemy as sa


revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("tags", sa.JSON(), nullable=True),
    )
    op.execute("UPDATE documents SET tags = JSON_ARRAY() WHERE tags IS NULL")
    with op.batch_alter_table("documents") as batch_op:
        batch_op.alter_column("tags", existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    op.drop_column("documents", "tags")
