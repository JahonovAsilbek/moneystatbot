"""Davr chegaralari — statistika, ro'yxat va PDF uchun yagona qoida.

Ilgari bu funksiya `services/expense.py` va `services/stats.py` da so'zma-so'z
takrorlangan edi, ya'ni birini tuzatib ikkinchisini unutish oson edi.
"""
from datetime import date, datetime, time, timedelta

from app.utils.time import now

DEFAULT_PERIOD = "1m"
DATE_FORMAT = "%Y-%m-%d"


def period_start(period: str) -> datetime:
    current = now()
    if period == "1d":
        return current - timedelta(days=1)
    if period == "3d":
        return current - timedelta(days=3)
    if period == "7d":
        return current - timedelta(days=7)
    if period == "this_month":
        return current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period == "1m":
        return current - timedelta(days=30)
    return current - timedelta(days=30)


def parse_date(value: str | None) -> date | None:
    """`YYYY-MM-DD` -> date. Bo'sh bo'lsa None, noto'g'ri bo'lsa ValueError."""
    if not value:
        return None
    return datetime.strptime(value.strip(), DATE_FORMAT).date()


def resolve_range(
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[datetime, datetime | None]:
    """Filtr uchun (boshlanish, tugash) chegaralari.

    Tugash — ochiq chegara (`< end`), shuning uchun foydalanuvchi tanlagan
    oxirgi kun to'liq kiradi: keyingi kunning 00:00 iga aylantiriladi.

    Sana berilgan bo'lsa u tayyor davrdan ustun turadi. Faqat bittasi berilsa
    ikkinchi tomon ochiq qoladi ("1-avgustdan buyon" yoki "15-avgustgacha").
    Sanalar teskari kelsa o'rin almashtiriladi.
    """
    start_date = parse_date(date_from)
    end_date = parse_date(date_to)

    if start_date and end_date and end_date < start_date:
        start_date, end_date = end_date, start_date

    if start_date:
        start = datetime.combine(start_date, time.min)
    elif end_date:
        start = datetime.min  # faqat "gacha" berilgan — quyi chegara ochiq
    else:
        start = period_start(period or DEFAULT_PERIOD)

    end = datetime.combine(end_date + timedelta(days=1), time.min) if end_date else None
    return start, end
