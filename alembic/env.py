import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.config import settings
from app.db.base import _fix_url
from app.db.models import Base

config = context.config
if config.config_file_name is not None:
    # disable_existing_loggers standart holatda True — u ilovaning allaqachon
    # yaratilgan loggerlarini butunlay o'chirib qo'yadi. Migratsiyalar bot
    # jarayonining ichida ishlagani uchun (app/bot.py: run_migrations) bu
    # migratsiyadan keyingi barcha loglarni yo'q qilardi.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=_fix_url(settings.DATABASE_URL),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(_fix_url(settings.DATABASE_URL))
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
