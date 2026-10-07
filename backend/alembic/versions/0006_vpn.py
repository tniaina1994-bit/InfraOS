"""0006 VPN (WireGuard) — vpn_servers, vpn_peers."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("vpn_servers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(32), unique=True, index=True),
        sa.Column("address", sa.String(64)),
        sa.Column("port", sa.Integer, server_default="51820"),
        sa.Column("private_key", sa.String(128), server_default=""),
        sa.Column("enabled", sa.Boolean, server_default="1"))
    op.create_table("vpn_peers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("server_id", sa.Integer, sa.ForeignKey("vpn_servers.id", ondelete="CASCADE"), index=True),
        sa.Column("name", sa.String(64)),
        sa.Column("public_key", sa.String(128)),
        sa.Column("preshared_key", sa.String(128), server_default=""),
        sa.Column("allowed_ips", sa.String(255), server_default=""),
        sa.Column("endpoint", sa.String(128), server_default=""),
        sa.Column("keepalive", sa.Integer, server_default="25"))


def downgrade():
    op.drop_table("vpn_peers")
    op.drop_table("vpn_servers")
