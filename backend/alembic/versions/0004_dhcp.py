"""0004 DHCP (Kea) — dhcp_scopes, dhcp_reservations."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("dhcp_scopes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64), unique=True, index=True),
        sa.Column("subnet", sa.String(32)),
        sa.Column("pool_start", sa.String(64)),
        sa.Column("pool_end", sa.String(64)),
        sa.Column("gateway", sa.String(64), server_default=""),
        sa.Column("dns", sa.Text, server_default="[]"),
        sa.Column("domain", sa.String(255), server_default=""),
        sa.Column("lease_valid", sa.Integer, server_default="3600"),
        sa.Column("lease_max", sa.Integer, server_default="7200"),
        sa.Column("enabled", sa.Boolean, server_default="1"))
    op.create_table("dhcp_reservations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("scope_id", sa.Integer, sa.ForeignKey("dhcp_scopes.id", ondelete="CASCADE"), index=True),
        sa.Column("mac", sa.String(32), index=True),
        sa.Column("ip", sa.String(64)),
        sa.Column("hostname", sa.String(255), server_default=""))


def downgrade():
    op.drop_table("dhcp_reservations")
    op.drop_table("dhcp_scopes")
