from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

from botfatir.config import AppConfig
from botfatir.models import Listing
from botfatir.scrapers.http import ScraperHttp

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    name: str

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    async def _delay(self) -> None:
        await asyncio.sleep(self.config.scraper.request_delay_seconds)

    @abstractmethod
    async def fetch(self, client: ScraperHttp) -> list[Listing]:
        pass

    async def run(self) -> list[Listing]:
        client = ScraperHttp(self.config)
        try:
            await client.warmup()
            listings = await self.fetch(client)
            logger.info("%s: fetched %d listings", self.name, len(listings))
            return listings
        except Exception:
            logger.exception("%s: fetch failed", self.name)
            return []
        finally:
            await client.close()
