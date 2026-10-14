"""Add persistent access requests.

Revision ID: 0007_access_requests
Revises: 0006_emoji_sets
Create Date: 2026-10-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_access_requests"
down_revision = "0006_emoji_sets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "access_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.telegram_id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )


def downgrade() -> None:
    op.drop_table("access_requests")
