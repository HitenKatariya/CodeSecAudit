"""Alter reviews.risk_score to Float for CVSS-style 0.0-10.0 scoring.

Revision ID: 003_alter_risk_score_to_float
Revises: 002_add_finding_status
Create Date: 2026-10-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "003_alter_risk_score_to_float"
down_revision = "002_add_finding_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "reviews",
        "risk_score",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using="risk_score::double precision",
    )


def downgrade() -> None:
    op.alter_column(
        "reviews",
        "risk_score",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
