"""merge model provider and account request heads

Revision ID: 0a1b2c3d4e5f
Revises: e8f9a0b1c2d3, f9a0b1c2d3e4
"""

from typing import Sequence, Union


revision: str = "0a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = (
    "e8f9a0b1c2d3",
    "f9a0b1c2d3e4",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
