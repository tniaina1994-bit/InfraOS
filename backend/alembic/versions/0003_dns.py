"""0003 DNS — dns_zones, dns_records."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("dns_zones",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), unique=True, index=True),
        sa.Column("kind", sa.String(16), server_default="master"),
        sa.Column("reverse", sa.Boolean, server_default="0"),
        sa.Column("ttl", sa.Integer, server_default="3600"),
        sa.Column("forwarders", sa.Text, server_default="[]"),
        sa.Column("enabled", sa.Boolean, server_default="1"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()))
    op.create_table("dns_records",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("zone_id", sa.Integer, sa.ForeignKey("dns_zones.id", ondelete="CASCADE"), index=True),
        sa.Column("name", sa.String(255)),
        sa.Column("rtype", sa.String(16), index=True),
        sa.Column("value", sa.Text),
        sa.Column("priority", sa.Integer, server_default="0"),
        sa.Column("ttl", sa.Integer, server_default="0"))


def downgrade():
    op.drop_table("dns_records")
    op.drop_table("dns_zones")
