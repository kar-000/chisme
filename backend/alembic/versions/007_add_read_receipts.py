"""Add read_receipts table for per-user unread tracking

Revision ID: 007_add_read_receipts
Revises: 006_add_thumbnail
Create Date: 2026-02-21
"""

import sqlalchemy as sa
from alembic import op

revision = "007_add_read_receipts"
down_revision = "006_add_thumbnail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "read_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("last_read_message_id", sa.Integer(), nullable=True),
        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_read_message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "channel_id", name="uq_read_receipt_user_channel"),
    )
    op.create_index("ix_read_receipts_id", "read_receipts", ["id"])


def downgrade() -> None:
    op.drop_index("ix_read_receipts_id", table_name="read_receipts")
    op.drop_table("read_receipts")
