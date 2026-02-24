"""add duration_secs to attachments

Revision ID: 018_add_attachment_duration
Revises: 017_add_keywords
Create Date: 2026-02-24
"""

import sqlalchemy as sa

from alembic import op

revision = "018_add_attachment_duration"
down_revision = "017_add_keywords"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("attachments", sa.Column("duration_secs", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("attachments", "duration_secs")
