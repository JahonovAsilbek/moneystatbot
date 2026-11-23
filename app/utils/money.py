"""Summani matndan o'qish — butun loyiha uchun yagona joy.

Muammo: O'zbekistonda ming ajratuvchi sifatida bo'sh joy ham, nuqta ham,
vergul ham ishlatiladi — Humo botining o'zi summani `18.483,00` deb yozadi.
Ilgari har uchala kirish yo'li (ulush, qo'lda summa, tahrirlash) matnni
shunchaki `Decimal` ga berardi, natijada:

    Decimal("100.000") == 100

ya'ni foydalanuvchi 100 000 yozmoqchi bo'lib 100 so'mni saqlab qo'yardi va
buni keyin sezardi. Pul ilovasida jim noto'g'ri raqam — eng yomon nosozlik.

Qoida: ajratuvchidan keyin roppa-rosa 3 ta raqam kelsa, u ming ajratuvchi.
1-2 ta raqam kelsa — kasr belgisi. Qolgan hollarda taxmin qilinmaydi, xato
qaytariladi. UZS da tiyin muomalada yo'q, shuning uchun natija butun son.
"""
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# Harf, eksponenta (`2e5`), ishora — hech biri qabul qilinmaydi
_ALLOWED = re.compile(r"^[\d\s., ]+$")
_COUNT = re.compile(r"^\d{1,3}$")
_PERCENT = re.compile(r"^\d{1,3}(?:[.,]\d{1,2})?$")


def _thousands_ok(text: str, sep: str) -> bool:
    """`1.234.567` — to'g'ri; `1.23.456`, `.123`, `1234.567` — noto'g'ri."""
    head, *rest = text.split(sep)
    return bool(head) and len(head) <= 3 and all(len(part) == 3 for part in rest)


def parse_amount(raw: str) -> Decimal | None:
    """Matndan summani o'qiydi. Tushunarsiz yoki musbat bo'lmasa — None."""
    text = (raw or "").replace(" ", " ").strip()
    if not text or not _ALLOWED.match(text):
        return None

    text = text.replace(" ", "")
    if not text.strip(".,"):  # faqat ajratuvchilardan iborat
        return None

    dots, commas = text.count("."), text.count(",")

    if dots and commas:
        # Ikkalasi ham bor: oxirgi kelgani — kasr belgisi (`18.483,00`)
        dec_sep = "." if text.rfind(".") > text.rfind(",") else ","
        thou_sep = "," if dec_sep == "." else "."
        if text.count(dec_sep) != 1:
            return None
        head, tail = text.split(dec_sep)
        if not _thousands_ok(head, thou_sep) or not 1 <= len(tail) <= 2:
            return None
        text = head.replace(thou_sep, "") + "." + tail

    elif dots or commas:
        sep = "." if dots else ","
        parts = text.split(sep)
        if len(parts) > 2 or len(parts[-1]) == 3:
            # Bir nechta ajratuvchi yoki keyin roppa-rosa 3 raqam -> ming
            if not _thousands_ok(text, sep):
                return None
            text = text.replace(sep, "")
        elif len(parts[-1]) in (1, 2):
            text = text.replace(sep, ".")  # kasr
        else:
            return None

    try:
        value = Decimal(text)
    except InvalidOperation:
        return None

    if value <= 0:
        return None
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def parse_people_count(raw: str) -> int | None:
    """`/3` dagi kishilar soni."""
    text = (raw or "").replace(" ", " ").replace(" ", "").strip()
    if not _COUNT.match(text):
        return None
    count = int(text)
    return count if count > 0 else None


def parse_percent(raw: str) -> Decimal | None:
    """`40%` dagi foiz (0 dan katta, 100 dan katta emas)."""
    text = (raw or "").replace(" ", " ").replace(" ", "").strip().replace(",", ".")
    if not _PERCENT.match(text):
        return None
    value = Decimal(text)
    return value if 0 < value <= 100 else None


def format_amount(amount) -> str:
    """`150000` -> `150 000`. Ilgari bu funksiya 9 ta faylda takrorlangan edi."""
    return f"{float(amount):,.0f}".replace(",", " ")


def round_som(value: Decimal) -> Decimal:
    """Butun so'mgacha yaxlitlash — hamma joyda bir xil qoida bilan."""
    return Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
