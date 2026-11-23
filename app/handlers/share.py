"""💰 Ulush — umumiy to'lovdan faqat o'z qismini xarajatga yozish.

Masalan: kafeda 300 000 so'mni siz to'lab yubordingiz, keyin 3 kishi bo'lishdingiz
va do'stlar o'z qismini qaytarishdi. Statistikaga faqat 100 000 tushishi kerak,
lekin asl to'lov ham yo'qolmasligi kerak — u `original_amount` da saqlanadi.

Ikkita joydan ochiladi:
  ctx="p" — 🏷 Kategoriyalash oqimi (pending xarajat)
  ctx="m" — ✏️ O'zgartirish oqimi (saqlangan xarajat)
"""
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.db.base import async_session
from app.handlers.manage import show_expense_card
from app.handlers.pending import send_pending_card_by_id
from app.handlers.start import MAIN_MENU_TEXTS
from app.keyboards.share import get_share_keyboard, share_of
from app.services import expense as expense_service
from app.states.share import ShareFlow, clear_share_state
from app.utils.money import (
    format_amount,
    parse_amount,
    parse_people_count,
    parse_percent,
    round_som,
)

router = Router()

CTX_PENDING = "p"
CTX_MANAGE = "m"

_INPUT_HELP = (
    "Quyidagicha yozishingiz mumkin:\n"
    "• <code>100000</code> — ulushingiz shu summa\n"
    "• <code>/3</code> — jamini 3 kishiga teng bo'lish\n"
    "• <code>-200000</code> — qaytarilgan pulni ayirish\n"
    "• <code>40%</code> — jamining 40 foizi"
)


def parse_share_input(raw: str, total: Decimal) -> tuple[Decimal | None, str | None]:
    """Foydalanuvchi kiritgan matndan ulush summasini hisoblaydi.

    Qaytaradi: (summa, None) yoki (None, xato matni).
    """
    text = (raw or "").strip()
    if not text:
        return None, f"❌ Summani tushunmadim.\n\n{_INPUT_HELP}"

    # Summa `app.utils.money.parse_amount` orqali o'qiladi: u `100.000` ni
    # 100 emas, 100 000 deb tushunadi (Humo botining o'zi summani shu
    # ko'rinishda yozadi, ya'ni foydalanuvchi shunday yozishga o'rganadi).
    if text.startswith("/"):
        people = parse_people_count(text[1:])
        if people is None:
            return None, "❌ Kishilar soni butun musbat son bo'lishi kerak, masalan <code>/3</code>."
        value = Decimal(total) / people
    elif text.startswith("-"):
        returned = parse_amount(text[1:])
        if returned is None:
            return None, f"❌ Summani tushunmadim.\n\n{_INPUT_HELP}"
        value = Decimal(total) - returned
    elif text.endswith("%"):
        percent = parse_percent(text[:-1])
        if percent is None:
            return None, "❌ Foiz 0 dan katta, 100 dan katta bo'lmasligi kerak, masalan <code>40%</code>."
        value = Decimal(total) * percent / Decimal(100)
    else:
        value = parse_amount(text)
        if value is None:
            return None, f"❌ Summani tushunmadim.\n\n{_INPUT_HELP}"

    value = round_som(value)

    if value <= 0:
        return None, "❌ Ulush 0 dan katta bo'lishi kerak."
    if value > Decimal(total):
        return None, (
            f"❌ Ulush jami to'lovdan ({format_amount(total)} UZS) katta bo'lolmaydi.\n"
            "Summani butunlay o'zgartirmoqchi bo'lsangiz — ✏️ O'zgartirish → Tahrirlash → Summa."
        )
    return value, None


def _parse_cb(data: str) -> tuple[str, int]:
    """'sh:p:42' → ('p', 42)"""
    parts = data.split(":")
    return parts[1], int(parts[2])


def _share_screen_text(expense) -> str:
    total = expense.original_amount or expense.amount
    text = f"💰 Ulush ajratish\n\n🧾 Jami to'lov: {format_amount(total)} UZS\n"
    text += f"🏪 {expense.merchant or '-'}\n"
    if expense.original_amount is not None:
        text += f"\n✅ Hozirgi ulushingiz: {format_amount(expense.amount)} UZS\n"
    text += "\nXarajatga faqat o'z ulushingiz yoziladi.\nNecha kishi bo'lishdi?"
    return text


async def _return_to_ctx(target, ctx: str, expense_id: int, edit: bool) -> None:
    if ctx == CTX_MANAGE:
        await show_expense_card(target, expense_id, edit=edit)
    else:
        await send_pending_card_by_id(target, expense_id, edit=edit)


# ---- Ulush ekranini ochish (sh:<ctx>:<id>) ----

@router.callback_query(F.data.startswith("sh:"))
async def open_share(callback: CallbackQuery) -> None:
    ctx, expense_id = _parse_cb(callback.data)

    async with async_session() as session:
        expense = await expense_service.get_expense_by_id(session, expense_id)

    if not expense:
        await callback.answer("❌ Xarajat topilmadi", show_alert=True)
        return

    total = expense.original_amount or expense.amount
    await callback.message.edit_text(
        _share_screen_text(expense),
        reply_markup=get_share_keyboard(
            ctx, expense_id, total, expense.original_amount is not None
        ),
    )
    await callback.answer()


# ---- Tez bo'lish (shn:<ctx>:<id>:<kishi>) ----

@router.callback_query(F.data.startswith("shn:"))
async def apply_split(callback: CallbackQuery, state: FSMContext) -> None:
    ctx, expense_id = _parse_cb(callback.data)
    people = int(callback.data.split(":")[3])

    async with async_session() as session:
        expense = await expense_service.get_expense_by_id(session, expense_id)
        if not expense:
            await callback.answer("❌ Xarajat topilmadi", show_alert=True)
            return
        total = expense.original_amount or expense.amount
        await expense_service.set_share(session, expense_id, share_of(total, people))

    await clear_share_state(state)
    await callback.answer(f"✅ {people} kishiga bo'lindi")
    await _return_to_ctx(callback, ctx, expense_id, edit=True)


# ---- Qo'lda kiritish (shm:<ctx>:<id>) ----

@router.callback_query(F.data.startswith("shm:"))
async def ask_share_amount(callback: CallbackQuery, state: FSMContext) -> None:
    ctx, expense_id = _parse_cb(callback.data)

    async with async_session() as session:
        expense = await expense_service.get_expense_by_id(session, expense_id)

    if not expense:
        await callback.answer("❌ Xarajat topilmadi", show_alert=True)
        return

    total = expense.original_amount or expense.amount
    await state.update_data(share_expense_id=expense_id, share_ctx=ctx)
    await state.set_state(ShareFlow.waiting_share)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Orqaga", callback_data=f"shb:{ctx}:{expense_id}")]
        ]
    )
    await callback.message.edit_text(
        f"✏️ O'z ulushingizni kiriting.\n\n"
        f"🧾 Jami: {format_amount(total)} UZS\n\n"
        f"{_INPUT_HELP}",
        reply_markup=kb,
    )
    await callback.answer()


@router.message(
    ShareFlow.waiting_share,
    ~F.forward_origin,
    ~F.text.in_(MAIN_MENU_TEXTS),
    ~F.text.regexp(r"^/[a-zA-Z]"),
)
async def handle_share_amount(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    expense_id = data.get("share_expense_id")
    ctx = data.get("share_ctx", CTX_PENDING)

    async with async_session() as session:
        expense = await expense_service.get_expense_by_id(session, expense_id)

    if not expense:
        await state.set_state(None)
        await message.answer("❌ Xarajat topilmadi.")
        return

    total = expense.original_amount or expense.amount
    value, error = parse_share_input(message.text or "", total)
    if value is None:
        await message.answer(error)  # holatda qolamiz — qayta urinib ko'rish mumkin
        return

    async with async_session() as session:
        await expense_service.set_share(session, expense_id, value)

    await state.set_state(None)
    await message.answer(
        f"✅ Ulushingiz: {format_amount(value)} UZS\n"
        f"🧾 Jami to'lov: {format_amount(total)} UZS"
    )
    await _return_to_ctx(message, ctx, expense_id, edit=False)


# ---- Asl summani qaytarish (shr:<ctx>:<id>) ----

@router.callback_query(F.data.startswith("shr:"))
async def reset_share(callback: CallbackQuery, state: FSMContext) -> None:
    ctx, expense_id = _parse_cb(callback.data)

    async with async_session() as session:
        await expense_service.reset_share(session, expense_id)

    await clear_share_state(state)
    await callback.answer("🔄 Asl summa qaytarildi")
    await _return_to_ctx(callback, ctx, expense_id, edit=True)


# ---- Orqaga (shb:<ctx>:<id>) ----

@router.callback_query(F.data.startswith("shb:"))
async def back_from_share(callback: CallbackQuery, state: FSMContext) -> None:
    ctx, expense_id = _parse_cb(callback.data)
    await clear_share_state(state)
    await _return_to_ctx(callback, ctx, expense_id, edit=True)
    await callback.answer()
