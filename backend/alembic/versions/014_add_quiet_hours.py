"""add quiet hours / DND fields to users

Revision ID: 014_add_quiet_hours
Revises: 013_add_refresh_tokens
Create Date: 2026-02-24

Adds five columns to the users table for Do Not Disturb / Quiet Hours (Feature 1):
  quiet_hours_enabled  — master toggle
  quiet_hours_start    — start time (e.g. 23:00)
  quiet_hours_end      — end time   (e.g. 08:00)
  quiet_hours_tz       — IANA timezone string (e.g. "America/Chicago")
  dnd_override         — "on" | "off" | NULL (NULL = use schedule)
"""

import sqlalchemy as sa

from alembic import op

revision = "014_add_quiet_hours"
down_revision = "013_add_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "quiet_hours_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("users", sa.Column("quiet_hours_start", sa.Time(), nullable=True))
    op.add_column("users", sa.Column("quiet_hours_end", sa.Time(), nullable=True))
    op.add_column("users", sa.Column("quiet_hours_tz", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("dnd_override", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "dnd_override")
    op.drop_column("users", "quiet_hours_tz")
    op.drop_column("users", "quiet_hours_end")
    op.drop_column("users", "quiet_hours_start")
    op.drop_column("users", "quiet_hours_enabled")
