from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.config import settings
from app.db.base import async_session
from app.services import expense as expense_service
from app.utils.money import format_amount

router = Router()

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Xarajatlar"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📥 Fayl yuklash"), KeyboardButton(text="✏️ O'zgartirish")],
        [KeyboardButton(text="🏷 Kategoriyalash"), KeyboardButton(text="🕐 So'nggi xarajat")],
        [KeyboardButton(text="⚙️ Sozlamalar")],
    ],
    resize_keyboard=True,
)

# Menyu tugmalarining matnlari — holat filtrlari va MenuResetMiddleware shu
# ro'yxatga tayanadi, ya'ni yangi tugma qo'shilsa ular o'zi qamrab oladi.
MAIN_MENU_TEXTS = [button.text for row in MAIN_MENU.keyboard for button in row]


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Salom! Men sizning xarajatlaringizni kuzatuvchi botman.\n\n"
        "📲 UzCard yoki Humo botidan kelgan tranzaksiya xabarini menga forward qiling.",
        reply_markup=MAIN_MENU,
    )


@router.message(F.text == "🕐 So'nggi xarajat")
async def handle_latest_expense(message: Message) -> None:
    async with async_session() as session:
        expense = await expense_service.get_latest_expense(session, settings.OWNER_ID)

    if not expense:
        await message.answer("📭 Hali xarajatlar yo'q.")
        return

    date = expense.transaction_time or expense.created_at
    date_str = date.strftime("%d.%m.%Y %H:%M") if date else "—"

    total_line = ""
    if expense.original_amount is not None:
        total_line = f"🧾 Jami to'lov: {format_amount(expense.original_amount)} UZS\n"

    text = (
        f"🕐 So'nggi xarajat:\n\n"
        f"📅 {date_str}\n"
        f"💰 {format_amount(expense.amount)} UZS\n"
        f"{total_line}"
        f"🏷 {expense.category or '— (kategoriyalanmagan)'}\n"
        f"🏪 {expense.merchant or '-'}\n"
        f"💳 {expense.card_type or '-'} *{expense.card_last4 or '?'}"
    )
    if expense.balance_after:
        text += f"\n💵 Balans: {format_amount(expense.balance_after)} UZS"

    await message.answer(text)
