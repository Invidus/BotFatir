from __future__ import annotations

import logging
import re

from botfatir.models import Listing, Source
from botfatir.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

AVITO_ITEMS_URL = "https://www.avito.ru/web/1/main/items"

_ROOM_PARAMS = {2: "110688", 3: "110689"}

_TITLE_ROOMS = re.compile(r"(\d+)\s*[-–]?\s*к", re.I)
_TITLE_AREA = re.compile(r"(\d+(?:[.,]\d+)?)\s*м²", re.I)
_TITLE_FLOOR = re.compile(r"(\d+)\s*/\s*(\d+)\s*эт", re.I)


class AvitoScraper(BaseScraper):
    name = "avito"

    def _build_params(self, page: int) -> dict:
        cfg = self.config
        params: dict = {
            "locationId": str(cfg.sources.avito_location_id),
            "categoryId": "24",
            "verticalId": "1",
            "rootCategoryId": "4",
            "localPriority": "0",
            "page": str(page),
            "priceMax": str(cfg.search.max_price),
            "sort": "date",
        }
        room_params = [_ROOM_PARAMS[r] for r in cfg.search.rooms if r in _ROOM_PARAMS]
        if room_params:
            params["params[549]"] = ",".join(room_params)

        # Исключение этажей — в filters.py (API Авито не даёт оба фильтра одновременно)
        return params

    async def fetch(self, client) -> list[Listing]:
        if not self.config.sources.avito_enabled:
            return []

        all_listings: list[Listing] = []
        max_pages = self.config.scraper.max_pages_per_source

        for page in range(1, max_pages + 1):
            await self._delay()
            resp = await client.get(
                AVITO_ITEMS_URL,
                params=self._build_params(page),
                headers={
                    **client.headers,
                    "Referer": "https://www.avito.ru/kazan/kvartiry/prodam",
                    "Origin": "https://www.avito.ru",
                    "X-Requested-With": "XMLHttpRequest",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items") or data.get("catalog", {}).get("items") or []
            if not items:
                break

            for item in items:
                listing = self._parse_item(item)
                if listing:
                    all_listings.append(listing)

        return all_listings

    def _parse_from_title(self, title: str) -> dict:
        rooms = area = floor = floors_total = None
        m = _TITLE_ROOMS.search(title)
        if m:
            rooms = int(m.group(1))
        m = _TITLE_AREA.search(title)
        if m:
            area = float(m.group(1).replace(",", "."))
        m = _TITLE_FLOOR.search(title)
        if m:
            floor = int(m.group(1))
            floors_total = int(m.group(2))
        return {
            "rooms": rooms,
            "area": area,
            "floor": floor,
            "floors_total": floors_total,
        }

    def _parse_item(self, item: dict) -> Listing | None:
        try:
            item_id = str(item.get("id") or item.get("itemId") or "")
            if not item_id:
                return None

            value = item.get("value") or item
            price = 0
            price_block = value.get("priceDetailed") or value.get("price") or {}
            if isinstance(price_block, dict):
                price = int(price_block.get("value") or price_block.get("price") or 0)
            elif isinstance(price_block, (int, float)):
                price = int(price_block)

            url_path = value.get("urlPath") or item.get("urlPath") or ""
            url = f"https://www.avito.ru{url_path}" if url_path.startswith("/") else url_path
            if not url:
                url = f"https://www.avito.ru/kazan/kvartiry/{item_id}"

            title = value.get("title") or item.get("title") or "Квартира"
            parsed = self._parse_from_title(title)

            rooms = parsed["rooms"]
            area = parsed["area"]
            floor = parsed["floor"]
            floors_total = parsed["floors_total"]
            district = None
            lat = lon = None

            for param in value.get("iva") or item.get("iva") or []:
                for block in param:
                    payload = block.get("payload") or {}
                    text = payload.get("value") or payload.get("text") or ""
                    if rooms is None and "комн" in text.lower():
                        try:
                            rooms = int("".join(c for c in text if c.isdigit())[:1])
                        except ValueError:
                            pass
                    if floor is None and "эт" in text.lower():
                        m = _TITLE_FLOOR.search(text)
                        if m:
                            floor = int(m.group(1))
                            floors_total = int(m.group(2))

            geo = value.get("geo") or item.get("geo") or {}
            address = title
            if geo:
                address = (
                    geo.get("formattedAddress")
                    or geo.get("address")
                    or geo.get("shortLabel")
                    or title
                )
                refs = geo.get("geoReferences") or []
                for ref in refs:
                    content = ref.get("content") or ""
                    if "район" in content.lower():
                        district = content

            location = value.get("location") or item.get("location") or {}
            if isinstance(location, dict):
                loc_name = location.get("name") or ""
                if loc_name and "казан" in loc_name.lower():
                    address = f"{loc_name}, {address}" if address != title else loc_name

            coords = (
                value.get("coords")
                or item.get("coords")
                or value.get("map")
                or geo.get("coords")
                or {}
            )
            if isinstance(coords, dict):
                lat = coords.get("lat")
                lon = coords.get("lng") or coords.get("lon")

            images = value.get("images") or item.get("images") or []
            photo_url = None
            if images:
                img = images[0]
                if isinstance(img, dict):
                    photo_url = img.get("636x476") or img.get("208x156") or next(
                        iter(img.values()), None
                    )

            return Listing(
                source=Source.AVITO,
                external_id=item_id,
                url=url,
                title=title,
                price=price,
                rooms=rooms,
                area=area,
                floor=floor,
                floors_total=floors_total,
                address=address,
                district=district,
                lat=lat,
                lon=lon,
                photo_url=photo_url,
                raw=item,
            )
        except Exception:
            logger.exception("avito: failed to parse item")
            return None
