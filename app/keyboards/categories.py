from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.models import Category

CATEGORY_EMOJI = {
    "Oziq-ovqat": "🍽",
    "Transport": "🚗",
    "Kommunal": "🏠",
    "Kiyim": "👕",
    "Sog'liqni saqlash": "💊",
    "Ta'lim": "📚",
    "Ko'ngilochar": "🎮",
    "Uy-ro'zg'or": "🛒",
    "Telefon": "📱",
    "Qarz berish": "🤝",
    "Naqdlashtirish": "💵",
    "Boshqa": "📦",
}

CATEGORY_LIST = [c.value for c in Category]

# Kategoriyalanmagan xarajatlar statistikada shu nom bilan ko'rinadi.
# Ilgari ular `None` bo'lib chiqardi va ekranda "🏷 None: 250 000 UZS" deb
# yozilardi (Mini App'da esa `null`).
UNCATEGORIZED_LABEL = "Kategoriyalanmagan"
UNCATEGORIZED_EMOJI = "❓"


def get_category_label(cat: str) -> str:
    emoji = CATEGORY_EMOJI.get(cat, "")
    return f"{emoji} {cat}"


def get_pending_category_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    """Pending xarajatni kategoriyalash uchun (callback: pcat:<id>:<cat>).

    Kategoriyalar ostida qo'shimcha amallar: ulush ajratish va o'chirish.
    """
    buttons = []
    row = []
    for cat in CATEGORY_LIST:
        row.append(
            InlineKeyboardButton(
                text=get_category_label(cat), callback_data=f"pcat:{expense_id}:{cat}"
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append(
        [
            InlineKeyboardButton(text="💰 Ulush", callback_data=f"sh:p:{expense_id}"),
            InlineKeyboardButton(
                text="🗑 O'chirish", callback_data=f"pdel:{expense_id}"
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)
