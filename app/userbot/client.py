"""Userbot (Kurigram/MTProto) — UzCard/Humo botlaridan xabarlarni avtomatik o'qiydi.

Faqat O'QIYDI (read-only): xabarni parse qilib, DB'ga category=NULL (pending)
sifatida saqlaydi. Barcha javob/UI rasmiy bot (aiogram) orqali ketadi.
"""
from __future__ import annotations

import html
import logging

from aiogram import Bot
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from app.config import settings
from app.db.base import async_session
from app.parsers.base import parse_message
from app.services import expense as expense_service
from app.services.settings import is_source_enabled
from app.userbot.compat import patch_richtext_parse
from app.userbot.sources import SOURCE_BOTS, SOURCE_BY_USERNAME

logger = logging.getLogger(__name__)

_client: Client | None = None
# Parse bo'lmagan xabar haqida egani ogohlantirish uchun (rasmiy bot orqali)
_bot: Bot | None = None


def is_running() -> bool:
    """Userbot haqiqatan ulanganmi.

    Sozlamalar ekrani ilgari `settings.userbot_enabled` ga qarardi, ya'ni
    faqat .env to'ldirilganini tekshirardi. Sessiya bekor qilingan yoki
    ulanish yiqilgan holatda ham ekran "🟢 yoqilgan" deb turaverardi.
    """
    return _client is not None


async def _notify_unparsed(username: str, text: str) -> None:
    """Parse bo'lmagan bank xabarini egaga yetkazadi.

    Ilgari bunday xabar `logger.info` bilan tashlab yuborilardi: tranzaksiya
    serverdagi logdan boshqa hech qayerda qolmasdi va foydalanuvchi buni faqat
    oy oxirida raqamlar to'g'ri kelmaganda sezardi. Xarajatni yo'qotgandan
    ko'ra ortiqcha bir xabar yuborgan yaxshi.
    """
    if _bot is None:
        return
    preview = html.escape(text[:600])
    try:
        await _bot.send_message(
            settings.OWNER_ID,
            f"⚠️ @{html.escape(username)} dan kelgan xabarni o'qiy olmadim — "
            f"xarajat <b>saqlanmadi</b>.\n\n"
            f"<pre>{preview}</pre>\n\n"
            f"📲 Shu xabarni menga forward qiling — summani qo'lda kiritasiz.",
        )
    except Exception:
        logger.exception("Parse bo'lmagan xabar haqida ogohlantirib bo'lmadi")


async def _handle_bank_message(client: Client, message: Message) -> None:
    username = (message.chat.username or "") if message.chat else ""
    src = SOURCE_BY_USERNAME.get(username.lower())
    if not src:
        return

    text = message.text or message.caption or ""
    if not text:
        return

    async with async_session() as session:
        # Toggle: bu bot o'chirilgan bo'lsa — e'tiborsiz qoldiramiz
        if not await is_source_enabled(session, src.username):
            return

        parsed = parse_message(text)
        if not parsed:
            logger.warning("Userbot: xabar parse bo'lmadi (@%s)", username)
            await _notify_unparsed(username, text)
            return

        if parsed.is_income:
            return  # kirim — kuzatilmaydi

        # Dublikat: summa + tranzaksiya vaqti + balans bo'yicha
        if await expense_service.is_duplicate_by_content(
            session, parsed.amount, parsed.transaction_time, parsed.merchant,
            balance_after=parsed.balance_after,
        ):
            logger.info("Userbot: dublikat o'tkazib yuborildi (%s)", parsed.amount)
            return

        await expense_service.create_expense(
            session,
            user_id=settings.OWNER_ID,
            amount=parsed.amount,
            category=None,  # pending — keyin eslatma orqali kategoriyalanadi
            merchant=parsed.merchant,
            card_type=parsed.card_type,
            card_last4=parsed.card_last4,
            transaction_time=parsed.transaction_time,
            balance_after=parsed.balance_after,
            source="userbot",
        )

    logger.info("Userbot: pending saqlandi %s (%s)", parsed.amount, parsed.merchant or "-")


def _build_client() -> Client:
    return Client(
        name="moneystat_userbot",
        api_id=settings.API_ID,
        api_hash=settings.API_HASH,
        session_string=settings.SESSION_STRING,
        in_memory=True,
    )


async def start_userbot(bot: Bot | None = None) -> Client | None:
    """Userbotni ishga tushiradi. Sozlanmagan yoki xato bo'lsa — None qaytaradi (bot baribir ishlaydi)."""
    global _client, _bot

    _bot = bot

    if not settings.userbot_enabled:
        logger.info("Userbot o'chiq (API_ID/API_HASH/SESSION_STRING yo'q)")
        return None

    patch_richtext_parse()

    usernames = [s.username for s in SOURCE_BOTS]
    client = _build_client()
    client.add_handler(
        MessageHandler(_handle_bank_message, filters.chat(usernames) & filters.incoming)
    )

    try:
        await client.start()
    except Exception as e:
        logger.error("Userbot ishga tushmadi: %s", e, exc_info=True)
        # Avtomatik o'qish butunlay o'chdi — buni jim qoldirmaymiz, aks holda
        # ⚙️ Sozlamalar ekrani ham, foydalanuvchi ham hech narsa sezmaydi.
        if bot is not None:
            try:
                await bot.send_message(
                    settings.OWNER_ID,
                    "🔴 Userbot ishga tushmadi — bank botlaridan xarajatlar "
                    "<b>avtomatik o'qilmaydi</b>.\n\n"
                    "Xabarlarni qo'lda forward qilib turing. "
                    f"Sabab: <code>{html.escape(str(e))[:200]}</code>",
                )
            except Exception:
                logger.exception("Userbot xatosi haqida ogohlantirib bo'lmadi")
        return None

    _client = client
    logger.info("Userbot ishga tushdi. Tinglanayotgan botlar: %s", usernames)
    return client


async def stop_userbot() -> None:
    global _client
    if _client is not None:
        try:
            await _client.stop()
        except Exception:
            pass
        _client = None
