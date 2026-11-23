"""initial

Revision ID: 001
Revises:
Create Date: 2026-03-05

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("merchant", sa.String(length=255), nullable=True),
        sa.Column("card_type", sa.String(length=10), nullable=True),
        sa.Column("card_last4", sa.String(length=10), nullable=True),
        sa.Column("balance_after", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("transaction_time", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expenses_user_time", "expenses", ["user_id", "transaction_time"])


def downgrade() -> None:
    op.drop_index("ix_expenses_user_time", table_name="expenses")
    op.drop_table("expenses")
