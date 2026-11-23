"""Xarajat servisi: dublikat aniqlash, ulush, sahifalash tartibi."""
from datetime import datetime, timedelta
from decimal import Decimal

from app.services import expense as svc
from tests.conftest import OWNER_ID

TIME = datetime(2026, 3, 5, 14, 23)


async def _add(session, amount, **kw):
    kw.setdefault("category", "Transport")
    kw.setdefault("user_id", OWNER_ID)
    return await svc.create_expense(session, amount=Decimal(str(amount)), **kw)


# ---- dublikat ----

async def test_duplicate_by_amount_and_time(session):
    await _add(session, 150000, transaction_time=TIME, merchant="KORZINKA")
    assert await svc.is_duplicate_by_content(session, Decimal("150000"), TIME)
    assert not await svc.is_duplicate_by_content(
        session, Decimal("150000"), TIME + timedelta(minutes=1)
    )


async def test_duplicate_matches_original_amount(session):
    """Ulush ajratilganda `amount` kamayadi — asl summa bo'yicha ham topilsin."""
    await _add(
        session, 100000, original_amount=Decimal("300000"),
        transaction_time=TIME, merchant="KAFE",
    )
    assert await svc.is_duplicate_by_content(session, Decimal("300000"), TIME)


async def test_duplicate_without_time(session):
    """Regressiya: vaqt yo'q bo'lsa tekshiruv butunlay o'chib qolardi."""
    await _add(session, 42000, transaction_time=None, merchant="PAYME", category=None)
    assert await svc.is_duplicate_by_content(session, Decimal("42000"), None, "PAYME")
    assert not await svc.is_duplicate_by_content(session, Decimal("42000"), None, "CLICK")
    assert not await svc.is_duplicate_by_content(session, Decimal("999"), None, "PAYME")


async def test_same_amount_same_minute_different_balance_is_not_duplicate(session):
    """Regressiya: metroda ikki kishi uchun ketma-ket to'lov.

    Summa ham, daqiqa ham bir xil — ilgari ikkinchisi jimgina tashlab
    yuborilardi. Balans har xil bo'lgani uchun bu ikki alohida to'lov.
    """
    await _add(session, 1700, transaction_time=TIME, balance_after=Decimal("50000"))
    assert not await svc.is_duplicate_by_content(
        session, Decimal("1700"), TIME, balance_after=Decimal("48300")
    )
    # Aynan o'sha xabarning ikkinchi nusxasi — balans ham bir xil
    assert await svc.is_duplicate_by_content(
        session, Decimal("1700"), TIME, balance_after=Decimal("50000")
    )


async def test_duplicate_when_stored_balance_unknown(session):
    """Saqlangan yozuvda balans yo'q bo'lsa — eski qoida (summa + vaqt)."""
    await _add(session, 1700, transaction_time=TIME, balance_after=None)
    assert await svc.is_duplicate_by_content(
        session, Decimal("1700"), TIME, balance_after=Decimal("48300")
    )


async def test_duplicate_without_time_respects_balance(session):
    await _add(session, 42000, transaction_time=None, merchant="PAYME",
               category=None, balance_after=Decimal("100000"))
    assert not await svc.is_duplicate_by_content(
        session, Decimal("42000"), None, "PAYME", balance_after=Decimal("58000")
    )
    assert await svc.is_duplicate_by_content(
        session, Decimal("42000"), None, "PAYME", balance_after=Decimal("100000")
    )


# ---- ulush ----

async def test_set_and_reset_share(session):
    exp = await _add(session, 300000, transaction_time=TIME)
    await svc.set_share(session, exp.id, Decimal("100000"))
    exp = await svc.get_expense_by_id(session, exp.id)
    assert (exp.amount, exp.original_amount) == (100000, 300000)

    # Qayta bo'lish har doim ASL summadan hisoblanadi
    await svc.set_share(session, exp.id, Decimal("75000"))
    exp = await svc.get_expense_by_id(session, exp.id)
    assert (exp.amount, exp.original_amount) == (75000, 300000)

    await svc.reset_share(session, exp.id)
    exp = await svc.get_expense_by_id(session, exp.id)
    assert (exp.amount, exp.original_amount) == (300000, None)


async def test_share_equal_to_total_clears_split(session):
    exp = await _add(session, 300000, transaction_time=TIME)
    await svc.set_share(session, exp.id, Decimal("300000"))
    exp = await svc.get_expense_by_id(session, exp.id)
    assert exp.original_amount is None


# ---- sahifalash ----

async def test_paging_is_stable_with_equal_timestamps(session):
    """Regressiya: teng vaqtli yozuvlarda ajratuvchi yo'q edi.

    Parserlar vaqtni daqiqa aniqligida beradi, ya'ni tenglik nodir hol emas.
    Barqaror tartibsiz bitta yozuv ikki sahifada chiqishi yoki umuman tushib
    qolishi mumkin edi.
    """
    for i in range(15):
        await _add(session, 1000 + i, transaction_time=TIME)

    page0, total_pages = await svc.get_expenses_page(session, OWNER_ID, 0)
    page1, _ = await svc.get_expenses_page(session, OWNER_ID, 1)
    ids = [e.id for e in page0] + [e.id for e in page1]

    assert total_pages == 2
    assert len(ids) == 15
    assert len(set(ids)) == 15, "yozuv takrorlandi yoki tushib qoldi"


async def test_pending_helpers(session):
    await _add(session, 1000, category=None, transaction_time=TIME)
    await _add(session, 2000, category="Transport", transaction_time=TIME)
    assert await svc.count_pending(session, OWNER_ID) == 1
    assert (await svc.get_next_pending(session, OWNER_ID)).amount == 1000
