"""Summani matndan o'qish.

Asosiy regressiya: `100.000` ilgari `Decimal("100.000")` = **100** bo'lardi.
Humo botining o'zi summani `18.483,00` ko'rinishida yozadi, ya'ni foydalanuvchi
nuqta bilan yozishga o'rganadi va bot 100 000 o'rniga 100 so'mni saqlab
qo'yardi — hech qanday xato belgisisiz.
"""
import pytest

from app.utils.money import (
    format_amount,
    parse_amount,
    parse_people_count,
    parse_percent,
    round_som,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("150000", 150000),
        ("150 000", 150000),
        ("100.000", 100000),   # ← regressiya: avval 100 bo'lardi
        ("100,000", 100000),   # ← regressiya: avval 100 bo'lardi
        ("1.234.567", 1234567),
        ("1 234 567", 1234567),
        ("18.483,00", 18483),  # Humo formati
        ("150 000.00", 150000),  # UzCard formati
        ("1500.50", 1501),     # haqiqiy kasr — butun so'mgacha yaxlitlanadi
        ("1500,5", 1501),
    ],
)
def test_parse_amount_ok(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "0", "-500", "2e5", "abc", "100.0000", ".123", "1.2.3", "1234.567", "12,345,6"],
)
def test_parse_amount_rejects(raw):
    assert parse_amount(raw) is None


@pytest.mark.parametrize("raw,expected", [("3", 3), ("10", 10)])
def test_people_count_ok(raw, expected):
    assert parse_people_count(raw) == expected


@pytest.mark.parametrize("raw", ["0", "-1", "abc", "3.5", ""])
def test_people_count_rejects(raw):
    assert parse_people_count(raw) is None


def test_percent():
    assert parse_percent("40") == 40
    assert parse_percent("40,5") == pytest.approx(40.5)
    assert parse_percent("150") is None
    assert parse_percent("0") is None


def test_round_som_is_half_up():
    """Bot va Mini App bir xil yaxlitlashi kerak.

    Mini App tomonida `quantize(Decimal("1"))` ishlatilardi — u standart
    ROUND_HALF_EVEN rejimida ishlaydi va 2.5 ni 2 ga aylantiradi.
    """
    from decimal import Decimal

    assert round_som(Decimal("2.5")) == 3
    assert round_som(Decimal("3.5")) == 4


def test_format_amount():
    assert format_amount(1234567) == "1 234 567"
    assert format_amount(0) == "0"
