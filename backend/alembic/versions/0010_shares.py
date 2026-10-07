"""0010 File Server (Samba) — samba_shares."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("samba_shares",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64), unique=True, index=True),
        sa.Column("path", sa.String(255)),
        sa.Column("comment", sa.String(255), server_default=""),
        sa.Column("read_only", sa.Boolean, server_default="0"),
        sa.Column("browsable", sa.Boolean, server_default="1"),
        sa.Column("guest_ok", sa.Boolean, server_default="0"),
        sa.Column("valid_users", sa.String(255), server_default=""),
        sa.Column("valid_groups", sa.String(255), server_default=""),
        sa.Column("enabled", sa.Boolean, server_default="1"))


def downgrade():
    op.drop_table("samba_shares")
