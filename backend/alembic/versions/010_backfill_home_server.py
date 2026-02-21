"""Backfill home_server with SERVER_DOMAIN env var

Revision ID: 010_backfill_home_server
Revises: 009_add_home_server
Create Date: 2026-02-21

Run AFTER setting SERVER_DOMAIN in your environment.
Any user whose home_server is still 'local' gets updated to the real domain.
"""

import os

from alembic import op

revision = "010_backfill_home_server"
down_revision = "009_add_home_server"
branch_labels = None
depends_on = None


def upgrade() -> None:
    domain = os.getenv("SERVER_DOMAIN", "localhost")
    op.execute(f"UPDATE users SET home_server = '{domain}' WHERE home_server = 'local'")


def downgrade() -> None:
    pass  # Not reversible without tracking original values
