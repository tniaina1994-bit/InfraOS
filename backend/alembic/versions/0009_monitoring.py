"""0009 Monitoring — monitoring_samples, monitoring_agents."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("monitoring_samples",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("host", sa.String(128), server_default="local", index=True),
        sa.Column("cpu", sa.Integer, server_default="0"),
        sa.Column("mem", sa.Integer, server_default="0"),
        sa.Column("disk", sa.Integer, server_default="0"),
        sa.Column("load1", sa.String(16), server_default=""),
        sa.Column("net_rx", sa.Integer, server_default="0"),
        sa.Column("net_tx", sa.Integer, server_default="0"),
        sa.Column("uptime", sa.Integer, server_default="0"),
        sa.Column("temp", sa.String(16), server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), index=True))
    op.create_table("monitoring_agents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("hostname", sa.String(128), unique=True, index=True),
        sa.Column("os", sa.String(64), server_default=""),
        sa.Column("token", sa.String(128), server_default=""),
        sa.Column("last_seen", sa.DateTime, nullable=True))


def downgrade():
    op.drop_table("monitoring_agents")
    op.drop_table("monitoring_samples")
