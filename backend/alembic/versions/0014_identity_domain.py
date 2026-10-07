"""0014 Identity & Domain — table identity_domains (Samba AD DC)."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("identity_domains",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("realm", sa.String(255), unique=True, index=True),
        sa.Column("netbios", sa.String(15), server_default=""),
        sa.Column("dc_hostname", sa.String(64), server_default=""),
        sa.Column("dc_fqdn", sa.String(255), server_default=""),
        sa.Column("dc_ip", sa.String(45), server_default=""),
        sa.Column("dns_backend", sa.String(32), server_default="SAMBA_INTERNAL"),
        sa.Column("status", sa.String(16), server_default="provisioning"),
        sa.Column("admin_user", sa.String(64), server_default="Administrator"),
        sa.Column("hosts_written", sa.Boolean, server_default=sa.false()),
        sa.Column("krb5_written", sa.Boolean, server_default=sa.false()),
        sa.Column("named_stopped", sa.Boolean, server_default=sa.false()),
        sa.Column("provisioned_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.String(64), server_default=""))


def downgrade():
    op.drop_table("identity_domains")
