"""set null on task user delete

Revision ID: a7b8c9d0e1f2
Revises: f1c2d3e4a5b6
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f1c2d3e4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table(
            "tasks",
            naming_convention=NAMING_CONVENTION,
            recreate="always",
        ) as batch_op:
            batch_op.drop_constraint(
                "fk_tasks_user_id_users",
                type_="foreignkey",
            )
            batch_op.create_foreign_key(
                "fk_tasks_user_id_users",
                "users",
                ["user_id"],
                ["id"],
                ondelete="SET NULL",
            )
    else:
        op.drop_constraint(
            "fk_tasks_user_id_users",
            "tasks",
            type_="foreignkey",
        )
        op.create_foreign_key(
            "fk_tasks_user_id_users",
            "tasks",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )
    with op.batch_alter_table(
        "tasks",
        naming_convention=NAMING_CONVENTION,
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint("fk_tasks_user_id_users", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_tasks_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "tasks",
        naming_convention=NAMING_CONVENTION,
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint("fk_tasks_user_id_users", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_tasks_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
