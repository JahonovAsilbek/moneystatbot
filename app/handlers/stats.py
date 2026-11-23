from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.db.base import async_session
from app.keyboards.categories import UNCATEGORIZED_EMOJI, UNCATEGORIZED_LABEL
from app.keyboards.periods import PERIODS, get_period_keyboard
from app.services import stats as stats_service
from app.utils.money import format_amount

router = Router()


@router.message(F.text == "📊 Statistika")
async def handle_stats_button(message: Message) -> None:
    await message.answer(
        "📊 Qaysi muddat uchun statistikani ko'rmoqchisiz?",
        reply_markup=get_period_keyboard("stats"),
    )


@router.callback_query(F.data.startswith("stats:"))
async def handle_stats_period(callback: CallbackQuery) -> None:
    period = callback.data.split(":", 1)[1]
    period_label = next((l for l, v in PERIODS if v == period), period)

    async with async_session() as session:
        stats = await stats_service.get_category_stats(
            session, settings.OWNER_ID, period
        )

    if not stats:
        await callback.message.edit_text(
            f"📭 '{period_label}' davomida xarajatlar topilmadi."
        )
        await callback.answer()
        return

    total = sum(float(amount) for _, amount in stats)
    lines = [f"📊 Statistika — {period_label}\n"]
    for category, amount in stats:
        pct = float(amount) / total * 100 if total > 0 else 0
        # Kategoriyalanmagan xarajatlar ilgari "🏷 None" bo'lib chiqardi
        icon = UNCATEGORIZED_EMOJI if category is None else "🏷"
        name = category or UNCATEGORIZED_LABEL
        lines.append(f"  {icon} {name}: {format_amount(amount)} UZS ({pct:.1f}%)")
    lines.append(f"\n💰 Jami: {format_amount(total)} UZS")

    await callback.message.edit_text("\n".join(lines))
    await callback.answer()
