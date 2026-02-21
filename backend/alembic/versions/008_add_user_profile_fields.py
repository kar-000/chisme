"""Add display_name and bio to users table

Revision ID: 008_add_user_profile_fields
Revises: 007_add_read_receipts
Create Date: 2026-02-21
"""

import sqlalchemy as sa

from alembic import op

revision = "008_add_user_profile_fields"
down_revision = "007_add_read_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("bio", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "bio")
    op.drop_column("users", "display_name")
