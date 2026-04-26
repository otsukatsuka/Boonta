"""add race_odds / cyb_record / kka_record tables

Revision ID: 6db0c37d9bc1
Revises: 9a92ed5b86e0
Create Date: 2026-04-26 22:00:00.000000

Phase 3: pre-race combination odds (OW/OU/OT) + per-horse training analysis
(CYB) + extended past-race summary (KKA).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6db0c37d9bc1"
down_revision: Union[str, Sequence[str], None] = "9a92ed5b86e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "race_odds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("race_id", sa.Integer(), nullable=False),
        sa.Column("head_count", sa.Integer(), nullable=True),
        sa.Column("wide", sa.JSON(), nullable=True),
        sa.Column("umatan", sa.JSON(), nullable=True),
        sa.Column("sanrenpuku", sa.JSON(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["race_id"], ["race.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("race_id"),
    )

    op.create_table(
        "cyb_record",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("horse_entry_id", sa.Integer(), nullable=False),
        sa.Column("finish_index", sa.Integer(), nullable=True),
        sa.Column("chase_index", sa.Integer(), nullable=True),
        sa.Column("training_eval", sa.String(length=2), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["horse_entry_id"], ["horse_entry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("horse_entry_id"),
    )

    op.create_table(
        "kka_record",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("horse_entry_id", sa.Integer(), nullable=False),
        sa.Column("raw", sa.JSON(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["horse_entry_id"], ["horse_entry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("horse_entry_id"),
    )


def downgrade() -> None:
    op.drop_table("kka_record")
    op.drop_table("cyb_record")
    op.drop_table("race_odds")
