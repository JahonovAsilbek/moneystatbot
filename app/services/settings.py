"""Kalit-qiymat sozlamalar servisi (toggle'lar uchun)."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Setting
from app.userbot.sources import SOURCE_BY_USERNAME, toggle_key


async def get_setting(session: AsyncSession, key: str, default: str | None = None) -> str | None:
    row = await session.get(Setting, key)
    return row.value if row else default


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    row = await session.get(Setting, key)
    if row:
        row.value = value
    else:
        session.add(Setting(key=key, value=value))
    await session.commit()


async def is_source_enabled(session: AsyncSession, username: str) -> bool:
    """Manba bot avtomatik o'qish uchun yoqilganmi. Sozlanmagan bo'lsa — default'ga qaytadi."""
    src = SOURCE_BY_USERNAME.get(username.lower())
    default = "1" if (src and src.default_enabled) else "0"
    return await get_setting(session, toggle_key(username), default) == "1"


async def set_source_enabled(session: AsyncSession, username: str, enabled: bool) -> None:
    await set_setting(session, toggle_key(username), "1" if enabled else "0")
