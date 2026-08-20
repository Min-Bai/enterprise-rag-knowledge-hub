"""add model usage metrics

Revision ID: 1b2c3d4e5f6a
Revises: 0a1b2c3d4e5f
"""

from alembic import op
import sqlalchemy as sa


revision = "1b2c3d4e5f6a"
down_revision = "0a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("model_providers", sa.Column("input_price_per_million", sa.Numeric(12, 6), nullable=True))
    op.add_column("model_providers", sa.Column("output_price_per_million", sa.Numeric(12, 6), nullable=True))
    op.create_table(
        "model_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("knowledge_base_id", sa.Integer(), sa.ForeignKey("knowledge_bases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider_slug", sa.String(length=40), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(16, 8), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_model_usage_user_id", "model_usage", ["user_id"])
    op.create_index("ix_model_usage_knowledge_base_id", "model_usage", ["knowledge_base_id"])
    op.create_index("ix_model_usage_provider_slug", "model_usage", ["provider_slug"])
    op.create_index("ix_model_usage_created_at", "model_usage", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_model_usage_created_at", table_name="model_usage")
    op.drop_index("ix_model_usage_provider_slug", table_name="model_usage")
    op.drop_index("ix_model_usage_knowledge_base_id", table_name="model_usage")
    op.drop_index("ix_model_usage_user_id", table_name="model_usage")
    op.drop_table("model_usage")
    op.drop_column("model_providers", "output_price_per_million")
    op.drop_column("model_providers", "input_price_per_million")
