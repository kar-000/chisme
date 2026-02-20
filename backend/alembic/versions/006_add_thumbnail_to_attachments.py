"""Add thumbnail_filename to attachments for image thumbnails

Revision ID: 006_add_thumbnail
Revises: 005_add_external_url
Create Date: 2026-02-19
"""

import sqlalchemy as sa
from alembic import op

revision = "006_add_thumbnail"
down_revision = "005_add_external_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("attachments", sa.Column("thumbnail_filename", sa.String(255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("attachments") as batch_op:
        batch_op.drop_column("thumbnail_filename")
