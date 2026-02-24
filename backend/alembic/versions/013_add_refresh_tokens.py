"""add refresh_tokens table

Revision ID: 013_add_refresh_tokens
Revises: 012_phase5_logical_servers
Create Date: 2026-02-24

Introduces:
- refresh_tokens table for persistent PWA sessions
  Columns: id, user_id (FK→users CASCADE), token (unique), expires_at, revoked, created_at
"""

import sqlalchemy as sa

from alembic import op

revision = "013_add_refresh_tokens"
down_revision = "012_phase5_logical_servers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("token", sa.String(128), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"])


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_token", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
