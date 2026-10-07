"""0002 identity avancee — user_groups, groups.role, sessions."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("groups", sa.Column("role", sa.String(16), server_default="viewer"))
    op.create_table("user_groups",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("group_id", sa.Integer, sa.ForeignKey("groups.id", ondelete="CASCADE"), index=True),
        sa.UniqueConstraint("user_id", "group_id", name="uq_user_group"))
    op.create_table("sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("jti", sa.String(64), unique=True, index=True),
        sa.Column("username", sa.String(64), index=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime),
        sa.Column("revoked", sa.Boolean, server_default="0"))


def downgrade():
    op.drop_table("sessions")
    op.drop_table("user_groups")
    op.drop_column("groups", "role")
