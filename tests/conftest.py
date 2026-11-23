"""Testlar uchun umumiy sozlama.

Muhit o'zgaruvchilari `app.config` import qilinishidan OLDIN qo'yiladi:
`Settings` modul yuklanganda o'qiladi.
"""
import os

os.environ.setdefault("BOT_TOKEN", "123456:TEST-TOKEN")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("OWNER_ID", "123456789")
os.environ.setdefault("TIMEZONE", "Asia/Tashkent")

import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.db.models import Base  # noqa: E402

OWNER_ID = int(os.environ["OWNER_ID"])


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        yield db
    await engine.dispose()
