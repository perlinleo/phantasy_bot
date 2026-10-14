"""Persist draft options and delivery status message.

Revision ID: 0003_draft_options_progress
Revises: 0002_jobs
Create Date: 2026-10-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_draft_options_progress"
down_revision = "0002_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("drafts") as batch:
        batch.add_column(sa.Column("options_json", sa.Text(), nullable=False, server_default="{}"))
        batch.add_column(
            sa.Column("mode", sa.String(length=16), nullable=False, server_default="input")
        )
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("options_json", sa.Text(), nullable=False, server_default="{}"))
    with op.batch_alter_table("deliveries") as batch:
        batch.add_column(sa.Column("status_message_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("deliveries") as batch:
        batch.drop_column("status_message_id")
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("options_json")
    with op.batch_alter_table("drafts") as batch:
        batch.drop_column("mode")
        batch.drop_column("options_json")
