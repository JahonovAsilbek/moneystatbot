"""💰 Ulush klaviaturasi — umumiy to'lovdan o'z qismini ajratish."""
from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.money import format_amount, round_som

# Tez tanlash uchun odam sonlari
QUICK_SPLITS = (2, 3, 4, 5)


def share_of(total, people: int) -> Decimal:
    """Jami summani `people` kishiga teng bo'ladi (butun so'mgacha yaxlitlab)."""
    return round_som(Decimal(total) / Decimal(people))


def get_share_keyboard(
    ctx: str, expense_id: int, total, has_share: bool
) -> InlineKeyboardMarkup:
    """ctx: 'p' — kategoriyalash oqimi, 'm' — tahrirlash oqimi."""
    buttons = []
    row = []
    for people in QUICK_SPLITS:
        row.append(
            InlineKeyboardButton(
                text=f"{people} kishi · {format_amount(share_of(total, people))}",
                callback_data=f"shn:{ctx}:{expense_id}:{people}",
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append(
        [
            InlineKeyboardButton(
                text="✏️ Qo'lda kiritish", callback_data=f"shm:{ctx}:{expense_id}"
            )
        ]
    )
    if has_share:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔄 Asl summani qaytarish",
                    callback_data=f"shr:{ctx}:{expense_id}",
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="↩️ Orqaga", callback_data=f"shb:{ctx}:{expense_id}")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)
