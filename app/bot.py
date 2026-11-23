import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import MenuButtonWebApp, WebAppInfo
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app.config import settings
from app.handlers import (
    expense,
    manage,
    pending,
    share,
    start,
    stats,
)
from app.handlers import (
    list as list_handler,
)
from app.handlers import (
    settings as settings_handler,
)
from app.handlers.errors import handle_error
from app.middlewares.menu_reset import MenuResetMiddleware
from app.middlewares.owner import OwnerMiddleware
from app.scheduler import scheduler_loop
from app.userbot.client import start_userbot, stop_userbot
from app.webapp.routes import setup_webapp_routes

logging.basicConfig(level=logging.INFO)
# Har bir HTTP so'rov uchun access-log yozilsa, `docker compose logs` webhook va
# healthcheck satrlaridan iborat bo'lib qoladi va ilovaning o'z xabarlari
# ko'rinmay ketadi. Faqat xatolarni qoldiramiz.
logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.update.outer_middleware(OwnerMiddleware())
    # Ildizga ulanadi: aiogram xatoni faqat istisno sodir bo'lgan routerdan
    # yuqoriga uzatadi, shuning uchun qo'shni routerdagi ishlovchi yetarli emas.
    dp.errors.register(handle_error)
    # Menyu tugmasi bosilganda yarim qolgan oqim holatini tozalaydi
    dp.message.middleware(MenuResetMiddleware())

    dp.include_router(start.router)
    dp.include_router(settings_handler.router)
    dp.include_router(pending.router)
    dp.include_router(manage.router)
    dp.include_router(share.router)
    dp.include_router(expense.router)
    dp.include_router(list_handler.router)
    dp.include_router(stats.router)

    return dp


async def on_startup(bot: Bot) -> None:
    if settings.public_url:
        webhook_url = f"{settings.public_url}/webhook"
        # `secret_token` busiz Telegram'dan kelmagan so'rov ham qabul qilinardi:
        # /webhook manzilini bilgan har kim soxta Update yuborib, `from.id` ni
        # ega qilib, `chat.id` ni o'ziniki qilib yozishi mumkin edi.
        await bot.set_webhook(webhook_url, secret_token=settings.webhook_secret)
        logger.info("Webhook set to %s", webhook_url)

        # Mini App'ni ochadigan menyu tugmasini o'rnatamiz
        try:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="📊 Panel",
                    web_app=WebAppInfo(url=f"{settings.public_url}/app"),
                )
            )
            logger.info("Mini App menu button set")
        except Exception as e:
            logger.error("Menu button o'rnatilmadi: %s", e)


async def health_handler(request: web.Request) -> web.Response:
    return web.Response(text="ok")


def run_webhook(bot: Bot, dp: Dispatcher) -> None:
    app = web.Application()
    app.router.add_get("/health", health_handler)
    setup_webapp_routes(app)

    webhook_handler = SimpleRequestHandler(
        dispatcher=dp, bot=bot, secret_token=settings.webhook_secret
    )
    webhook_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    dp.startup.register(on_startup)

    async def start_userbot_task(app_instance: web.Application) -> None:
        app_instance["userbot"] = await start_userbot(bot)

    async def stop_userbot_task(app_instance: web.Application) -> None:
        await stop_userbot()

    async def start_scheduler(app_instance: web.Application) -> None:
        app_instance["scheduler_task"] = asyncio.create_task(scheduler_loop(bot))

    async def stop_scheduler(app_instance: web.Application) -> None:
        task = app_instance.get("scheduler_task")
        if task:
            task.cancel()

    app.on_startup.append(start_userbot_task)
    app.on_cleanup.append(stop_userbot_task)
    app.on_startup.append(start_scheduler)
    app.on_cleanup.append(stop_scheduler)

    # `access_log=None` — aiohttp'ning o'z access-loggerini butunlay o'chiradi.
    # /health va /webhook so'rovlari sekundiga bir necha marta keladi.
    web.run_app(app, host="0.0.0.0", port=settings.PORT, access_log=None)


async def run_polling(bot: Bot, dp: Dispatcher) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await start_userbot(bot)
    scheduler_task = asyncio.create_task(scheduler_loop(bot))
    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        await stop_userbot()


def run_migrations() -> None:
    from alembic.config import Config

    from alembic import command

    error: Exception | None = None
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        error = e

    # alembic/env.py alembic.ini dagi logging sozlamasini qo'llaydi va root
    # logger darajasini WARN ga tushirib yuboradi — natijada migratsiyadan
    # keyin ilovaning INFO loglari umuman chiqmaydi. Sozlamamizni qaytaramiz.
    logging.basicConfig(level=logging.INFO, force=True)

    if error is not None:
        logger.error("Migration failed: %s", error, exc_info=error)
        # Ilgari bot davom etardi: sxema eski holida qolib, har bir so'rov
        # noaniq xato bilan yiqilardi — deploy esa "muvaffaqiyatli" ko'rinardi,
        # chunki konteyner baribir "running" bo'lib turardi. Shu yerda to'xtash
        # nosozlikni darhol ko'rinadigan qiladi.
        raise SystemExit(1)

    logger.info("Database migrations applied successfully")


def main() -> None:
    run_migrations()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher()

    if settings.public_url:
        logger.info("Starting in WEBHOOK mode on port %s", settings.PORT)
        run_webhook(bot, dp)
    else:
        logger.info("Starting in POLLING mode")
        asyncio.run(run_polling(bot, dp))


if __name__ == "__main__":
    main()
