"""Add dm_channels and update messages for DMs

Revision ID: 004_add_dm_channels
Revises: 003_add_reply_to
Create Date: 2026-02-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_add_dm_channels"
down_revision: Union[str, None] = "003_add_reply_to"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dm_channels",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user1_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("user2_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user1_id", "user2_id", name="unique_dm_pair"),
    )

    with op.batch_alter_table("messages") as batch_op:
        batch_op.add_column(sa.Column("dm_channel_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_messages_dm_channel_id", "dm_channels", ["dm_channel_id"], ["id"],
            ondelete="CASCADE",
        )
        # Make channel_id nullable so DM messages don't need a channel
        batch_op.alter_column("channel_id", nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column("channel_id", nullable=False)
        batch_op.drop_constraint("fk_messages_dm_channel_id", type_="foreignkey")
        batch_op.drop_column("dm_channel_id")
    op.drop_table("dm_channels")
