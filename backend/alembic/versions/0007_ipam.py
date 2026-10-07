"""0007 IPAM — ipam_networks, ipam_hosts."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("ipam_networks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64), unique=True, index=True),
        sa.Column("cidr", sa.String(32)),
        sa.Column("gateway", sa.String(64), server_default=""),
        sa.Column("vlan", sa.Integer, server_default="0"),
        sa.Column("description", sa.String(255), server_default=""))
    op.create_table("ipam_hosts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("network_id", sa.Integer, sa.ForeignKey("ipam_networks.id", ondelete="CASCADE"), index=True),
        sa.Column("ip", sa.String(64), index=True),
        sa.Column("mac", sa.String(32), server_default=""),
        sa.Column("hostname", sa.String(255), server_default=""),
        sa.Column("kind", sa.String(16), server_default="static"))


def downgrade():
    op.drop_table("ipam_hosts")
    op.drop_table("ipam_networks")
