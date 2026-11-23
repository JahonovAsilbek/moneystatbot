"""category nullable (pending), source column, settings table

Revision ID: 003
Revises: 002
Create Date: 2026-07-19

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Kategoriya endi NULL bo'lishi mumkin (pending = kategoriyalanmagan)
    op.alter_column("expenses", "category", existing_type=sa.String(length=50), nullable=True)
    # Manba ustuni
    op.add_column("expenses", sa.Column("source", sa.String(length=20), nullable=True))

    # Kalit-qiymat sozlamalar jadvali
    op.create_table(
        "settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_column("expenses", "source")
    # category'ni qayta NOT NULL qilishdan oldin mavjud NULL'larni 'Boshqa' bilan to'ldiramiz
    op.execute("UPDATE expenses SET category = 'Boshqa' WHERE category IS NULL")
    op.alter_column("expenses", "category", existing_type=sa.String(length=50), nullable=False)
