from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.enums import ParseMode

from botfatir.config import AppConfig
from botfatir.models import Listing

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self, config: AppConfig, bot: Bot) -> None:
        self.config = config
        self.bot = bot
        self.chat_id = config.telegram_chat_id

    async def send_listing(self, listing: Listing) -> None:
        if not self.chat_id:
            logger.warning("TELEGRAM_CHAT_ID not set, skip notification")
            return

        text = listing.format_message()
        try:
            if listing.photo_url:
                await self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=listing.photo_url,
                    caption=text,
                    parse_mode=ParseMode.HTML,
                )
            else:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False,
                )
        except Exception:
            logger.exception("Failed to send listing %s", listing.dedup_key)
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )

    async def send_text(self, text: str) -> None:
        if not self.chat_id:
            return
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )
