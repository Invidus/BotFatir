from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from botfatir.bot.handlers import setup_handlers
from botfatir.config import load_config
from botfatir.db import Database
from botfatir.notifier import Notifier
from botfatir.poll import PollService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    config = load_config()

    if not config.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN не задан. Скопируй .env.example → .env")
        sys.exit(1)

    db = Database()
    await db.init()

    session = None
    if config.http_proxy:
        session = AiohttpSession(proxy=config.http_proxy)
        logger.info("Using proxy for Telegram API: %s", config.http_proxy)

    bot = Bot(token=config.telegram_bot_token, session=session)
    notifier = Notifier(config, bot)
    poll_service = PollService(config, db, notifier)

    dp = Dispatcher()
    dp.include_router(setup_handlers(poll_service, db, config))

    scheduler = AsyncIOScheduler()
    interval = config.scraper.poll_interval_minutes

    async def scheduled_poll() -> None:
        logger.info("Scheduled poll started")
        try:
            summary = await poll_service.run_poll()
            logger.info("Scheduled poll done: %s new", summary["new_total"])
        except Exception:
            logger.exception("Scheduled poll failed")

    scheduler.add_job(
        scheduled_poll,
        "interval",
        minutes=interval,
        id="apartment_poll",
        max_instances=1,
    )
    scheduler.start()

    logger.info("BotFatir started. Poll every %d min.", interval)
    await dp.start_polling(bot)


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
