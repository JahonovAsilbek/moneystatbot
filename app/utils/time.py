"""Vaqt bilan ishlash — yagona qoida.

Bazada vaqt **naive va mahalliy** (`TIMEZONE`) saqlanadi.

Ilgari bitta jadvalda ikki xil vaqt aralashardi:

* `transaction_time` — parserlardan kelgan naive **Toshkent** vaqti
* `created_at` — `datetime.utcnow()`, ya'ni naive **UTC**

Ular `coalesce()` bilan birlashtirilib tartiblanardi, davr filtri esa
`created_at` bilan solishtirilardi. Ikki oqibati bor edi:

1. Tartib 5 soatga siljigan bo'lardi (manbaga qarab).
2. "Shu oy" chegarasi UTC'da hisoblanardi: oyning 1-sanasida 00:00–05:00
   orasida statistika **o'tgan oyni** ko'rsatardi.

Qo'shimcha: `datetime.utcnow()` Python 3.12 dan beri eskirgan.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings


def tz() -> ZoneInfo:
    return ZoneInfo(settings.TIMEZONE)


def now() -> datetime:
    """Mahalliy vaqt, naive — bazadagi ustunlar ham naive."""
    return datetime.now(tz()).replace(tzinfo=None)
