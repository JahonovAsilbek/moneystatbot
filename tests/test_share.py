"""💰 Ulush kiritish."""
from decimal import Decimal

import pytest

from app.handlers.share import parse_share_input

TOTAL = Decimal("300000")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("100000", 100000),
        ("100 000", 100000),
        ("100.000", 100000),  # ← regressiya: avval 100 bo'lardi
        ("100,000", 100000),
        ("/3", 100000),
        ("/2", 150000),
        ("-200000", 100000),  # qaytarilgan pulni ayirish
        ("-200 000", 100000),
        ("40%", 120000),
        ("300000", 300000),   # ulush = jami, ruxsat etiladi
    ],
)
def test_accepted(raw, expected):
    value, error = parse_share_input(raw, TOTAL)
    assert error is None and value == expected


@pytest.mark.parametrize("raw", ["350000", "0", "/0", "/abc", "abc", "150%", "", "-400000"])
def test_rejected(raw):
    value, error = parse_share_input(raw, TOTAL)
    assert value is None and error
