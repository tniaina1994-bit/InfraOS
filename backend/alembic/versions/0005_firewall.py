"""0005 Firewall (nftables) — firewall_rules."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("firewall_rules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64)),
        sa.Column("chain", sa.String(16), server_default="input"),
        sa.Column("action", sa.String(16), server_default="accept"),
        sa.Column("proto", sa.String(8), server_default="all"),
        sa.Column("src", sa.String(64), server_default=""),
        sa.Column("dst", sa.String(64), server_default=""),
        sa.Column("dport", sa.Integer, server_default="0"),
        sa.Column("in_if", sa.String(32), server_default=""),
        sa.Column("out_if", sa.String(32), server_default=""),
        sa.Column("nat_to", sa.String(64), server_default=""),
        sa.Column("log", sa.Boolean, server_default="0"),
        sa.Column("position", sa.Integer, server_default="100"),
        sa.Column("enabled", sa.Boolean, server_default="1"))


def downgrade():
    op.drop_table("firewall_rules")
