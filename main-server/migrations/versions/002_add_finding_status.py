"""Add findings.status (open/resolved/ignored) - the model already declared
this column (app/db/models/review.py) but no migration created it, so any
insert or select against findings on a real Postgres database was broken.

Revision ID: 002_add_finding_status
Revises: 001_initial_schema
Create Date: 2026-10-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "002_add_finding_status"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "findings",
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
    )
    op.create_index("idx_findings_status", "findings", ["status"])


def downgrade() -> None:
    op.drop_index("idx_findings_status", table_name="findings")
    op.drop_column("findings", "status")
