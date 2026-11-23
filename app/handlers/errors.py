"""Ushlanmagan istisnolar uchun yagona joy.

Busiz handler ichidagi har qanday xato foydalanuvchi uchun sukunatga
aylanardi: oddiy xabarga javob umuman kelmasdi, inline tugmada esa
`callback.answer()` ga yetib borilmagani uchun spinner abadiy aylanardi.
Xarajat kuzatuvchi botda "ishlamadi" ni "ishladi" dan farqlab bo'lmasligi —
eng yomon nosozlik turi, chunki yo'qolgan yozuv oy oxirigacha sezilmaydi.

Handler `dp.errors` ga (ildizga) ulanadi, alohida routerga emas: aiogram
xatoni faqat istisno sodir bo'lgan routerdan yuqoriga uzatadi, ya'ni qo'shni
routerdagi ishlovchi boshqalarning xatosini ko'rmaydi.
"""
import logging

from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)

USER_MESSAGE = "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring."


async def handle_error(event: ErrorEvent) -> bool:
    logger.error(
        "Handler xatosi (update_id=%s): %s",
        getattr(event.update, "update_id", "?"),
        event.exception,
        exc_info=event.exception,
    )

    update = event.update
    try:
        if update.callback_query is not None:
            # Birinchi navbatda spinnerni to'xtatamiz
            await update.callback_query.answer(USER_MESSAGE, show_alert=True)
        elif update.message is not None:
            await update.message.answer(USER_MESSAGE)
    except Exception:
        logger.exception("Xato haqida xabar berib ham bo'lmadi")

    return True
