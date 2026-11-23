from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Expense
from app.services.periods import DEFAULT_PERIOD, period_start
from app.utils.time import now as local_now

PAGE_SIZE = 10


def sort_column():
    return func.coalesce(Expense.transaction_time, Expense.created_at)


def order_by():
    """Tartib har doim bir xil bo'lishi uchun `id` ajratuvchi sifatida qo'shiladi.

    Parserlar vaqtni daqiqa aniqligida beradi, ya'ni teng qiymatlar nodir hol
    emas (bitta do'konda ketma-ket ikki to'lov). Ajratuvchisiz Postgres teng
    qatorlarni har safar boshqa tartibda qaytarishi mumkin — OFFSET bilan
    sahifalashda bitta yozuv ikki sahifada chiqishi yoki umuman tushib qolishi
    mumkin edi.
    """
    return sort_column().desc(), Expense.id.desc()


async def is_duplicate_by_forward(
    session: AsyncSession, forward_chat_id: int, forward_message_id: int
) -> Expense | None:
    stmt = select(Expense).where(
        Expense.forward_chat_id == forward_chat_id,
        Expense.forward_message_id == forward_message_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# Tranzaksiya vaqti noma'lum bo'lganda dublikat qidiriladigan oyna.
DUPLICATE_WINDOW = timedelta(hours=6)


async def is_duplicate_by_content(
    session: AsyncSession,
    amount: Decimal,
    transaction_time: datetime | None = None,
    merchant: str | None = None,
    balance_after: Decimal | None = None,
) -> Expense | None:
    """Dublikatni mazmun bo'yicha topadi.

    Ulush ajratilgan bo'lsa `amount` kamaygan bo'ladi — shuning uchun kartadan
    chiqqan asl summa (`original_amount`) bo'yicha ham tekshiriladi.

    `transaction_time` bor bo'lsa u eng ishonchli belgi: bir xil summa bir xil
    daqiqada ikki marta chiqmaydi.

    Vaqt yo'q bo'lsa (parser uni o'qiy olmagan hollarda) tekshiruv ilgari
    BUTUNLAY o'chib qolardi va aynan o'sha xabarlar takroran yozilardi. Endi
    summa + merchant + yaqin vaqt oynasi bo'yicha qidiriladi.

    `balance_after` — haqiqiy takroriy to'lovni dublikatdan ajratadi. Ilgari
    metroda ikki kishi uchun ketma-ket to'langan 1 700 so'm bir daqiqaga
    tushardi va ikkinchisi "dublikat" deb jimgina tashlab yuborilardi. Ikki
    haqiqiy to'lovdan keyingi balans har xil, bitta xabarning ikki nusxasida
    esa bir xil. Balansi noma'lum yozuv (qo'lda kiritilgan) bilan solishtirishda
    bu belgi ishlatilmaydi.
    """
    target = Decimal(amount)
    amount_match = or_(Expense.amount == target, Expense.original_amount == target)

    if transaction_time is not None:
        stmt = select(Expense).where(
            amount_match, Expense.transaction_time == transaction_time
        )
    else:
        stmt = select(Expense).where(
            amount_match,
            Expense.transaction_time.is_(None),
            Expense.created_at >= local_now() - DUPLICATE_WINDOW,
            Expense.merchant == merchant if merchant else Expense.merchant.is_(None),
        )

    if balance_after is not None:
        stmt = stmt.where(
            or_(
                Expense.balance_after.is_(None),
                Expense.balance_after == Decimal(balance_after),
            )
        )

    result = await session.execute(stmt.limit(1))
    return result.scalar_one_or_none()


async def create_expense(session: AsyncSession, **kwargs) -> Expense:
    expense = Expense(**kwargs)
    session.add(expense)
    await session.commit()
    await session.refresh(expense)
    return expense


async def count_pending(session: AsyncSession, user_id: int) -> int:
    """Kategoriyalanmagan (category IS NULL) xarajatlar soni."""
    stmt = (
        select(func.count())
        .select_from(Expense)
        .where(Expense.user_id == user_id, Expense.category.is_(None))
    )
    return (await session.execute(stmt)).scalar() or 0


async def get_pending(session: AsyncSession, user_id: int) -> list[Expense]:
    stmt = (
        select(Expense)
        .where(Expense.user_id == user_id, Expense.category.is_(None))
        .order_by(*order_by())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_next_pending(session: AsyncSession, user_id: int) -> Expense | None:
    stmt = (
        select(Expense)
        .where(Expense.user_id == user_id, Expense.category.is_(None))
        .order_by(*order_by())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_latest_expense(session: AsyncSession, user_id: int) -> Expense | None:
    stmt = (
        select(Expense)
        .where(Expense.user_id == user_id)
        .order_by(*order_by())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_expenses(
    session: AsyncSession,
    user_id: int,
    period: str | None = None,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    category: str | None = None,
    only_uncategorized: bool = False,
) -> list[Expense]:
    """Davr yoki aniq sana oralig'i bo'yicha xarajatlar.

    Filtr tartiblash bilan bir xil ustunga tayanadi. Ilgari filtr `created_at`
    bo'yicha edi: kechagi tranzaksiyani bugun forward qilsangiz u bugungi
    statistikaga tushib ketardi.
    """
    if start is None:
        start = period_start(period or DEFAULT_PERIOD)

    stmt = select(Expense).where(Expense.user_id == user_id, sort_column() >= start)
    if end is not None:
        stmt = stmt.where(sort_column() < end)
    if only_uncategorized:
        stmt = stmt.where(Expense.category.is_(None))
    elif category:
        stmt = stmt.where(Expense.category == category)

    result = await session.execute(stmt.order_by(*order_by()))
    return list(result.scalars().all())


async def get_expenses_page(
    session: AsyncSession, user_id: int, page: int
) -> tuple[list[Expense], int]:
    """Returns (expenses, total_pages)."""
    count_stmt = select(func.count()).select_from(Expense).where(Expense.user_id == user_id)
    total = (await session.execute(count_stmt)).scalar() or 0
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    offset = page * PAGE_SIZE
    stmt = (
        select(Expense)
        .where(Expense.user_id == user_id)
        .order_by(*order_by())
        .offset(offset)
        .limit(PAGE_SIZE)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all()), total_pages


async def get_expense_by_id(session: AsyncSession, expense_id: int) -> Expense | None:
    return await session.get(Expense, expense_id)


async def update_expense(session: AsyncSession, expense_id: int, **kwargs) -> None:
    stmt = update(Expense).where(Expense.id == expense_id).values(**kwargs)
    await session.execute(stmt)
    await session.commit()


async def set_share(
    session: AsyncSession, expense_id: int, share: Decimal
) -> Expense | None:
    """Xarajatga faqat o'z ulushini yozadi, asl summani `original_amount`ga saqlaydi.

    Takror chaqirilganda asl summa o'zgarmaydi — ulush har doim asl summadan
    hisoblanadi (3 kishiga bo'lgandan keyin 4 kishiga o'zgartirish mumkin).
    """
    expense = await session.get(Expense, expense_id)
    if expense is None:
        return None

    total = expense.original_amount or expense.amount
    if Decimal(share) == Decimal(total):
        # Ulush = jami summa → bo'lish bekor qilingan hisoblanadi
        expense.original_amount = None
    else:
        expense.original_amount = total
    expense.amount = share

    await session.commit()
    await session.refresh(expense)
    return expense


async def reset_share(session: AsyncSession, expense_id: int) -> Expense | None:
    """Ulushni bekor qiladi — asl (umumiy) summani qaytaradi."""
    expense = await session.get(Expense, expense_id)
    if expense is None:
        return None

    if expense.original_amount is not None:
        expense.amount = expense.original_amount
        expense.original_amount = None
        await session.commit()
        await session.refresh(expense)
    return expense


async def delete_expense(session: AsyncSession, expense_id: int) -> None:
    stmt = delete(Expense).where(Expense.id == expense_id)
    await session.execute(stmt)
    await session.commit()
