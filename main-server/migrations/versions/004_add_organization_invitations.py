"""Add organization_invitations table.

Revision ID: 004_add_organization_invitations
Revises: 003_alter_risk_score_to_float
Create Date: 2026-11-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "004_add_organization_invitations"
down_revision = "003_alter_risk_score_to_float"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_invitations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), default="developer", nullable=False),
        sa.Column("token", sa.String(128), unique=True, nullable=False),
        sa.Column("invited_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), default="pending", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_org_invitations_org_id", "organization_invitations", ["organization_id"])
    op.create_index("idx_org_invitations_token", "organization_invitations", ["token"], unique=True)
    op.create_index("idx_org_invitations_email", "organization_invitations", ["email"])
    op.create_index("idx_org_invitations_status", "organization_invitations", ["status"])


def downgrade() -> None:
    op.drop_table("organization_invitations")
