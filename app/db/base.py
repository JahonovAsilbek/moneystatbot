from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings


def _fix_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    url = url.replace("sslmode=require", "ssl=require")
    url = url.replace("&channel_binding=require", "")
    url = url.replace("?channel_binding=require&", "?")
    url = url.replace("?channel_binding=require", "")
    return url


# `pool_pre_ping` — har bir ulanishdan oldin tirikligini tekshiradi. Busiz
# bot kechasi bo'sh turganda Postgres ulanishni yopib qo'yardi va ertalabki
# birinchi so'rov `ConnectionDoesNotExistError` bilan yiqilardi.
# `pool_recycle` — ulanishni bir soatdan ko'p ushlab turmaslik.
engine = create_async_engine(
    _fix_url(settings.DATABASE_URL),
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
)
async_session = async_sessionmaker(engine, expire_on_commit=False)
