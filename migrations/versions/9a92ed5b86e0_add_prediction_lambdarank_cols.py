"""add prediction lambdarank columns

Revision ID: 9a92ed5b86e0
Revises: 0159350f2302
Create Date: 2026-04-26 21:30:00.000000

Phase 2: store LightGBM lambdarank outputs alongside the AutoGluon
``prob`` column. ``prob_top3`` mirrors ``prob`` for backward-compat
but allows different model versions to fill it independently.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a92ed5b86e0"
down_revision: Union[str, Sequence[str], None] = "0159350f2302"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("prediction", schema=None) as batch_op:
        batch_op.add_column(sa.Column("prob_win", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("prob_top2", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("prob_top3", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("lambdarank_score", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("prediction", schema=None) as batch_op:
        batch_op.drop_column("lambdarank_score")
        batch_op.drop_column("prob_top3")
        batch_op.drop_column("prob_top2")
        batch_op.drop_column("prob_win")
