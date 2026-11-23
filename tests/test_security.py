"""Xavfsizlik regressiyalari.

1. Webhook `secret_token` siz edi, `OwnerMiddleware` esa faqat `from_user.id`
   ni tekshirardi. Soxta Update'da `from.id` ni ega qilib, `chat.id` ni
   o'ziniki qilib yozish mumkin edi — bot javobni hujumchining chatiga
   yuborardi (ega ID si `deploy/README.md` da ochiq yozilgan edi).
2. Middleware faqat `message` va `callback_query` ni bilardi; boshqa har
   qanday update turi tekshiruvsiz o'tib ketardi ("fail-open").
3. `initData` muddati tekshirilmasdi — bir marta sizib chiqqan satr abadiy
   amal qilardi.
"""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from aiogram.types import Chat, Message, Update, User

from app.config import settings
from app.middlewares.owner import OwnerMiddleware
from app.webapp.auth import is_owner
from tests.conftest import OWNER_ID

ATTACKER_ID = 999_999


def _message(from_id: int, chat_id: int) -> Message:
    return Message(
        message_id=1,
        date=1,
        text="📋 Xarajatlar",
        chat=Chat(id=chat_id, type="private"),
        from_user=User(id=from_id, is_bot=False, first_name="x"),
    )


async def _passes(update: Update) -> bool:
    async def handler(event, data):
        return "handled"

    return await OwnerMiddleware()(handler, update, {}) is not None


async def test_owner_allowed():
    assert await _passes(Update(update_id=1, message=_message(OWNER_ID, OWNER_ID)))


async def test_spoofed_chat_rejected():
    """`from.id` to'g'ri, lekin javob boshqa chatga ketardi."""
    assert not await _passes(Update(update_id=1, message=_message(OWNER_ID, ATTACKER_ID)))


async def test_stranger_rejected():
    assert not await _passes(Update(update_id=1, message=_message(ATTACKER_ID, ATTACKER_ID)))


async def test_unknown_update_type_rejected():
    """Fail-open emas, fail-closed."""
    assert not await _passes(
        Update(update_id=1, edited_message=_message(ATTACKER_ID, ATTACKER_ID))
    )


def _init_data(auth_date: int, user_id: int = OWNER_ID, corrupt: bool = False) -> str:
    data = {"auth_date": str(auth_date), "user": json.dumps({"id": user_id})}
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    data["hash"] = digest[:-4] + "0000" if corrupt else digest
    return urlencode(data)


def test_fresh_init_data_accepted():
    assert is_owner(_init_data(int(time.time())))


def test_expired_init_data_rejected():
    assert not is_owner(_init_data(int(time.time()) - 25 * 3600))


def test_forged_signature_rejected():
    assert not is_owner(_init_data(int(time.time()), corrupt=True))


def test_other_user_rejected():
    assert not is_owner(_init_data(int(time.time()), user_id=ATTACKER_ID))


@pytest.mark.parametrize("raw", ["", "garbage", "hash=abc"])
def test_malformed_init_data_rejected(raw):
    assert not is_owner(raw)


def test_webhook_secret_is_derived_and_stable():
    assert len(settings.webhook_secret) == 64
    assert settings.webhook_secret == settings.webhook_secret
    assert settings.BOT_TOKEN not in settings.webhook_secret
