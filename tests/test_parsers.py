"""Bank xabarlarini parse qilish.

Regressiyalar:

* Merchant nomi ikki qatorga bo'linganda vaqt ham, balans ham yo'qolardi.
  Xavflisi shundaki, summa to'g'ri o'qilardi — ya'ni xabar "muvaffaqiyatli"
  parse bo'lgandek ko'rinardi — lekin `transaction_time=NULL` bo'lgani uchun
  dublikat tekshiruvi butunlay o'chib ketardi.
* Tiyinsiz summa (`➖ 150 000 UZS`) umuman parse bo'lmasdi va userbot uni
  jimgina tashlab yuborardi.
"""
import pytest

from app.parsers.base import parse_message

UZCARD = """💳 UZCARD
➖ 150 000.00 UZS
***4321
📍 KORZINKA TASHKENT
05.03.26 14:23
Balans: 1 250 000.00 UZS"""

HUMO = """💳 HUMO
➖ 18.483,00 UZS
Komissiya: 0,00 UZS
📍 OASIS SUPERMARKET
HUMOCARD *1234
14:23 05.03.2026
Balans: 1.250.000,00 UZS"""


def test_uzcard():
    tx = parse_message(UZCARD)
    assert tx.card_type == "uzcard"
    assert tx.amount == 150000
    assert tx.merchant == "KORZINKA TASHKENT"
    assert tx.card_last4 == "4321"
    assert (tx.transaction_time.day, tx.transaction_time.hour) == (5, 14)
    assert tx.balance_after == 1250000
    assert tx.is_income is False


def test_humo():
    tx = parse_message(HUMO)
    assert tx.card_type == "humo"
    assert tx.amount == 18483
    assert tx.merchant == "OASIS SUPERMARKET"
    assert tx.card_last4 == "1234"
    assert tx.balance_after == 1250000


def test_income_flagged():
    assert parse_message(UZCARD.replace("➖", "➕")).is_income is True


@pytest.mark.parametrize("text", ["", "salom qalaysan", "bitta\nikkita\nuchta"])
def test_garbage_rejected(text):
    assert parse_message(text) is None


def test_blank_lines_ignored():
    tx = parse_message(UZCARD.replace("***4321", "***4321\n\n"))
    assert tx.amount == 150000 and tx.transaction_time is not None


@pytest.mark.parametrize(
    "text,merchant",
    [
        (UZCARD.replace("📍 KORZINKA TASHKENT", "📍 KORZINKA\nTASHKENT"), "KORZINKA TASHKENT"),
        (HUMO.replace("📍 OASIS SUPERMARKET", "📍 OASIS\nSUPERMARKET"), "OASIS SUPERMARKET"),
    ],
)
def test_multiline_merchant_keeps_time_and_balance(text, merchant):
    """Ilgari bu holatda vaqt ham, balans ham NULL bo'lib qolardi."""
    tx = parse_message(text)
    assert tx.merchant == merchant
    assert tx.transaction_time is not None, "vaqt yo'qolgan — dublikat himoyasi o'chadi"
    assert tx.balance_after == 1250000


@pytest.mark.parametrize(
    "text,amount",
    [
        (UZCARD.replace("150 000.00", "150 000"), 150000),
        (HUMO.replace("18.483,00", "18.483"), 18483),
    ],
)
def test_amount_without_decimals(text, amount):
    """Ilgari tiyinsiz summa parse bo'lmay, tranzaksiya jimgina yo'qolardi."""
    tx = parse_message(text)
    assert tx is not None and tx.amount == amount


def test_missing_balance_line_still_parses():
    tx = parse_message("\n".join(UZCARD.splitlines()[:5]))
    assert tx.amount == 150000
    assert tx.balance_after is None


def test_humo_not_parsed_as_uzcard():
    assert parse_message(HUMO).card_type == "humo"
