"""Parserlarning umumiy yordamchilari.

Asosiy g'oya: qaysi qatorda nima turishiga qat'iy bog'lanmaslik.

Ilgari vaqt ham, balans ham qat'iy qator raqamidan olinardi. Merchant nomi
ikki qatorga bo'linganda (uzun nomlar — `PAYME UZ` + `TOSHKENT SH.`) undan
keyingi hamma narsa bir qatorga suriladi va vaqt topilmay qolardi. Natija
xavfli edi: summa to'g'ri o'qilardi, ya'ni xabar "muvaffaqiyatli" parse
bo'lgandek ko'rinardi, lekin `transaction_time=NULL` bo'lgani uchun dublikat
tekshiruvi ham o'chib ketardi va aynan o'sha xabarlar takroran yozilardi.
"""
import re
from datetime import datetime

# UzCard: `05.03.26 14:23`
_DATE_FIRST = re.compile(r"(\d{2}\.\d{2}\.\d{2,4})\s+(\d{2}:\d{2})")
# Humo: `14:23 05.03.2026`
_TIME_FIRST = re.compile(r"(\d{2}:\d{2})\s+(\d{2}\.\d{2}\.\d{2,4})")


def split_lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").strip().splitlines() if line.strip()]


def _to_datetime(date_str: str, time_str: str) -> datetime | None:
    fmt = "%d.%m.%Y" if len(date_str) == 10 else "%d.%m.%y"
    try:
        return datetime.strptime(f"{date_str} {time_str}", f"{fmt} %H:%M")
    except ValueError:
        return None


def find_transaction_time(lines: list[str]) -> tuple[datetime | None, int | None]:
    """Vaqtni butun xabar bo'ylab qidiradi. (vaqt, qator indeksi) qaytaradi."""
    for idx, line in enumerate(lines):
        match = _DATE_FIRST.search(line)
        if match:
            dt = _to_datetime(match.group(1), match.group(2))
            if dt:
                return dt, idx
        match = _TIME_FIRST.search(line)
        if match:
            dt = _to_datetime(match.group(2), match.group(1))
            if dt:
                return dt, idx
    return None, None


def find_value_after(
    lines: list[str], after_index: int | None, pattern: re.Pattern
) -> str | None:
    """Berilgan qatordan KEYIN birinchi uchragan summani qaytaradi.

    Balans har doim vaqtdan keyin turadi. Oxiridan qidirish o'rniga aynan shu
    tartibga tayanamiz — aks holda Humo'dagi komissiya qatori balans deb
    o'qilib qolishi mumkin edi.
    """
    if after_index is None:
        return None
    for line in lines[after_index + 1:]:
        match = pattern.search(line)
        if match:
            return match.group(1)
    return None


def join_merchant(
    lines: list[str],
    start: int,
    end: int | None,
    skip: re.Pattern | None = None,
) -> str | None:
    """`start` dan `end` gacha bo'lgan qatorlarni merchant nomi sifatida birlashtiradi."""
    if start >= len(lines):
        return None
    stop = end if end is not None and end > start else start + 1
    parts = [
        re.sub(r"^📍\s*", "", line).strip()
        for line in lines[start:stop]
        if not (skip and skip.search(line))
    ]
    merchant = " ".join(part for part in parts if part)
    return merchant or None
