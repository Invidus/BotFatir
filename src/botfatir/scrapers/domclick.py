from __future__ import annotations

import json
import logging
import re
from datetime import datetime

from botfatir.models import Listing, Source
from botfatir.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

DOMCLICK_OFFERS_URL = "https://offers-service.domclick.ru/offers/v2/offers"
DOMCLICK_SUGGESTS_URL = "https://offers-service.domclick.ru/research/v1/suggests"
GEO_SUGGESTS_URL = "https://geo-service.domclick.ru/v1/suggestions"

# ФИАС города Казань + запасные GUID
KAZAN_GUID_FALLBACKS = (
    "93b3df57-79b4-4b59-8e81-04924d5c4ae1",
    "0c4f1e77-1a8e-4b93-9744-5d0536d5c3b2",
)

KAZAN_SEARCH_PAGE = (
    "https://kazan.domclick.ru/search"
    "?deal_type=sale&category=living&offer_type=flat&sort=created&sort_dir=desc"
)


class DomclickScraper(BaseScraper):
    name = "domclick"

    def _headers(self, client) -> dict:
        return {
            **client.headers,
            "Referer": "https://domclick.ru/",
            "Origin": "https://domclick.ru",
        }

    async def _try_suggests(self, client, url: str, params: dict) -> str | None:
        try:
            resp = await client.get(url, params=params, headers=self._headers(client))
            if resp.status_code != 200:
                return None
            data = resp.json()
            items = data if isinstance(data, list) else data.get("suggests") or data.get("items") or []
            for item in items:
                name = (item.get("name") or item.get("display_name") or item.get("title") or "").lower()
                guid = item.get("guid") or item.get("id") or item.get("addressGuid")
                if guid and ("казан" in name or item.get("kind") == "locality"):
                    return str(guid)
        except Exception:
            logger.debug("domclick suggests %s failed", url, exc_info=True)
        return None

    async def _resolve_kazan_guid(self, client) -> str | None:
        configured = self.config.sources.domclick_address_guid
        if configured:
            return configured

        for url, params in (
            (DOMCLICK_SUGGESTS_URL, {"query": self.config.search.city, "type": "geo"}),
            (GEO_SUGGESTS_URL, {"query": self.config.search.city}),
            (GEO_SUGGESTS_URL, {"text": self.config.search.city}),
        ):
            guid = await self._try_suggests(client, url, params)
            if guid:
                logger.info("domclick: resolved Kazan guid via %s", url)
                return guid

        for guid in KAZAN_GUID_FALLBACKS:
            logger.info("domclick: trying fallback guid %s", guid)
            if await self._probe_guid(client, guid):
                return guid

        return None

    async def _probe_guid(self, client, guid: str) -> bool:
        try:
            resp = await client.get(
                DOMCLICK_OFFERS_URL,
                params={
                    "address": guid,
                    "limit": "1",
                    "offset": "0",
                    "deal_type": "sale",
                    "category": "living",
                    "offer_type": "flat",
                },
                headers=self._headers(client),
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _base_params(self, offset: int, address_guid: str) -> dict:
        cfg = self.config
        params: dict = {
            "address": address_guid,
            "offset": str(offset),
            "limit": "30",
            "sort": "created",
            "sort_dir": "desc",
            "deal_type": "sale",
            "category": "living",
            "offer_type": "flat",
            "rooms": ",".join(str(r) for r in cfg.search.rooms),
            "price_lte": str(cfg.search.max_price),
        }
        if cfg.search.exclude_first_floor:
            params["floor_ne"] = "1"
        return params

    async def _fetch_via_api(self, client, address_guid: str) -> list[Listing]:
        all_listings: list[Listing] = []
        max_pages = self.config.scraper.max_pages_per_source
        limit = 30

        for page in range(max_pages):
            await self._delay()
            resp = await client.get(
                DOMCLICK_OFFERS_URL,
                params=self._base_params(page * limit, address_guid),
                headers=self._headers(client),
            )
            if resp.status_code in (401, 403):
                logger.warning("domclick api: %s for address %s", resp.status_code, address_guid)
                break
            if resp.status_code != 200:
                logger.warning("domclick api: unexpected %s", resp.status_code)
                break

            data = resp.json()
            items = data.get("result", {}).get("items") or data.get("items") or []
            if not items:
                break

            for item in items:
                listing = self._parse_item(item)
                if listing:
                    all_listings.append(listing)

        return all_listings

    async def _fetch_via_html(self, client) -> list[Listing]:
        try:
            resp = await client.get(KAZAN_SEARCH_PAGE, headers=self._headers(client))
            if resp.status_code != 200:
                logger.warning("domclick html: status %s", resp.status_code)
                return []

            html = resp.text
            items: list[dict] = []

            for pattern in (
                r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>',
                r'window\.__PRELOADED_STATE__\s*=\s*(\{.+?\})\s*;',
            ):
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        items = self._extract_items_from_json(data)
                        if items:
                            break
                    except json.JSONDecodeError:
                        continue

            listings = []
            for item in items:
                listing = self._parse_item(item)
                if listing:
                    listings.append(listing)
            return listings
        except Exception:
            logger.exception("domclick html fallback failed")
            return []

    def _extract_items_from_json(self, data: object) -> list[dict]:
        found: list[dict] = []

        def walk(obj: object) -> None:
            if isinstance(obj, dict):
                if "price" in obj and ("rooms" in obj or "area" in obj) and ("id" in obj or "offer_id" in obj):
                    found.append(obj)
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)

        walk(data)
        return found[:100]

    async def fetch(self, client) -> list[Listing]:
        if not self.config.sources.domclick_enabled:
            return []

        try:
            address_guid = await self._resolve_kazan_guid(client)
            if address_guid:
                listings = await self._fetch_via_api(client, address_guid)
                if listings:
                    return listings
                logger.warning("domclick api returned 0, trying HTML fallback")

            listings = await self._fetch_via_html(client)
            if not listings:
                logger.warning("domclick: no listings (API/HTML blocked from this IP)")
            return listings
        except Exception:
            logger.exception("domclick: fetch failed")
            return []

    def _parse_item(self, item: dict) -> Listing | None:
        try:
            offer_id = str(item.get("id") or item.get("offer_id") or item.get("offerId") or "")
            if not offer_id:
                return None

            price = int(item.get("price") or item.get("sale_price") or item.get("salePrice") or 0)
            rooms = item.get("rooms")
            area = item.get("area") or item.get("square")
            floor = item.get("floor")
            floors_total = item.get("floors") or item.get("floors_count") or item.get("totalFloors")

            if self.config.search.exclude_last_floor:
                if floor is not None and floors_total is not None:
                    if int(floor) >= int(floors_total):
                        return None

            address_obj = item.get("address") or {}
            if isinstance(address_obj, dict):
                address = (
                    address_obj.get("display_name")
                    or address_obj.get("name")
                    or item.get("shortAddress")
                    or item.get("addressName")
                    or ""
                )
                district = address_obj.get("district") or address_obj.get("suburb")
                lat = address_obj.get("lat") or address_obj.get("latitude") or item.get("latitude")
                lon = address_obj.get("lon") or address_obj.get("longitude") or item.get("longitude")
            else:
                address = str(address_obj) or item.get("shortAddress") or ""
                district = lat = lon = None

            path = item.get("path") or item.get("seo", {}).get("path") or ""
            if path and not path.startswith("sale__"):
                path = f"sale__flat__{offer_id}"
            url = f"https://domclick.ru/card/{path}" if path else f"https://domclick.ru/card/sale__flat__{offer_id}"

            photos = item.get("photos") or []
            photo_url = photos[0] if photos else None
            if isinstance(photo_url, dict):
                photo_url = photo_url.get("url")

            published = item.get("published_at") or item.get("created") or item.get("publishedAt")
            published_at = None
            if published:
                try:
                    published_at = datetime.fromisoformat(
                        str(published).replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            title = f"{rooms or '?'}к квартира, {area or '?'} м²"

            return Listing(
                source=Source.DOMCLICK,
                external_id=offer_id,
                url=url,
                title=title,
                price=price,
                rooms=int(rooms) if rooms is not None else None,
                area=float(area) if area is not None else None,
                floor=int(floor) if floor is not None else None,
                floors_total=int(floors_total) if floors_total is not None else None,
                address=address or "Казань",
                district=district,
                lat=float(lat) if lat is not None else None,
                lon=float(lon) if lon is not None else None,
                photo_url=photo_url,
                published_at=published_at,
                raw=item,
            )
        except Exception:
            logger.exception("domclick: failed to parse item")
            return None
