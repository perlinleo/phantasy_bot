"""Add delivery recovery metadata.

Revision ID: 0008_delivery_recovery
Revises: 0007_access_requests
Create Date: 2026-10-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_delivery_recovery"
down_revision = "0007_access_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("deliveries", sa.Column("next_attempt_at", sa.DateTime(timezone=True)))
    op.add_column("deliveries", sa.Column("sending_started_at", sa.DateTime(timezone=True)))
    op.add_column("deliveries", sa.Column("error_message", sa.Text()))


def downgrade() -> None:
    op.drop_column("deliveries", "error_message")
    op.drop_column("deliveries", "sending_started_at")
    op.drop_column("deliveries", "next_attempt_at")
