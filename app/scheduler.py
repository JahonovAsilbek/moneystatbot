"""Eslatma scheduleri — qayta ishga tushishga chidamli (deploy/restart uchun).

Holat DB'da saqlanadi (`last_notify_slot`). Har ~5 daqiqada tekshiradi:
o'tgan eng oxirgi eslatma-slotini hali qayta ishlamagan bo'lsa va pending
xarajat bo'lsa — eslatma yuboradi. Shu tufayli deploy/uyqu tufayli
o'tkazib yuborilgan slot ishga tushishda "catch-up" qilinadi.
"""
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import settings
from app.db.base import async_session
from app.services import expense as expense_service
from app.services import settings as settings_service

logger = logging.getLogger(__name__)

# Toshkent vaqti bo'yicha eslatma soatlari (kunduzi ~har 4 soat)
NOTIFY_HOURS = [9, 13, 17, 21]
CHECK_INTERVAL = 300  # 5 daqiqa
_LAST_SLOT_KEY = "last_notify_slot"


def _latest_passed_slot(now: datetime) -> datetime | None:
    """Bugun `now` dan oldin (yoki teng) o'tgan eng oxirgi eslatma-slot vaqti."""
    latest = None
    for h in sorted(NOTIFY_HOURS):
        slot = now.replace(hour=h, minute=0, second=0, microsecond=0)
        if slot <= now:
            latest = slot
    return latest


async def _send_notification(bot: Bot, count: int) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏷 Kategoriyalash", callback_data="pending_start")]
        ]
    )
    await bot.send_message(
        settings.OWNER_ID,
        f"🔔 Sizda <b>{count} ta</b> kategoriyalanmagan xarajat bor.\n\n"
        "Ularni kategoriyalarga ajratamizmi?",
        reply_markup=kb,
    )
    logger.info("Eslatma yuborildi: %s ta pending", count)


async def _run_check(bot: Bot, tz: ZoneInfo) -> None:
    now = datetime.now(tz)
    slot = _latest_passed_slot(now)
    if slot is None:
        return  # bugungi birinchi slotdan oldin — eslatma yo'q

    async with async_session() as session:
        last_raw = await settings_service.get_setting(session, _LAST_SLOT_KEY)
        last_dt = datetime.fromisoformat(last_raw) if last_raw else None

        # Bu slot allaqachon qayta ishlanganmi?
        if last_dt is not None and last_dt >= slot:
            return

        count = await expense_service.count_pending(session, settings.OWNER_ID)

    # MUHIM: slot faqat xabar HAQIQATAN yuborilgandan keyin belgilanadi.
    # Ilgari tartib teskari edi va `send_message` yiqilsa (tarmoq uzilishi,
    # Telegram 429) slot "ishlangan" bo'lib qolardi — ya'ni o'sha eslatma
    # butunlay yo'qolardi. Bu esa modulning o'z maqsadiga (o'tkazib
    # yuborilgan slotni catch-up qilish) zid edi.
    if count > 0:
        await _send_notification(bot, count)

    async with async_session() as session:
        # Pending bo'lmasa ham belgilaymiz — takror tekshirmaslik uchun
        await settings_service.set_setting(session, _LAST_SLOT_KEY, slot.isoformat())


async def scheduler_loop(bot: Bot) -> None:
    tz = ZoneInfo(settings.TIMEZONE)
    logger.info("Scheduler ishga tushdi (soatlar: %s, TZ: %s)", NOTIFY_HOURS, settings.TIMEZONE)
    while True:
        try:
            await _run_check(bot, tz)
        except Exception as e:
            logger.error("Eslatma tekshiruvida xato: %s", e, exc_info=True)
        await asyncio.sleep(CHECK_INTERVAL)
