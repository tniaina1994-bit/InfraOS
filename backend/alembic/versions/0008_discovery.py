"""0008 Discovery — discovery_scans, discovery_hosts."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("discovery_scans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("target", sa.String(64)),
        sa.Column("profile", sa.String(16), server_default="ping"),
        sa.Column("status", sa.String(16), server_default="done"),
        sa.Column("hosts_up", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()))
    op.create_table("discovery_hosts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("scan_id", sa.Integer, sa.ForeignKey("discovery_scans.id", ondelete="CASCADE"), index=True),
        sa.Column("ip", sa.String(64), index=True),
        sa.Column("mac", sa.String(32), server_default=""),
        sa.Column("hostname", sa.String(255), server_default=""),
        sa.Column("ports", sa.Text, server_default="[]"),
        sa.Column("os", sa.String(255), server_default=""))


def downgrade():
    op.drop_table("discovery_hosts")
    op.drop_table("discovery_scans")
