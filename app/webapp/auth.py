"""Telegram Mini App initData tekshiruvi (HMAC-SHA256, bot token bilan)."""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.config import settings

# initData — mohiyatan kirish kaliti. Muddat qo'yilmasa, bir marta sizib
# chiqqan satr abadiy amal qiladi. Telegram 24 soatni tavsiya qiladi.
MAX_AGE_SECONDS = 24 * 60 * 60


def validate_init_data(init_data: str) -> dict | None:
    """initData'ni tekshiradi. To'g'ri bo'lsa parse qilingan dict (user bilan) qaytaradi, aks holda None."""
    if not init_data:
        return None
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except Exception:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed, received_hash):
        return None

    # Muddat imzodan keyin tekshiriladi: `auth_date` imzolangan ma'lumot
    # tarkibida, ya'ni bu yergacha yetib kelgan bo'lsa unga ishonsa bo'ladi.
    try:
        auth_date = int(parsed.get("auth_date", ""))
    except (TypeError, ValueError):
        return None
    if time.time() - auth_date > MAX_AGE_SECONDS:
        return None

    if "user" in parsed:
        try:
            parsed["user"] = json.loads(parsed["user"])
        except Exception:
            parsed["user"] = {}
    return parsed


def is_owner(init_data: str) -> bool:
    data = validate_init_data(init_data)
    if not data:
        return False
    user = data.get("user") or {}
    return user.get("id") == settings.OWNER_ID
