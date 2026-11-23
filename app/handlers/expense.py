"""📲 Forward qilingan bank xabarini xarajatga aylantirish.

Ilgari bu yerda FSM ichida "navbat" (queue) bor edi: forward qilingan
tranzaksiyalar ro'yxatga yig'ilib, kategoriya tugmasi har safar navbatning
BOSHIDAGI yozuvni olardi. Ikki muammosi bor edi:

1. Telegram bir nechta forwardni deyarli bir vaqtda yetkazadi va webhook
   yangilanishlari parallel qayta ishlanadi. Ikkala handler ham holatni
   "bo'sh" deb ko'rib, bitta tranzaksiya uchun IKKITA kategoriya so'rovi
   yuborardi. Ikkinchi tugma bosilganda navbatdan boshqa yozuv olinardi —
   ya'ni kategoriya boshqa tranzaksiyaga, hech qanday xato belgisisiz
   yozilardi.
2. Navbat xotirada saqlanardi va deploy paytida yo'qolardi.

Endi forward darhol `category=NULL` (pending) yozuv sifatida saqlanadi va
kategoriya `pcat:<id>:<kategoriya>` orqali tanlanadi — ya'ni tugma qaysi
yozuvga tegishli ekani tugmaning o'zida yozilgan. Bu userbot allaqachon
ishlatadigan yo'l, endi ikkala manba bir xil oqimdan o'tadi.
"""
import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.config import settings
from app.db.base import async_session
from app.handlers.pending import send_pending_card
from app.handlers.start import MAIN_MENU_TEXTS
from app.parsers.base import parse_message
from app.services import expense as expense_service
from app.states.expense import ExpenseFlow
from app.utils.money import format_amount, parse_amount

router = Router()

_AMOUNT_HELP = (
    "❌ Summani tushunmadim. Masalan: <code>150000</code>, "
    "<code>150 000</code> yoki <code>150.000</code>."
)


def _format_existing_expense(exp) -> str:
    date = exp.transaction_time or exp.created_at
    date_str = date.strftime("%d.%m.%Y %H:%M") if date else "—"
    text = f"📅 {date_str}\n💰 {format_amount(exp.amount)} UZS"
    if exp.original_amount is not None:
        text += f"\n🧾 Jami to'lov: {format_amount(exp.original_amount)} UZS"
    text += f"\n🏷 {exp.category or '— (kategoriyalanmagan)'}\n🏪 {exp.merchant or '-'}"
    return text


async def _save_pending(
    message: Message,
    amount,
    parsed=None,
    forward_chat_id: int | None = None,
    forward_message_id: int | None = None,
) -> None:
    """Xarajatni kategoriyasiz saqlaydi va uning kartochkasini ko'rsatadi."""
    async with async_session() as session:
        expense = await expense_service.create_expense(
            session,
            user_id=settings.OWNER_ID,
            amount=amount,
            category=None,
            merchant=parsed.merchant if parsed else None,
            card_type=parsed.card_type if parsed else None,
            card_last4=parsed.card_last4 if parsed else None,
            transaction_time=parsed.transaction_time if parsed else None,
            balance_after=parsed.balance_after if parsed else None,
            forward_chat_id=forward_chat_id,
            forward_message_id=forward_message_id,
            source="forward",
        )
        remaining = await expense_service.count_pending(session, settings.OWNER_ID)

    await send_pending_card(message, expense, remaining, edit=False)


def _forward_source(message: Message) -> tuple[int | None, int | None]:
    """Forward manbasi: (chat_id, message_id).

    Bot API 7.0 dan beri rasmiy maydon — `forward_origin`. Eski
    `forward_from_chat` / `forward_from_message_id` "eskirgan, kelajakda olib
    tashlanadi" deb belgilangan; o'sha kuni `F.forward_date` filtri ham hech
    narsaga mos kelmay qolar va bot forwardlarni jimgina e'tiborsiz
    qoldirardi.

    Amalda bank botidan kelgan forwardning manbasi "user" (bot) bo'ladi va
    unda `message_id` umuman bo'lmaydi — shuning uchun dublikat aniqlash
    mazmun bo'yicha ishlaydi (`is_duplicate_by_content`).
    """
    origin = message.forward_origin
    chat = getattr(origin, "chat", None) or getattr(origin, "sender_chat", None)
    return getattr(chat, "id", None), getattr(origin, "message_id", None)


@router.message(F.forward_origin)
async def handle_forward(message: Message, state: FSMContext) -> None:
    text = message.text or message.caption or ""
    parsed = parse_message(text)

    # Kirim tekshiruvi dublikatdan OLDIN: aks holda summasi mavjud xarajatga
    # mos tushgan kirim "allaqachon saqlangan" deb xabar qilinardi.
    if parsed and parsed.is_income:
        await message.answer("➕ Kirim tranzaksiyasi — o'tkazib yuborildi.")
        return

    forward_chat_id, forward_message_id = _forward_source(message)

    if parsed is None:
        if await state.get_state() == ExpenseFlow.waiting_amount.state:
            await message.answer(
                "⏳ Avval oldingi xabarning summasini kiriting, keyin buni yuboring."
            )
            return

        await state.set_state(ExpenseFlow.waiting_amount)
        await state.update_data(
            forward_chat_id=forward_chat_id, forward_message_id=forward_message_id
        )
        preview = html.escape(text[:200]) + ("..." if len(text) > 200 else "")
        body = f"\n\n<i>{preview}</i>" if preview else ""
        await message.answer(
            f"❌ Xabarni o'qib bo'lmadi.{body}\n\n✏️ Summani qo'lda kiriting:"
        )
        return

    async with async_session() as session:
        existing = await expense_service.is_duplicate_by_content(
            session, parsed.amount, parsed.transaction_time, parsed.merchant,
            balance_after=parsed.balance_after,
        )

    if existing:
        await message.answer(
            "⚠️ Bu tranzaksiya allaqachon saqlangan:\n\n"
            f"{_format_existing_expense(existing)}"
        )
        return

    await _save_pending(
        message,
        parsed.amount,
        parsed=parsed,
        forward_chat_id=forward_chat_id,
        forward_message_id=forward_message_id,
    )


@router.message(
    ExpenseFlow.waiting_amount,
    ~F.forward_origin,
    # Menyu tugmalari va buyruqlar o'z handlerlariga o'tsin
    ~F.text.in_(MAIN_MENU_TEXTS),
    ~F.text.regexp(r"^/[a-zA-Z]"),
)
async def handle_manual_amount(message: Message, state: FSMContext) -> None:
    amount = parse_amount(message.text or "")
    if amount is None:
        await message.answer(_AMOUNT_HELP)
        return

    data = await state.get_data()
    await state.clear()
    await _save_pending(
        message,
        amount,
        forward_chat_id=data.get("forward_chat_id"),
        forward_message_id=data.get("forward_message_id"),
    )
