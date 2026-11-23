"""Kategoriyalanmagan (pending) xarajatlarni bittalab kategoriyalash oqimi."""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.config import settings
from app.db.base import async_session
from app.db.models import Category, Expense
from app.keyboards.categories import get_pending_category_keyboard
from app.services import expense as expense_service
from app.states.share import clear_share_state
from app.utils.money import format_amount

router = Router()


def _format_expense_body(exp: Expense) -> str:
    date = exp.transaction_time or exp.created_at
    date_str = date.strftime("%d.%m.%Y %H:%M") if date else "—"
    text = f"📅 {date_str}\n💰 {format_amount(exp.amount)} UZS"
    if exp.original_amount is not None:
        text += f"\n🧾 Jami to'lov: {format_amount(exp.original_amount)} UZS"
    text += (
        f"\n🏪 {exp.merchant or '-'}"
        f"\n💳 {exp.card_type or '-'} *{exp.card_last4 or '?'}"
    )
    if exp.balance_after is not None:
        text += f"\n💵 Balans: {format_amount(exp.balance_after)} UZS"
    return text


def _format_pending(exp: Expense, remaining: int) -> str:
    return (
        f"🏷 Kategoriyalash  ({remaining} ta qoldi)\n\n"
        f"{_format_expense_body(exp)}\n\n"
        "🏷 Kategoriyani tanlang:"
    )


def _responder(target, edit: bool):
    """CallbackQuery/Message uchun mos yuborish funksiyasi."""
    if isinstance(target, CallbackQuery):
        return target.message.edit_text if edit else target.message.answer
    return target.answer


async def send_pending_card(target, expense: Expense, remaining: int, edit: bool) -> None:
    """AYNAN shu xarajatning kategoriyalash kartochkasini ko'rsatadi.

    Tugmalarga xarajat `id` si yoziladi, shuning uchun bir vaqtda bir nechta
    kartochka ochiq turishi xavfsiz — har biri o'z yozuviga tegadi.
    """
    await _responder(target, edit)(
        _format_pending(expense, remaining),
        reply_markup=get_pending_category_keyboard(expense.id),
    )


async def send_pending_card_by_id(target, expense_id: int, edit: bool) -> None:
    """Aynan shu xarajatning kartochkasi.

    Yozuv o'chirilgan yoki allaqachon kategoriyalangan bo'lsa — keyingisiga
    o'tadi. Ulush ekranidan "Orqaga" bosilganda ilgari eng yangi pending
    ko'rsatilardi, ya'ni foydalanuvchi boshqa yozuvga tushib qolishi mumkin edi.
    """
    async with async_session() as session:
        expense = await expense_service.get_expense_by_id(session, expense_id)
        remaining = await expense_service.count_pending(session, settings.OWNER_ID)

    if expense is None or expense.category is not None:
        await send_next_pending(target, edit)
        return

    await send_pending_card(target, expense, remaining, edit)


async def send_next_pending(target, edit: bool) -> None:
    """Keyingi pending'ni ko'rsatadi. edit=True bo'lsa mavjud xabarni tahrirlaydi."""
    async with async_session() as session:
        exp = await expense_service.get_next_pending(session, settings.OWNER_ID)
        remaining = await expense_service.count_pending(session, settings.OWNER_ID)

    if not exp:
        await _responder(target, edit)("✅ Barcha xarajatlar kategoriyalangan! 🎉")
        return

    await send_pending_card(target, exp, remaining, edit)


# ---- 🏷 Kategoriyalash (menyu tugmasi) ----

@router.message(F.text == "🏷 Kategoriyalash")
async def handle_categorize_button(message: Message, state: FSMContext) -> None:
    await clear_share_state(state)
    await send_next_pending(message, edit=False)


# ---- Eslatmadagi tugma ----

@router.callback_query(F.data == "pending_start")
async def handle_pending_start(callback: CallbackQuery, state: FSMContext) -> None:
    await clear_share_state(state)
    await send_next_pending(callback, edit=True)
    await callback.answer()


# ---- Kategoriya tanlash (pcat:<id>:<cat>) ----

@router.callback_query(F.data.startswith("pcat:"))
async def handle_pending_category(callback: CallbackQuery) -> None:
    parts = callback.data.split(":", 2)
    expense_id = int(parts[1])
    category = parts[2]

    if category not in {c.value for c in Category}:
        await callback.answer("Noto'g'ri kategoriya")
        return

    async with async_session() as session:
        expense = await expense_service.get_expense_by_id(session, expense_id)
        if expense is None:
            await callback.answer("❌ Xarajat topilmadi", show_alert=True)
            await send_next_pending(callback, edit=True)
            return
        # Ekranda bir nechta kartochka ochiq turishi mumkin (bir necha forward
        # ketma-ket kelganda). Eskirgan kartochkadagi tugma allaqachon
        # tanlangan kategoriyani ustidan yozib yubormasin.
        if expense.category is not None:
            await callback.answer(
                f"ℹ️ Bu xarajat allaqachon kategoriyalangan: {expense.category}",
                show_alert=True,
            )
            await send_next_pending(callback, edit=True)
            return

        await expense_service.update_expense(session, expense_id, category=category)

    await callback.answer(f"✅ {category}")
    await send_next_pending(callback, edit=True)


# ---- O'chirish (pdel:<id> → pdelok:<id>) ----

@router.callback_query(F.data.startswith("pdel:"))
async def confirm_pending_delete(callback: CallbackQuery) -> None:
    expense_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        exp = await expense_service.get_expense_by_id(session, expense_id)

    if not exp:
        await callback.answer("❌ Xarajat topilmadi", show_alert=True)
        await send_next_pending(callback, edit=True)
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Ha, o'chirish", callback_data=f"pdelok:{expense_id}"
                ),
                InlineKeyboardButton(
                    text="↩️ Orqaga", callback_data=f"pback:{expense_id}"
                ),
            ]
        ]
    )
    await callback.message.edit_text(
        f"🗑 Bu xarajat o'chirilsinmi?\n\n{_format_expense_body(exp)}",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pback:"))
async def back_to_pending_card(callback: CallbackQuery) -> None:
    expense_id = int(callback.data.split(":")[1])
    await send_pending_card_by_id(callback, expense_id, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("pdelok:"))
async def handle_pending_delete(callback: CallbackQuery) -> None:
    expense_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        await expense_service.delete_expense(session, expense_id)

    await callback.answer("🗑 O'chirildi")
    await send_next_pending(callback, edit=True)
