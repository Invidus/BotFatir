from __future__ import annotations

import logging
from datetime import datetime

from botfatir.models import Listing, Source
from botfatir.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

DOMCLICK_OFFERS_URL = "https://offers-service.domclick.ru/offers/v2/offers"
DOMCLICK_SUGGESTS_URL = "https://offers-service.domclick.ru/research/v1/suggests"


class DomclickScraper(BaseScraper):
    name = "domclick"
    _kazan_guid: str | None = None

    async def _resolve_kazan_guid(self, client) -> str | None:
        if self._kazan_guid:
            return self._kazan_guid

        resp = await client.get(
            DOMCLICK_SUGGESTS_URL,
            params={"query": self.config.search.city, "type": "geo"},
        )
        if resp.status_code != 200:
            logger.warning("domclick: suggests failed %s", resp.status_code)
            return None

        data = resp.json()
        items = data if isinstance(data, list) else data.get("suggests") or []

        for item in items:
            name = (item.get("name") or item.get("display_name") or "").lower()
            guid = item.get("guid") or item.get("id")
            if guid and "казан" in name:
                self._kazan_guid = str(guid)
                return self._kazan_guid

        if isinstance(data, list) and data:
            self._kazan_guid = str(data[0].get("guid") or data[0].get("id", ""))
            return self._kazan_guid
        return None

    def _build_params(self, offset: int, address_guid: str) -> dict:
        cfg = self.config
        rooms = ",".join(str(r) for r in cfg.search.rooms)
        params: dict = {
            "address": address_guid,
            "offset": str(offset),
            "limit": "30",
            "sort": "created",
            "sort_dir": "desc",
            "deal_type": "sale",
            "category": "living",
            "offer_type": "flat",
            "rooms": rooms,
            "price_lte": str(cfg.search.max_price),
        }
        if cfg.search.exclude_first_floor:
            params["floor_ne"] = "1"
        return params

    async def fetch(self, client) -> list[Listing]:
        if not self.config.sources.domclick_enabled:
            return []

        address_guid = await self._resolve_kazan_guid(client)
        if not address_guid:
            logger.error("domclick: could not resolve Kazan address GUID")
            return []

        all_listings: list[Listing] = []
        max_pages = self.config.scraper.max_pages_per_source
        limit = 30

        for page in range(max_pages):
            await self._delay()
            offset = page * limit
            resp = await client.get(
                DOMCLICK_OFFERS_URL,
                params=self._build_params(offset, address_guid),
                headers={
                    **client.headers,
                    "Referer": "https://domclick.ru/",
                    "Origin": "https://domclick.ru",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("result", {}).get("items") or data.get("items") or []
            if not items:
                break

            for item in items:
                listing = self._parse_item(item)
                if listing:
                    all_listings.append(listing)

        return all_listings

    def _parse_item(self, item: dict) -> Listing | None:
        try:
            offer_id = str(item.get("id") or item.get("offer_id") or "")
            if not offer_id:
                return None

            price = int(item.get("price") or item.get("sale_price") or 0)
            rooms = item.get("rooms")
            area = item.get("area") or item.get("square")
            floor = item.get("floor")
            floors_total = item.get("floors") or item.get("floors_count")

            if self.config.search.exclude_last_floor:
                if floor is not None and floors_total is not None:
                    if int(floor) >= int(floors_total):
                        return None

            address_obj = item.get("address") or {}
            if isinstance(address_obj, dict):
                address = address_obj.get("display_name") or address_obj.get("name") or ""
                district = address_obj.get("district") or address_obj.get("suburb")
                lat = address_obj.get("lat") or address_obj.get("latitude")
                lon = address_obj.get("lon") or address_obj.get("longitude")
            else:
                address = str(address_obj)
                district = lat = lon = None

            path = item.get("path") or item.get("seo", {}).get("path") or ""
            url = f"https://domclick.ru/card/{path}" if path else f"https://domclick.ru/card/{offer_id}"

            photos = item.get("photos") or []
            photo_url = photos[0] if photos else None
            if isinstance(photo_url, dict):
                photo_url = photo_url.get("url")

            published = item.get("published_at") or item.get("created")
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
