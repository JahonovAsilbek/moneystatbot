"""Kurigram'dagi ochiq bug uchun himoya qatlami.

`RichText._parse` ichma-ich joylashgan rich-text uchun satr emas, `RichTextBold`
kabi obyekt qaytaradi, keyin esa o'sha obyektda satr metodini chaqiradi:

    pyrogram/types/messages_and_media/rich_text.py:207
        hashtag=content.lstrip("#")

Natijada instant-view maqolasi bo'lgan har qanday xabar
`AttributeError: 'RichTextBold' object has no attribute 'lstrip'` bilan
yiqiladi. Muhimi — xato dispatcher'ning `message_parser` bosqichida sodir
bo'ladi, ya'ni **butun update tashlab yuboriladi** va handlerlargacha yetib
bormaydi.

Bizga `rich_message` (instant view bloklari) umuman kerak emas — biz faqat bank
botlarining oddiy matnini o'qiymiz. Shuning uchun rich-text parse xatosini
yutamiz: xabarning qolgan qismi normal parse bo'ladi va handlerlarga boradi.

Bug 2.2.24 (eng oxirgi versiya) da hali ham bor, ya'ni kutubxonani yangilash
yordam bermaydi. Kurigram yangilanganda bu faylning hali ham kerakligini
qayta tekshirish kerak.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_patched = False


def patch_richtext_parse() -> None:
    """`RichText._parse` ni xatoga chidamli qiladi. Qayta chaqirish xavfsiz."""
    global _patched
    if _patched:
        return

    try:
        from pyrogram.types.messages_and_media.rich_text import RichText
    except Exception as e:  # kutubxona tuzilishi o'zgargan bo'lsa — bot baribir ishlasin
        logger.warning("Kurigram RichText patchi qo'llanmadi: %s", e)
        return

    original = RichText._parse

    async def safe_parse(client, rich_text, users=None, chats=None):
        try:
            return await original(client, rich_text, users or {}, chats or {})
        except AttributeError:
            # Aynan yuqoridagi bug. `_parse` rekursiv chaqiriladi, shuning uchun
            # ichkarida None qaytganda tashqi qatlam ham shu yerga tushadi va
            # xato yuqoriga chiqmasdan so'nadi.
            logger.debug("RichText bloki o'tkazib yuborildi (kurigram bug)")
            return None

    RichText._parse = staticmethod(safe_parse)
    _patched = True
    logger.info("Kurigram RichText patchi qo'llandi")
