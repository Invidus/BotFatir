from __future__ import annotations

import asyncio
import logging
from typing import Any

from curl_cffi.requests import AsyncSession

from botfatir.config import AppConfig

logger = logging.getLogger(__name__)

BROWSER_HEADERS = {
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "application/json, text/plain, */*",
}

WARMUP_URLS = (
    "https://www.avito.ru/kazan/kvartiry",
    "https://kazan.cian.ru/kupit-kvartiru/",
    "https://domclick.ru/search?deal_type=sale&category=living&offer_type=flat",
)


class ScraperHttp:
    """HTTP-клиент с имитацией Chrome — обходит 403 на VPS."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._session = AsyncSession(
            impersonate="chrome120",
            proxy=config.http_proxy,
            timeout=config.scraper.timeout_seconds,
            headers=BROWSER_HEADERS,
        )

    async def warmup(self) -> None:
        for url in WARMUP_URLS:
            try:
                await self._session.get(url)
                await asyncio.sleep(1)
            except Exception as exc:
                logger.warning("warmup %s: %s", url, exc)

    async def get(self, url: str, **kwargs: Any):
        return await self._session.get(url, **kwargs)

    async def post(self, url: str, **kwargs: Any):
        return await self._session.post(url, **kwargs)

    async def close(self) -> None:
        await self._session.close()

    @property
    def headers(self) -> dict:
        return dict(BROWSER_HEADERS)
