"""add reminders table

Revision ID: 019_add_reminders
Revises: 018_add_attachment_duration
Create Date: 2026-02-24
"""

import sqlalchemy as sa

from alembic import op

revision = "019_add_reminders"
down_revision = "018_add_attachment_duration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "delivered",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reminders_id"), "reminders", ["id"], unique=False)
    op.create_index("ix_reminders_user_delivered", "reminders", ["user_id", "delivered"])


def downgrade() -> None:
    op.drop_index("ix_reminders_user_delivered", table_name="reminders")
    op.drop_index(op.f("ix_reminders_id"), table_name="reminders")
    op.drop_table("reminders")
