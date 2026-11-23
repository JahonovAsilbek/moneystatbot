"""Faqat bot egasining yangilanishlarini o'tkazadi.

Ikki tamoyil:

1. Tekshiruv "rad etish" tomonga yiqiladi. Oldingi variant faqat `message` va
   `callback_query` ni bilardi va boshqa har qanday update turini (masalan
   `edited_message`) tekshiruvsiz o'tkazib yuborardi. Endi foydalanuvchini
   aniqlab bo'lmasa — update tashlab yuboriladi.

2. Chat ham tekshiriladi. Webhook so'rovi soxta bo'lsa, unda `from.id` ni
   eganiki qilib, `chat.id` ni o'ziniki qilib yozish mumkin edi — javob
   hujumchining chatiga ketardi. Bot shaxsiy, shuning uchun yagona haqiqiy
   chat — eganing o'z chati.
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app.config import settings


def _chat_id(event: Any) -> int | None:
    chat = getattr(event, "chat", None)
    if chat is None:
        # CallbackQuery'da chat bevosita emas, xabar ichida bo'ladi
        chat = getattr(getattr(event, "message", None), "chat", None)
    return getattr(chat, "id", None)


class OwnerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Update):
            return await handler(event, data)

        try:
            inner = event.event
        except Exception:
            return None  # noma'lum update turi — o'tkazmaymiz

        # `poll_answer` da maydon `user` deb ataladi, qolganlarida `from_user`
        user = getattr(inner, "from_user", None) or getattr(inner, "user", None)
        if user is None or user.id != settings.OWNER_ID:
            return None

        chat_id = _chat_id(inner)
        if chat_id is not None and chat_id != settings.OWNER_ID:
            return None

        return await handler(event, data)
