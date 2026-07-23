"""add updated at to tasks

Revision ID: f1c2d3e4a5b6
Revises: 32af132d4ecc
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1c2d3e4a5b6"
down_revision: Union[str, Sequence[str], None] = "32af132d4ecc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
        ),
    )
    op.execute("UPDATE tasks SET updated_at = CURRENT_TIMESTAMP")

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column("updated_at", nullable=False)


def downgrade() -> None:
    op.drop_column("tasks", "updated_at")
