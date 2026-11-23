"""Asosiy menyu tugmasi bosilganda yarim qolgan oqim holatini tozalaydi.

Ilgari "summani kiriting" holatida turib menyu tugmasi bosilsa, tugma
`❌ Noto'g'ri summa` javobini olardi va holatdan chiqib bo'lmasdi (router
tartibi tufayli 📋 Xarajatlar, 📊 Statistika va 📥 Fayl yuklash aynan shunday
tiqilib qolardi).

Handlerlarga `~F.text.in_(MAIN_MENU_TEXTS)` filtri qo'yish tugmani ishlatadi,
lekin holatni joyida qoldiradi — keyin tasodifan yozilgan raqam eski
xarajatga tushib ketishi mumkin. Shuning uchun holat markazlashgan holda,
bitta joyda tozalanadi.
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.handlers.start import MAIN_MENU_TEXTS


class MenuResetMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text in MAIN_MENU_TEXTS:
            state = data.get("state")
            if state is not None and await state.get_state() is not None:
                await state.clear()
        return await handler(event, data)
