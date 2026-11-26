"""Add policy_json column to organizations table.

Revision ID: 005_add_org_policy_json
Revises: 004_add_organization_invitations
Create Date: 2026-11-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "005_add_org_policy_json"
down_revision = "004_add_organization_invitations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("organizations")}
    if "policy_json" not in cols:
        op.add_column("organizations", sa.Column("policy_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "policy_json")
