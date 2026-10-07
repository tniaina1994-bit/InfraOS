"""0013 RBAC en base — roles, permissions, user_roles, modules, settings."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("roles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(32), unique=True, index=True),
        sa.Column("rank", sa.Integer, server_default="0"),
        sa.Column("description", sa.String(255), server_default=""))
    op.create_table("permissions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64), unique=True, index=True),
        sa.Column("description", sa.String(255), server_default=""))
    op.create_table("role_permissions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id", ondelete="CASCADE"), index=True),
        sa.Column("permission_id", sa.Integer, sa.ForeignKey("permissions.id", ondelete="CASCADE"), index=True),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_perm"))
    op.create_table("user_roles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id", ondelete="CASCADE"), index=True),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role"))
    op.create_table("modules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64), unique=True, index=True),
        sa.Column("version", sa.String(32), server_default=""),
        sa.Column("enabled", sa.Boolean, server_default="1"))
    op.create_table("module_dependencies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("module_id", sa.Integer, sa.ForeignKey("modules.id", ondelete="CASCADE"), index=True),
        sa.Column("depends_on", sa.String(64)))
    op.create_table("system_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(128), unique=True, index=True),
        sa.Column("value", sa.Text, server_default=""),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()))


def downgrade():
    for t in ("system_settings", "module_dependencies", "modules",
              "user_roles", "role_permissions", "permissions", "roles"):
        op.drop_table(t)
