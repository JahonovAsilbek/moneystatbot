from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.parsers.common import (
    find_transaction_time,
    find_value_after,
    join_merchant,
    split_lines,
)
from app.utils.money import parse_amount

if TYPE_CHECKING:
    from app.parsers.base import ParsedTransaction

# Humo formati: nuqta — ming ajratuvchi, vergul — o'nlik. Tiyin ixtiyoriy.
_AMOUNT_RE = re.compile(r"[➖➕]\s*([\d.]+(?:,\d{2})?)\s*UZS")
_VALUE_RE = re.compile(r"([\d.]+(?:,\d{2})?)\s*UZS")
_CARD_RE = re.compile(r"HUMOCARD\s*\*?(\d+)", re.IGNORECASE)


def parse_humo(text: str) -> ParsedTransaction | None:
    lines = split_lines(text)
    if len(lines) < 6:
        return None

    if not any("HUMOCARD" in line.upper() for line in lines):
        return None

    # 2-qator: summa (➖ yoki ➕ bilan)
    amount_line = lines[1]
    if "➖" not in amount_line and "➕" not in amount_line:
        return None

    amount_match = _AMOUNT_RE.search(amount_line)
    if not amount_match:
        return None

    amount = parse_amount(amount_match.group(1))
    if amount is None:
        return None

    is_income = "➕" in amount_line

    # 3-qator: komissiya (e'tiborsiz qoldiramiz)

    card_match = next(
        (m for m in (_CARD_RE.search(line) for line in lines) if m), None
    )
    transaction_time, time_index = find_transaction_time(lines)
    merchant = join_merchant(lines, 3, time_index, skip=_CARD_RE)

    balance_raw = find_value_after(lines, time_index, _VALUE_RE)
    balance_after = parse_amount(balance_raw) if balance_raw else None

    from app.parsers.base import ParsedTransaction

    return ParsedTransaction(
        amount=amount,
        is_income=is_income,
        merchant=merchant,
        card_type="humo",
        card_last4=card_match.group(1) if card_match else None,
        transaction_time=transaction_time,
        balance_after=balance_after,
    )
