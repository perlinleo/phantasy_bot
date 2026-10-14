"""Make draft confirmation idempotent.

Revision ID: 0010_job_submission_key
Revises: 0009_job_progress_fraction
Create Date: 2026-10-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_job_submission_key"
down_revision = "0009_job_progress_fraction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("submission_key", sa.String(length=80), nullable=True))
        batch.create_unique_constraint("uq_jobs_submission_key", ["submission_key"])


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.drop_constraint("uq_jobs_submission_key", type_="unique")
        batch.drop_column("submission_key")
