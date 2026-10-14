"""Store Telegram progress-card message on jobs.

Revision ID: 0004_job_status_card
Revises: 0003_draft_options_progress
Create Date: 2026-10-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_job_status_card"
down_revision = "0003_draft_options_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("status_message_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("status_message_id")
