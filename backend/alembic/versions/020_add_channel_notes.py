"""add channel notes tables

Revision ID: 020_add_channel_notes
Revises: 019_add_reminders
Create Date: 2026-02-24
"""

import sqlalchemy as sa

from alembic import op

revision = "020_add_channel_notes"
down_revision = "019_add_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "channel_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", name="uq_channel_notes_channel"),
    )
    op.create_index(op.f("ix_channel_notes_id"), "channel_notes", ["id"], unique=False)

    op.create_table(
        "channel_notes_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notes_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("edited_by", sa.Integer(), nullable=False),
        sa.Column(
            "edited_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["edited_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["notes_id"], ["channel_notes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_channel_notes_history_id"),
        "channel_notes_history",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_channel_notes_history_id"), table_name="channel_notes_history")
    op.drop_table("channel_notes_history")
    op.drop_index(op.f("ix_channel_notes_id"), table_name="channel_notes")
    op.drop_table("channel_notes")
