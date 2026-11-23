"""Davr chegaralari va vaqt zonasi.

Regressiya: `created_at` `utcnow()` bilan yozilardi, `transaction_time` esa
mahalliy vaqt edi. "Shu oy" chegarasi UTC'da hisoblangani uchun oyning
1-sanasida 00:00–05:00 orasida statistika o'tgan oyni ko'rsatardi.
"""
from datetime import datetime, timezone

from app.services.periods import period_start
from app.utils.time import now


def test_now_is_local_not_utc():
    delta = (now() - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds()
    assert round(delta / 3600) == 5, "Asia/Tashkent = UTC+5"


def test_this_month_uses_local_calendar():
    start = period_start("this_month")
    local = now()
    assert (start.year, start.month, start.day) == (local.year, local.month, 1)
    assert (start.hour, start.minute, start.second) == (0, 0, 0)


def test_relative_periods():
    # `now()` test ichida va `period_start` ichida alohida chaqiriladi,
    # shuning uchun mikrosoniyalik farqni yaxlitlaymiz.
    def days_back(period):
        return round((now() - period_start(period)).total_seconds() / 86400)

    assert days_back("1d") == 1
    assert days_back("3d") == 3
    assert days_back("7d") == 7
    assert days_back("1m") == 30
    assert days_back("nomalum") == 30  # noma'lum davr -> standart 30 kun
