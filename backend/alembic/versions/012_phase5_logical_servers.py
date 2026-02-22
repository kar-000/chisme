"""phase 5 logical servers

Revision ID: 012_phase5_logical_servers
Revises: 011_add_push_subscriptions
Create Date: 2026-02-22

Introduces:
- servers table (with suspension fields)
- server_memberships table
- server_invites table
- channels.server_id (migrates existing channels to a seeded 'main' server)
- users.is_site_admin, users.can_create_server
- Replaces the global unique constraint on channels.name with a per-server one
"""

import sqlalchemy as sa

from alembic import op

revision = "012_phase5_logical_servers"
down_revision = "011_add_push_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Create servers table ─────────────────────────────────────────────
    op.create_table(
        "servers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("icon_url", sa.String(500), nullable=True),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_suspended", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("suspended_reason", sa.String(500), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_servers_slug", "servers", ["slug"])

    # ── 2. Create server_memberships table ──────────────────────────────────
    op.create_table(
        "server_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "server_id",
            sa.Integer(),
            sa.ForeignKey("servers.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("server_id", "user_id", name="unique_server_member"),
    )
    op.create_index("ix_server_memberships_server_id", "server_memberships", ["server_id"])
    op.create_index("ix_server_memberships_user_id", "server_memberships", ["user_id"])

    # ── 3. Create server_invites table ──────────────────────────────────────
    op.create_table(
        "server_invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "server_id",
            sa.Integer(),
            sa.ForeignKey("servers.id"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("code", sa.String(12), nullable=False, unique=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_server_invites_code", "server_invites", ["code"])

    # ── 4. Add server_id to channels (nullable first for data migration) ────
    op.add_column("channels", sa.Column("server_id", sa.Integer(), nullable=True))

    # ── 5. Seed the default 'main' server (earliest registered user is owner) ──
    op.execute(
        """
        INSERT INTO servers (name, slug, description, owner_id, is_public, is_suspended)
        SELECT
            'Main',
            'main',
            'The original Chisme community',
            (SELECT id FROM users ORDER BY created_at ASC LIMIT 1),
            0,
            0
        WHERE EXISTS (SELECT 1 FROM users)
        """
    )

    # ── 6. Assign all existing channels to the default server ───────────────
    op.execute(
        """
        UPDATE channels
        SET server_id = (SELECT id FROM servers WHERE slug = 'main')
        WHERE EXISTS (SELECT 1 FROM servers WHERE slug = 'main')
        """
    )

    # ── 7. Enroll all existing users as members of the default server ───────
    op.execute(
        """
        INSERT INTO server_memberships (server_id, user_id, role)
        SELECT
            (SELECT id FROM servers WHERE slug = 'main'),
            u.id,
            CASE
                WHEN u.id = (SELECT owner_id FROM servers WHERE slug = 'main')
                THEN 'owner'
                ELSE 'member'
            END
        FROM users u
        WHERE EXISTS (SELECT 1 FROM servers WHERE slug = 'main')
        """
    )

    # ── 8-9. Restructure channels: make server_id non-nullable, replace ──────
    #         global unique constraint with per-server unique.
    #
    # Use batch_alter_table so this works on both SQLite (which cannot ALTER
    # COLUMN or DROP CONSTRAINT) and PostgreSQL (which can).  Batch mode
    # recreates the table on SQLite and issues native DDL on Postgres.
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    with op.batch_alter_table("channels", schema=None) as batch_op:
        batch_op.alter_column("server_id", nullable=False)
        batch_op.create_foreign_key("fk_channels_server_id", "servers", ["server_id"], ["id"])
        # Drop the old global unique on name.
        # On Postgres it was auto-named 'channels_name_key'.
        # On SQLite the inline unique is dropped when the table is recreated.
        if is_postgres:
            try:
                batch_op.drop_constraint("channels_name_key", type_="unique")
            except Exception:
                pass  # Already gone
        batch_op.create_unique_constraint("unique_channel_per_server", ["server_id", "name"])

    # ── 10. Add site-level flags to users ────────────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "is_site_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "can_create_server",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "can_create_server")
    op.drop_column("users", "is_site_admin")

    with op.batch_alter_table("channels", schema=None) as batch_op:
        try:
            batch_op.drop_constraint("unique_channel_per_server", type_="unique")
        except Exception:
            pass
        try:
            batch_op.drop_constraint("fk_channels_server_id", type_="foreignkey")
        except Exception:
            pass
        batch_op.alter_column("server_id", nullable=True)
        batch_op.create_unique_constraint("channels_name_key", ["name"])

    op.drop_column("channels", "server_id")

    op.drop_index("ix_server_invites_code", "server_invites")
    op.drop_table("server_invites")

    op.drop_index("ix_server_memberships_user_id", "server_memberships")
    op.drop_index("ix_server_memberships_server_id", "server_memberships")
    op.drop_table("server_memberships")

    op.drop_index("ix_servers_slug", "servers")
    op.drop_table("servers")
