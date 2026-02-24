"""add polls tables

Revision ID: 016_add_polls
Revises: 015_add_bookmarks
Create Date: 2026-02-24
"""

import sqlalchemy as sa

from alembic import op

revision = "016_add_polls"
down_revision = "015_add_bookmarks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "polls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(300), nullable=False),
        sa.Column("multi_choice", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id"),
    )
    op.create_index("ix_polls_id", "polls", ["id"])

    op.create_table(
        "poll_options",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("poll_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(150), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["poll_id"], ["polls.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_poll_options_id", "poll_options", ["id"])
    op.create_index("ix_poll_options_poll_id", "poll_options", ["poll_id"])

    op.create_table(
        "poll_votes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("option_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "voted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["option_id"], ["poll_options.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("option_id", "user_id", name="unique_vote_per_option"),
    )
    op.create_index("ix_poll_votes_id", "poll_votes", ["id"])


def downgrade() -> None:
    op.drop_index("ix_poll_votes_id", table_name="poll_votes")
    op.drop_table("poll_votes")
    op.drop_index("ix_poll_options_poll_id", table_name="poll_options")
    op.drop_index("ix_poll_options_id", table_name="poll_options")
    op.drop_table("poll_options")
    op.drop_index("ix_polls_id", table_name="polls")
    op.drop_table("polls")
