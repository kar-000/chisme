"""Add reply_to_id to messages

Revision ID: 003_add_reply_to
Revises: 002_add_attachments
Create Date: 2026-02-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_add_reply_to"
down_revision: Union[str, None] = "002_add_attachments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("messages") as batch_op:
        batch_op.add_column(sa.Column("reply_to_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_messages_reply_to_id", "messages", ["reply_to_id"], ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_constraint("fk_messages_reply_to_id", type_="foreignkey")
        batch_op.drop_column("reply_to_id")
