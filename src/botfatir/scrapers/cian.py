from __future__ import annotations

import logging
from datetime import datetime

from botfatir.models import Listing, Source
from botfatir.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

CIAN_SEARCH_URL = "https://api.cian.ru/search-offers/v2/search-offers-desktop/"


class CianScraper(BaseScraper):
    name = "cian"

    def _build_query(self, page: int) -> dict:
        cfg = self.config
        query: dict = {
            "region": {"type": "terms", "value": [cfg.sources.cian_region_id]},
            "_type": "flatsale",
            "engine_version": {"type": "term", "value": 2},
            "room": {"type": "terms", "value": cfg.search.rooms},
            "price": {
                "type": "range",
                "value": {"lte": cfg.search.max_price},
            },
            "page": {"type": "term", "value": page},
        }
        if cfg.search.exclude_first_floor:
            query["floornf"] = {"type": "term", "value": True}
        if cfg.search.exclude_last_floor:
            query["floornl"] = {"type": "term", "value": True}
        if cfg.search.secondary_only:
            query["from_developer"] = {"type": "term", "value": False}
        return {"jsonQuery": query}

    async def fetch(self, client) -> list[Listing]:
        if not self.config.sources.cian_enabled:
            return []

        all_listings: list[Listing] = []
        max_pages = self.config.scraper.max_pages_per_source

        for page in range(1, max_pages + 1):
            await self._delay()
            resp = await client.post(
                CIAN_SEARCH_URL,
                json=self._build_query(page),
                headers={
                    **client.headers,
                    "Content-Type": "application/json",
                    "Origin": "https://kazan.cian.ru",
                    "Referer": "https://kazan.cian.ru/cat.php?deal_type=sale&engine_version=2&offer_type=flat&region=4777",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            offers = data.get("data", {}).get("offersSerialized") or []
            if not offers:
                break

            for offer in offers:
                listing = self._parse_offer(offer)
                if listing:
                    all_listings.append(listing)

        return all_listings

    def _parse_offer(self, offer: dict) -> Listing | None:
        try:
            offer_id = str(offer.get("id") or offer.get("cianId") or "")
            if not offer_id:
                return None

            geo = offer.get("geo", {}) or {}
            coords = geo.get("coordinates") or {}
            address_parts = geo.get("address") or []
            address = ", ".join(
                p.get("fullName", "") for p in address_parts if p.get("fullName")
            )
            if not address:
                address = geo.get("userInput", "Казань")

            district = None
            for part in address_parts:
                name = part.get("fullName", "")
                if "район" in name.lower():
                    district = name
                    break

            bargain = offer.get("bargainTerms", {}) or {}
            price = int(bargain.get("priceRur") or bargain.get("price") or 0)

            building = offer.get("building", {}) or {}
            floors_total = building.get("floorsCount")

            floor_info = offer.get("floorNumber")
            if floor_info is None:
                floor_info = offer.get("floor")

            rooms = offer.get("roomsCount")
            area = offer.get("totalArea") or offer.get("area")

            photos = offer.get("photos") or []
            photo_url = None
            if photos:
                photo_url = (
                    photos[0].get("fullUrl")
                    or photos[0].get("url")
                    or (photos[0].get("thumbnail2Url"))
                )

            published = offer.get("creationDate") or offer.get("added")
            published_at = None
            if published:
                try:
                    published_at = datetime.fromisoformat(
                        published.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            url = f"https://kazan.cian.ru/sale/flat/{offer_id}/"
            title = f"{rooms or '?'}к квартира, {area or '?'} м²"

            return Listing(
                source=Source.CIAN,
                external_id=offer_id,
                url=url,
                title=title,
                price=price,
                rooms=int(rooms) if rooms is not None else None,
                area=float(area) if area is not None else None,
                floor=int(floor_info) if floor_info is not None else None,
                floors_total=int(floors_total) if floors_total is not None else None,
                address=address,
                district=district,
                lat=coords.get("lat"),
                lon=coords.get("lng") or coords.get("lon"),
                photo_url=photo_url,
                published_at=published_at,
                raw=offer,
            )
        except Exception:
            logger.exception("cian: failed to parse offer")
            return None
