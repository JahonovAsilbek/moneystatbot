"""Sana oralig'i va kategoriya bo'yicha filtrlash (Mini App uchun)."""
from datetime import datetime
from decimal import Decimal

import pytest

from app.services import expense as svc
from app.services import stats as stats_svc
from app.services.periods import resolve_range
from tests.conftest import OWNER_ID

# ---- resolve_range ----

def test_explicit_range_is_inclusive_on_both_ends():
    """Foydalanuvchi uchun `to` oxirgi kunni ham qamrab olishi kerak."""
    start, end = resolve_range(None, "2026-08-01", "2026-08-31")
    assert start == datetime(2026, 8, 1, 0, 0)
    assert end == datetime(2026, 9, 1, 0, 0)  # ochiq chegara -> 31-avgust to'liq kiradi


def test_only_from_leaves_upper_bound_open():
    start, end = resolve_range(None, "2026-08-01", None)
    assert start == datetime(2026, 8, 1, 0, 0) and end is None


def test_only_to_leaves_lower_bound_open():
    start, end = resolve_range(None, None, "2026-08-15")
    assert start == datetime.min and end == datetime(2026, 8, 16, 0, 0)


def test_reversed_dates_are_swapped():
    a = resolve_range(None, "2026-08-31", "2026-08-01")
    b = resolve_range(None, "2026-08-01", "2026-08-31")
    assert a == b


def test_dates_win_over_period():
    start, _ = resolve_range("1d", "2026-01-01", None)
    assert start == datetime(2026, 1, 1, 0, 0)


def test_period_used_when_no_dates():
    start, end = resolve_range("this_month", None, None)
    assert start.day == 1 and end is None


@pytest.mark.parametrize("bad", ["2026-13-01", "01.08.2026", "kecha", "2026-08-32"])
def test_invalid_date_raises(bad):
    with pytest.raises(ValueError):
        resolve_range(None, bad, None)


# ---- filtrlangan so'rovlar ----

async def _seed(session):
    rows = [
        ("2026-08-05", "Transport", 10000),
        ("2026-08-20", "Transport", 20000),
        ("2026-09-02", "Transport", 30000),
        ("2026-08-10", "Oziq-ovqat", 40000),
        ("2026-08-31", None, 50000),  # kategoriyalanmagan
    ]
    for day, cat, amount in rows:
        await svc.create_expense(
            session, user_id=OWNER_ID, amount=Decimal(amount), category=cat,
            transaction_time=datetime.fromisoformat(day + "T12:00"),
        )


async def test_range_filters_expenses(session):
    await _seed(session)
    start, end = resolve_range(None, "2026-08-01", "2026-08-31")
    rows = await svc.get_expenses(session, OWNER_ID, start=start, end=end)
    assert sorted(int(r.amount) for r in rows) == [10000, 20000, 40000, 50000]
    # 31-avgustdagi yozuv kiradi, 2-sentabrdagi kirmaydi
    assert 30000 not in [int(r.amount) for r in rows]


async def test_category_filter(session):
    await _seed(session)
    start, end = resolve_range(None, "2026-08-01", "2026-09-30")
    rows = await svc.get_expenses(session, OWNER_ID, start=start, end=end, category="Transport")
    assert sorted(int(r.amount) for r in rows) == [10000, 20000, 30000]


async def test_uncategorized_filter(session):
    await _seed(session)
    start, end = resolve_range(None, "2026-08-01", "2026-09-30")
    rows = await svc.get_expenses(session, OWNER_ID, start=start, end=end, only_uncategorized=True)
    assert [int(r.amount) for r in rows] == [50000]


async def test_stats_respect_range(session):
    await _seed(session)
    start, end = resolve_range(None, "2026-08-01", "2026-08-31")
    rows = await stats_svc.get_category_stats(session, OWNER_ID, start=start, end=end)
    by_cat = {cat: int(amount) for cat, amount in rows}
    assert by_cat == {"Transport": 30000, "Oziq-ovqat": 40000, None: 50000}
