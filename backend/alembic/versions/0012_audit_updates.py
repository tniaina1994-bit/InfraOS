"""0012 audit complet + historique updates."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("audit_events", sa.Column("resource", sa.String(255), server_default=""))
    op.add_column("audit_events", sa.Column("ip", sa.String(64), server_default=""))
    op.add_column("audit_events", sa.Column("result", sa.String(16), server_default="SUCCESS"))
    op.create_table("update_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("kind", sa.String(16), server_default="packages"),
        sa.Column("packages", sa.Text, server_default="[]"),
        sa.Column("status", sa.String(16), server_default="running"),
        sa.Column("log", sa.Text, server_default=""),
        sa.Column("actor", sa.String(64), server_default="system"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime, nullable=True))


def downgrade():
    op.drop_table("update_runs")
    op.drop_column("audit_events", "result")
    op.drop_column("audit_events", "ip")
    op.drop_column("audit_events", "resource")
