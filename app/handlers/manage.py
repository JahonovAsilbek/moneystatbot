
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.config import settings
from app.db.base import async_session
from app.db.models import Category
from app.handlers.start import MAIN_MENU_TEXTS
from app.keyboards.manage import (
    get_confirm_delete_keyboard,
    get_edit_category_keyboard,
    get_edit_field_keyboard,
    get_expense_actions_keyboard,
)
from app.services import expense as expense_service
from app.states.share import clear_share_state
from app.utils.money import format_amount, parse_amount

router = Router()


class EditFlow(StatesGroup):
    waiting_new_amount = State()


def _build_manage_list(expenses, page: int, total_pages: int) -> tuple[str, InlineKeyboardMarkup]:
    lines = [f"✏️ Tahrirlash/O'chirish  ({page + 1}/{total_pages})\n"]
    lines.append("Tranzaksiyani tanlang:\n")

    rows = []
    for exp in expenses:
        date = exp.transaction_time or exp.created_at
        date_str = date.strftime("%d.%m") if date else "?"
        label = f"{date_str} | {format_amount(exp.amount)} | {exp.category or '❓'}"
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"manage_exp:{exp.id}")]
        )

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"mpage:{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"mpage:{page + 1}"))
    if nav_row:
        rows.append(nav_row)

    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)


# ---- ✏️ O'zgartirish ----

@router.message(F.text == "✏️ O'zgartirish")
async def handle_manage_button(message: Message, state: FSMContext) -> None:
    await clear_share_state(state)
    async with async_session() as session:
        expenses, total_pages = await expense_service.get_expenses_page(
            session, settings.OWNER_ID, 0
        )

    if not expenses:
        await message.answer("📭 Xarajatlar topilmadi.")
        return

    text, kb = _build_manage_list(expenses, 0, total_pages)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("mpage:"))
async def handle_manage_page(callback: CallbackQuery) -> None:
    page = int(callback.data.split(":")[1])

    async with async_session() as session:
        expenses, total_pages = await expense_service.get_expenses_page(
            session, settings.OWNER_ID, page
        )

    text, kb = _build_manage_list(expenses, page, total_pages)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


def format_expense_card(expense) -> str:
    date = expense.transaction_time or expense.created_at
    date_str = date.strftime("%d.%m.%Y %H:%M") if date else "—"

    text = f"📅 {date_str}\n💰 {format_amount(expense.amount)} UZS"
    if expense.original_amount is not None:
        text += f"\n🧾 Jami to'lov: {format_amount(expense.original_amount)} UZS"
    text += f"\n🏷 {expense.category or '— (kategoriyalanmagan)'}\n🏪 {expense.merchant or '-'}"
    return text


async def show_expense_card(target, expense_id: int, edit: bool = True) -> None:
    """Xarajat kartochkasi + amallar (CallbackQuery yoki Message uchun)."""
    async with async_session() as session:
        expense = await expense_service.get_expense_by_id(session, expense_id)

    if isinstance(target, CallbackQuery):
        send = target.message.edit_text if edit else target.message.answer
    else:
        send = target.answer

    if not expense:
        await send("❌ Xarajat topilmadi.")
        return

    await send(
        f"{format_expense_card(expense)}\n\nNima qilmoqchisiz?",
        reply_markup=get_expense_actions_keyboard(expense_id),
    )


@router.callback_query(F.data.startswith("manage_exp:"))
async def show_expense_actions(callback: CallbackQuery) -> None:
    expense_id = int(callback.data.split(":")[1])
    await show_expense_card(callback, expense_id)
    await callback.answer()


@router.callback_query(F.data.startswith("del_exp:"))
async def confirm_delete(callback: CallbackQuery) -> None:
    expense_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "🗑 Rostdan ham bu xarajatni o'chirmoqchimisiz?",
        reply_markup=get_confirm_delete_keyboard(expense_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_del:"))
async def handle_delete(callback: CallbackQuery) -> None:
    expense_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        await expense_service.delete_expense(session, expense_id)

    await callback.message.edit_text("✅ Xarajat o'chirildi.")
    await callback.answer()


@router.callback_query(F.data == "cancel_del")
async def cancel_delete(callback: CallbackQuery) -> None:
    await callback.message.edit_text("↩️ Bekor qilindi.")
    await callback.answer()


@router.callback_query(F.data.startswith("edit_exp:"))
async def show_edit_fields(callback: CallbackQuery) -> None:
    expense_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "✏️ Nimani o'zgartirmoqchisiz?",
        reply_markup=get_edit_field_keyboard(expense_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_amount:"))
async def ask_new_amount(callback: CallbackQuery, state: FSMContext) -> None:
    expense_id = int(callback.data.split(":")[1])
    await state.update_data(edit_expense_id=expense_id)
    await state.set_state(EditFlow.waiting_new_amount)
    await callback.message.edit_text("✏️ Yangi summani kiriting:")
    await callback.answer()


@router.message(
    EditFlow.waiting_new_amount,
    ~F.forward_origin,
    # Busiz menyu tugmalari shu handlerga tushib, "noto'g'ri summa" javobini
    # olardi va foydalanuvchi holatda tiqilib qolardi.
    ~F.text.in_(MAIN_MENU_TEXTS),
    ~F.text.regexp(r"^/[a-zA-Z]"),
)
async def handle_new_amount(message: Message, state: FSMContext) -> None:
    amount = parse_amount(message.text or "")
    if amount is None:
        await message.answer(
            "❌ Summani tushunmadim. Masalan: <code>150000</code>, "
            "<code>150 000</code> yoki <code>150.000</code>."
        )
        return

    data = await state.get_data()
    expense_id = data["edit_expense_id"]

    async with async_session() as session:
        expense = await expense_service.get_expense_by_id(session, expense_id)
        had_share = expense is not None and expense.original_amount is not None
        # Ulush eski summadan hisoblangan edi — yangi summa bilan u ma'nosiz
        # bo'lib qoladi. Ilgari `original_amount` joyida qolib, kartochkada
        # eski "Jami to'lov" ko'rinib turardi va yangi summa undan katta
        # bo'lib qolishi ham mumkin edi.
        await expense_service.update_expense(
            session, expense_id, amount=amount, original_amount=None
        )

    await state.clear()
    text = f"✅ Summa yangilandi: {format_amount(amount)} UZS"
    if had_share:
        text += "\n🧾 Ulush bekor qilindi — summa endi to'liq hisobga olinadi."
    await message.answer(text)


@router.callback_query(F.data.startswith("edit_cat:"))
async def show_edit_categories(callback: CallbackQuery) -> None:
    expense_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "🏷 Yangi kategoriyani tanlang:",
        reply_markup=get_edit_category_keyboard(expense_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_cat:"))
async def handle_set_category(callback: CallbackQuery) -> None:
    parts = callback.data.split(":", 2)
    expense_id = int(parts[1])
    category = parts[2]

    # Qo'shni ikki oqim (forward va pending) kategoriyani tekshiradi — bu yer
    # ham tekshirsin, aks holda validatsiya izchil bo'lmaydi.
    if category not in {c.value for c in Category}:
        await callback.answer("Noto'g'ri kategoriya")
        return

    async with async_session() as session:
        await expense_service.update_expense(session, expense_id, category=category)

    await callback.message.edit_text(f"✅ Kategoriya yangilandi: {category}")
    await callback.answer()


@router.callback_query(F.data == "cancel_edit")
async def cancel_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("↩️ Bekor qilindi.")
    await callback.answer()
