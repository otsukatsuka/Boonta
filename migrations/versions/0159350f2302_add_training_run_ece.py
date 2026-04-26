"""add training_run.ece column

Revision ID: 0159350f2302
Revises: d332999781bf
Create Date: 2026-04-26 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0159350f2302"
down_revision: Union[str, Sequence[str], None] = "d332999781bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ECE (expected calibration error) column to training_run."""
    with op.batch_alter_table("training_run", schema=None) as batch_op:
        batch_op.add_column(sa.Column("ece", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("training_run", schema=None) as batch_op:
        batch_op.drop_column("ece")
