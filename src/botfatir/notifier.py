from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramMigrateToChat

from botfatir.config import AppConfig
from botfatir.models import Listing

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self, config: AppConfig, bot: Bot) -> None:
        self.config = config
        self.bot = bot
        self.chat_id = config.telegram_chat_id

    def _handle_migrate(self, exc: TelegramMigrateToChat) -> None:
        new_id = str(exc.migrate_to_chat_id)
        logger.warning(
            "Group upgraded to supergroup: update TELEGRAM_CHAT_ID to %s in .env",
            new_id,
        )
        self.chat_id = new_id

    async def _send_message(self, **kwargs) -> None:
        try:
            await self.bot.send_message(chat_id=self.chat_id, **kwargs)
        except TelegramMigrateToChat as exc:
            self._handle_migrate(exc)
            await self.bot.send_message(chat_id=self.chat_id, **kwargs)

    async def _send_photo(self, **kwargs) -> None:
        try:
            await self.bot.send_photo(chat_id=self.chat_id, **kwargs)
        except TelegramMigrateToChat as exc:
            self._handle_migrate(exc)
            await self.bot.send_photo(chat_id=self.chat_id, **kwargs)

    async def send_listing(self, listing: Listing) -> None:
        if not self.chat_id:
            logger.warning("TELEGRAM_CHAT_ID not set, skip notification")
            return

        text = listing.format_message()
        try:
            if listing.photo_url:
                await self._send_photo(
                    photo=listing.photo_url,
                    caption=text,
                    parse_mode=ParseMode.HTML,
                )
            else:
                await self._send_message(
                    text=text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False,
                )
        except Exception:
            logger.exception("Failed to send listing %s", listing.dedup_key)
            await self._send_message(text=text, parse_mode=ParseMode.HTML)

    async def send_text(self, text: str) -> None:
        if not self.chat_id:
            return
        await self._send_message(text=text, parse_mode=ParseMode.HTML)
