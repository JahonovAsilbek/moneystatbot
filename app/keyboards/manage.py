from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.models import Category
from app.keyboards.categories import get_category_label


def get_expense_actions_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Ulush ajratish", callback_data=f"sh:m:{expense_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Tahrirlash", callback_data=f"edit_exp:{expense_id}"
                ),
                InlineKeyboardButton(
                    text="🗑 O'chirish", callback_data=f"del_exp:{expense_id}"
                ),
            ],
        ]
    )


def get_confirm_delete_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Ha, o'chirish", callback_data=f"confirm_del:{expense_id}"
                ),
                InlineKeyboardButton(text="Bekor qilish", callback_data="cancel_del"),
            ]
        ]
    )


def get_edit_field_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Summa", callback_data=f"edit_amount:{expense_id}"
                ),
                InlineKeyboardButton(
                    text="Kategoriya", callback_data=f"edit_cat:{expense_id}"
                ),
            ],
            [
                InlineKeyboardButton(text="Bekor qilish", callback_data="cancel_edit"),
            ],
        ]
    )


def get_edit_category_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for cat in Category:
        row.append(
            InlineKeyboardButton(
                text=get_category_label(cat.value), callback_data=f"set_cat:{expense_id}:{cat.value}"
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)
