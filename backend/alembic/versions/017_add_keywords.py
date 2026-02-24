"""add user_keywords table

Revision ID: 017_add_keywords
Revises: 016_add_polls
Create Date: 2026-02-24
"""

import sqlalchemy as sa

from alembic import op

revision = "017_add_keywords"
down_revision = "016_add_polls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_keywords",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("keyword", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "keyword", name="unique_user_keyword"),
    )
    op.create_index(op.f("ix_user_keywords_id"), "user_keywords", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_keywords_id"), table_name="user_keywords")
    op.drop_table("user_keywords")
