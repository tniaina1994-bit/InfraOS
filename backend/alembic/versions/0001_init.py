"""0001 schema initial — users/groups/audit_events/jobs (sqlite+postgres)."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), unique=True, index=True),
        sa.Column("password_hash", sa.String(256)),
        sa.Column("role", sa.String(16), server_default="viewer"),
        sa.Column("display_name", sa.String(128), server_default=""),
        sa.Column("disabled", sa.Boolean, server_default="0"),
        sa.Column("auth_source", sa.String(16), server_default="local"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()))
    op.create_table("groups",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64), unique=True, index=True),
        sa.Column("description", sa.String(256), server_default=""))
    op.create_table("audit_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ts", sa.DateTime, server_default=sa.func.now(), index=True),
        sa.Column("actor", sa.String(64), server_default="system"),
        sa.Column("action", sa.String(128)),
        sa.Column("detail", sa.Text, server_default=""))
    op.create_table("jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("kind", sa.String(64), index=True),
        sa.Column("payload", sa.Text, server_default="{}"),
        sa.Column("status", sa.String(16), server_default="queued"),
        sa.Column("result", sa.Text, server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()))


def downgrade():
    for t in ("jobs", "audit_events", "groups", "users"):
        op.drop_table(t)
