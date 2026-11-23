from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.parsers.humo import parse_humo
from app.parsers.uzcard import parse_uzcard


@dataclass
class ParsedTransaction:
    amount: Decimal
    is_income: bool = False
    merchant: str | None = None
    card_type: str | None = None
    card_last4: str | None = None
    transaction_time: datetime | None = None
    balance_after: Decimal | None = None


def parse_message(text: str) -> ParsedTransaction | None:
    result = parse_humo(text)
    if result:
        return result
    return parse_uzcard(text)
