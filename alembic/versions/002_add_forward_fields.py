"""add forward_chat_id and forward_message_id

Revision ID: 002
Revises: 001
Create Date: 2026-03-05

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("expenses", sa.Column("forward_chat_id", sa.BigInteger(), nullable=True))
    op.add_column("expenses", sa.Column("forward_message_id", sa.BigInteger(), nullable=True))
    op.create_index(
        "ix_expenses_forward",
        "expenses",
        ["forward_chat_id", "forward_message_id"],
        unique=True,
        postgresql_where=sa.text("forward_chat_id IS NOT NULL AND forward_message_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_expenses_forward", table_name="expenses")
    op.drop_column("expenses", "forward_message_id")
    op.drop_column("expenses", "forward_chat_id")
