"""Add worker leases and fencing tokens.

Revision ID: 0005_job_leases
Revises: 0004_job_status_card
Create Date: 2026-10-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_job_leases"
down_revision = "0004_job_status_card"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("lease_owner", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("lease_token", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("heartbeat_at")
        batch.drop_column("lease_expires_at")
        batch.drop_column("lease_token")
        batch.drop_column("lease_owner")
