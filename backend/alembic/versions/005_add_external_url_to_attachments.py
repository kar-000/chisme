"""Add external_url to attachments for Tenor GIF support

Revision ID: 005_add_external_url
Revises: 004_add_dm_channels
Create Date: 2026-02-19
"""

import sqlalchemy as sa
from alembic import op

revision = "005_add_external_url"
down_revision = "004_add_dm_channels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("attachments", sa.Column("external_url", sa.String(2048), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("attachments") as batch_op:
        batch_op.drop_column("external_url")
