"""Persist Telegram custom emoji set mappings.

Revision ID: 0006_emoji_sets
Revises: 0005_job_leases
Create Date: 2026-10-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_emoji_sets"
down_revision = "0005_job_leases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emoji_sets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id"), nullable=False),
        sa.Column("set_name", sa.String(length=128), nullable=False, unique=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )
    op.create_table(
        "emoji_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("emoji_set_id", sa.Integer(), sa.ForeignKey("emoji_sets.id"), nullable=False),
        sa.Column("tile_hash", sa.String(length=64), nullable=False),
        sa.Column("custom_emoji_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.UniqueConstraint("emoji_set_id", "tile_hash", name="uq_emoji_items_set_hash"),
    )


def downgrade() -> None:
    op.drop_table("emoji_items")
    op.drop_table("emoji_sets")
