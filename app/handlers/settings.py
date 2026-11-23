"""⚙️ Sozlamalar — manba botlarni avtomatik o'qish on/off."""
from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.config import settings as app_settings
from app.db.base import async_session
from app.services import settings as settings_service
from app.userbot import client as userbot_client
from app.userbot.sources import SOURCE_BOTS, SOURCE_BY_USERNAME

router = Router()


async def _build_settings_kb() -> InlineKeyboardMarkup:
    rows = []
    async with async_session() as session:
        for src in SOURCE_BOTS:
            enabled = await settings_service.is_source_enabled(session, src.username)
            mark = "✅" if enabled else "❌"
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"{mark} {src.label} (@{src.username})",
                        callback_data=f"toggle_src:{src.username}",
                    )
                ]
            )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _header() -> str:
    # Ilgari bu yerda faqat .env to'ldirilganmi tekshirilardi, ya'ni sessiya
    # bekor qilingan yoki ulanish yiqilgan holatda ham ekran "🟢" ko'rsatardi.
    if not app_settings.userbot_enabled:
        ub = "🔴 sozlanmagan"
    elif userbot_client.is_running():
        ub = "🟢 ishlayapti"
    else:
        ub = "🟠 sozlangan, lekin ulanmadi — loglarni tekshiring"
    return (
        "⚙️ Sozlamalar\n\n"
        f"Userbot (avtomatik o'qish): {ub}\n\n"
        "Qaysi botlardan xarajat avtomatik o'qilsin? "
        "(bosib yoqing/o'chiring)"
    )


@router.message(F.text == "⚙️ Sozlamalar")
async def handle_settings_button(message: Message) -> None:
    await message.answer(_header(), reply_markup=await _build_settings_kb())


@router.callback_query(F.data.startswith("toggle_src:"))
async def handle_toggle_source(callback: CallbackQuery) -> None:
    username = callback.data.split(":", 1)[1]
    if username.lower() not in SOURCE_BY_USERNAME:
        await callback.answer("Noma'lum bot")
        return

    async with async_session() as session:
        current = await settings_service.is_source_enabled(session, username)
        await settings_service.set_source_enabled(session, username, not current)

    await callback.message.edit_reply_markup(reply_markup=await _build_settings_kb())
    await callback.answer("✅ Yoqildi" if not current else "❌ O'chirildi")
