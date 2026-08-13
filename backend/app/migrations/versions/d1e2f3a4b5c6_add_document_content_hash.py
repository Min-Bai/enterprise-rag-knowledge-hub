"""add document content hash

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
"""

from alembic import op
import sqlalchemy as sa

revision = "d1e2f3a4b5c6"
down_revision = "c0d1e2f3a4b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(sa.Column("content_sha256", sa.String(length=64), nullable=True))
        batch_op.create_unique_constraint("uq_documents_knowledge_base_content_sha256", ["knowledge_base_id", "content_sha256"])


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_constraint("uq_documents_knowledge_base_content_sha256", type_="unique")
        batch_op.drop_column("content_sha256")
