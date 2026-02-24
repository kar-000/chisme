"""add bookmarks table

Revision ID: 015_add_bookmarks
Revises: 014_add_quiet_hours
Create Date: 2026-02-24
"""

import sqlalchemy as sa

from alembic import op

revision = "015_add_bookmarks"
down_revision = "014_add_quiet_hours"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bookmarks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "message_id", name="unique_bookmark"),
    )
    op.create_index("ix_bookmarks_id", "bookmarks", ["id"])
    op.create_index("ix_bookmarks_user_id", "bookmarks", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_bookmarks_user_id", table_name="bookmarks")
    op.drop_index("ix_bookmarks_id", table_name="bookmarks")
    op.drop_table("bookmarks")
