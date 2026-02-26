"""add nickname to server_memberships

Revision ID: 021_add_nickname_to_server_memberships
Revises: 020_add_channel_notes
Create Date: 2026-02-25
"""

import sqlalchemy as sa

from alembic import op

revision = "021_add_nickname_to_server_memberships"
down_revision = "020_add_channel_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("server_memberships", sa.Column("nickname", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("server_memberships", "nickname")
