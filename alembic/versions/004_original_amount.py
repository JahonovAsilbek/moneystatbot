"""original_amount — ulush ajratilganda asl (umumiy) to'lov summasi

Revision ID: 004
Revises: 003
Create Date: 2026-08-07

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "expenses",
        sa.Column("original_amount", sa.Numeric(precision=15, scale=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("expenses", "original_amount")
