from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import Bot

from botfatir.config import AppConfig
from botfatir.db import Database
from botfatir.filters import apply_filters
from botfatir.models import Listing
from botfatir.notifier import Notifier
from botfatir.scrapers import AvitoScraper, CianScraper, DomclickScraper
from botfatir.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class PollService:
    def __init__(
        self,
        config: AppConfig,
        db: Database,
        notifier: Notifier,
    ) -> None:
        self.config = config
        self.db = db
        self.notifier = notifier
        self.paused = False
        self._scrapers: list[BaseScraper] = [
            CianScraper(config),
            AvitoScraper(config),
            DomclickScraper(config),
        ]

    async def run_poll(self) -> dict:
        started = datetime.now(timezone.utc).isoformat()
        summary: dict = {"sources": {}, "new_total": 0}

        for scraper in self._scrapers:
            source_name = scraper.name
            found = 0
            new_count = 0
            error = None

            try:
                listings = await scraper.run()
                found = len(listings)

                for listing in listings:
                    if not apply_filters(listing, self.config.search):
                        continue

                    is_new = await self.db.save_listing(listing)
                    if is_new:
                        new_count += 1
                        if not self.paused:
                            await self.notifier.send_listing(listing)
                            await self.db.mark_notified(listing.dedup_key)

            except Exception as exc:
                error = str(exc)
                logger.exception("Poll failed for %s", source_name)

            await self.db.log_poll(source_name, found, new_count, error, started)
            summary["sources"][source_name] = {
                "found": found,
                "new": new_count,
                "error": error,
            }
            summary["new_total"] += new_count

        return summary
