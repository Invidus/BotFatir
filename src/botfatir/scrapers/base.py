from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

import httpx

from botfatir.config import AppConfig
from botfatir.models import Listing

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}


class BaseScraper(ABC):
    name: str

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def _client_kwargs(self) -> dict:
        kwargs: dict = {
            "timeout": self.config.scraper.timeout_seconds,
            "headers": DEFAULT_HEADERS,
            "follow_redirects": True,
        }
        if self.config.http_proxy:
            kwargs["proxy"] = self.config.http_proxy
        return kwargs

    async def _delay(self) -> None:
        await asyncio.sleep(self.config.scraper.request_delay_seconds)

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient) -> list[Listing]:
        pass

    async def run(self) -> list[Listing]:
        async with httpx.AsyncClient(**self._client_kwargs()) as client:
            try:
                listings = await self.fetch(client)
                logger.info("%s: fetched %d listings", self.name, len(listings))
                return listings
            except Exception:
                logger.exception("%s: fetch failed", self.name)
                raise
