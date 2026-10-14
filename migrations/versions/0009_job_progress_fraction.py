"""Persist measured job progress.

Revision ID: 0009_job_progress_fraction
Revises: 0008_delivery_recovery
Create Date: 2026-10-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_job_progress_fraction"
down_revision = "0008_delivery_recovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("fraction", sa.Float()))


def downgrade() -> None:
    op.drop_column("jobs", "fraction")
