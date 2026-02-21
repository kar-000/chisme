"""Add home_server to users table

Revision ID: 009_add_home_server
Revises: 008_add_user_profile_fields
Create Date: 2026-02-21
"""

import sqlalchemy as sa

from alembic import op

revision = "009_add_home_server"
down_revision = "008_add_user_profile_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "home_server",
            sa.String(255),
            nullable=False,
            server_default="local",
        ),
    )
    op.create_index("ix_users_home_server", "users", ["home_server"])


def downgrade() -> None:
    op.drop_index("ix_users_home_server", table_name="users")
    op.drop_column("users", "home_server")
