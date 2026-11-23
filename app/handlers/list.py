from aiogram import F, Router
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.config import settings
from app.db.base import async_session
from app.keyboards.periods import PERIODS, get_period_keyboard
from app.services import expense as expense_service
from app.services.pdf import generate_expenses_pdf
from app.utils.money import format_amount

router = Router()


def _build_list_text(expenses, page: int, total_pages: int) -> str:
    if not expenses:
        return "📭 Xarajatlar topilmadi."

    lines = [f"📋 Xarajatlar ro'yxati  ({page + 1}/{total_pages})\n"]
    for exp in expenses:
        date = exp.transaction_time or exp.created_at
        date_str = date.strftime("%d.%m.%Y %H:%M") if date else "—"
        total_line = ""
        if exp.original_amount is not None:
            total_line = f"🧾 Jami: {format_amount(exp.original_amount)} UZS\n"
        lines.append(
            f"📅 {date_str}\n"
            f"💰 {format_amount(exp.amount)} UZS\n"
            f"{total_line}"
            f"🏪 {exp.merchant or '-'}\n"
        )
    return "\n".join(lines)


def _build_page_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"page:{page - 1}"))
    nav_row.append(
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop")
    )
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"page:{page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=[nav_row])


# ---- 📋 Xarajatlar ro'yxati ----

@router.message(F.text == "📋 Xarajatlar")
async def handle_list_button(message: Message) -> None:
    async with async_session() as session:
        expenses, total_pages = await expense_service.get_expenses_page(
            session, settings.OWNER_ID, 0
        )

    if not expenses:
        await message.answer("📭 Xarajatlar topilmadi.")
        return

    text = _build_list_text(expenses, 0, total_pages)
    await message.answer(text, reply_markup=_build_page_keyboard(0, total_pages))


@router.callback_query(F.data.startswith("page:"))
async def handle_page(callback: CallbackQuery) -> None:
    page = int(callback.data.split(":")[1])

    async with async_session() as session:
        expenses, total_pages = await expense_service.get_expenses_page(
            session, settings.OWNER_ID, page
        )

    text = _build_list_text(expenses, page, total_pages)
    await callback.message.edit_text(text, reply_markup=_build_page_keyboard(page, total_pages))
    await callback.answer()


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery) -> None:
    await callback.answer()


# ---- 📥 Fayl yuklash ----

@router.message(F.text == "📥 Fayl yuklash")
async def handle_download_button(message: Message) -> None:
    await message.answer(
        "📥 Qaysi muddat uchun yuklab olmoqchisiz?",
        reply_markup=get_period_keyboard("pdf"),
    )


@router.callback_query(F.data.startswith("pdf:"))
async def handle_pdf_period(callback: CallbackQuery) -> None:
    period = callback.data.split(":", 1)[1]
    period_label = next((l for l, v in PERIODS if v == period), period)

    async with async_session() as session:
        expenses = await expense_service.get_expenses(
            session, settings.OWNER_ID, period
        )

    if not expenses:
        await callback.message.edit_text(
            f"📭 '{period_label}' davomida xarajatlar topilmadi."
        )
        await callback.answer()
        return

    pdf_buffer = generate_expenses_pdf(expenses, period_label)
    doc = BufferedInputFile(pdf_buffer.read(), filename=f"xarajatlar_{period}.pdf")
    await callback.message.answer_document(doc)
    await callback.message.delete()
    await callback.answer()
