from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PERIODS = [
    ("1 kun", "1d"),
    ("3 kun", "3d"),
    ("7 kun", "7d"),
    ("Shu oy", "this_month"),
    ("Oxirgi 1 oy", "1m"),
]


def get_period_keyboard(prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for label, value in PERIODS:
        row.append(InlineKeyboardButton(text=label, callback_data=f"{prefix}:{value}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)
