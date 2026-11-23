from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Expense
from app.services.expense import sort_column
from app.services.periods import DEFAULT_PERIOD, period_start


async def get_category_stats(
    session: AsyncSession,
    user_id: int,
    period: str | None = None,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[tuple[str | None, Decimal]]:
    """Kategoriyalar kesimida jami summa.

    Kategoriyalanmagan xarajatlar ham qaytariladi (`category` = None) — ularni
    yashirish pulni ko'rinmas qilib qo'yardi. Ekranga chiqarishda
    `UNCATEGORIZED_LABEL` bilan nomlanadi.
    """
    if start is None:
        start = period_start(period or DEFAULT_PERIOD)

    stmt = select(Expense.category, func.sum(Expense.amount)).where(
        Expense.user_id == user_id, sort_column() >= start
    )
    if end is not None:
        stmt = stmt.where(sort_column() < end)

    stmt = stmt.group_by(Expense.category).order_by(func.sum(Expense.amount).desc())
    result = await session.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]
