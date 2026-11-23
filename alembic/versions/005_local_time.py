"""created_at ni UTC dan mahalliy vaqtga o'tkazish

`created_at` `datetime.utcnow()` bilan yozilardi (naive UTC), holbuki
`transaction_time` parserlardan naive MAHALLIY vaqt sifatida kelardi. Ikkalasi
`coalesce()` bilan aralashtirilgani uchun tartib ham, davr filtri ham siljigan
edi. Endi butun jadvalda vaqt mahalliy.

Revision ID: 005
Revises: 004
Create Date: 2026-09-02

"""
from typing import Sequence, Union
from zoneinfo import ZoneInfo

import sqlalchemy as sa

from alembic import op
from app.config import settings

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timezone() -> str:
    # Nom yaroqli ekanini shu yerda tekshiramiz: u SQL matniga qo'shiladi va
    # xato yozuv migratsiyani tushunarsiz xato bilan yiqitardi.
    name = settings.TIMEZONE
    ZoneInfo(name)
    return name


def _convert(from_tz: str, to_tz: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # `AT TIME ZONE` faqat Postgres'da bor; lokal SQLite bilan
        # tajribalarda migratsiya shunchaki o'tkazib yuboriladi.
        return
    op.execute(
        sa.text(
            "UPDATE expenses SET created_at = "
            f"(created_at AT TIME ZONE '{from_tz}') AT TIME ZONE '{to_tz}' "
            "WHERE created_at IS NOT NULL"
        )
    )


def upgrade() -> None:
    _convert("UTC", _timezone())


def downgrade() -> None:
    _convert(_timezone(), "UTC")
