"""0011 Backup — backup_jobs, backup_runs."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("backup_jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64), unique=True, index=True),
        sa.Column("backend", sa.String(16), server_default="restic"),
        sa.Column("repo", sa.String(255)),
        sa.Column("sources", sa.Text, server_default="[]"),
        sa.Column("schedule", sa.String(64), server_default=""),
        sa.Column("retention", sa.String(255), server_default="--keep-daily 7 --keep-weekly 4"),
        sa.Column("encrypted", sa.Boolean, server_default="1"),
        sa.Column("enabled", sa.Boolean, server_default="1"))
    op.create_table("backup_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("backup_jobs.id", ondelete="CASCADE"), index=True),
        sa.Column("status", sa.String(16), server_default="running"),
        sa.Column("log", sa.Text, server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime, nullable=True))


def downgrade():
    op.drop_table("backup_runs")
    op.drop_table("backup_jobs")
