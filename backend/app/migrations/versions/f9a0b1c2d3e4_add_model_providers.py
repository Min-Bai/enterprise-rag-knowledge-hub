"""add model providers

Revision ID: f9a0b1c2d3e4
Revises: f6a7b8c9d0e1
"""

from alembic import op
import sqlalchemy as sa


revision = "f9a0b1c2d3e4"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_providers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=40), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("model_providers")
