from __future__ import annotations

from botfatir.config import SearchConfig
from botfatir.geo import point_in_zone
from botfatir.models import Listing, Source


def matches_district(listing: Listing, districts: list[str]) -> bool:
    if not districts:
        return True
    haystack = " ".join(
        filter(None, [listing.address, listing.district, listing.title])
    ).lower()
    for district in districts:
        key = district.lower().replace("ий", "").replace("ский", "")
        if district.lower() in haystack or key in haystack:
            return True
    return False


def is_new_building(listing: Listing) -> bool:
    text = f"{listing.title} {listing.address} {listing.url}".lower()
    keywords = (
        "новострой",
        "новостро",
        "от застройщика",
        "жилой комплекс",
        "жк ",
    )
    if any(k in text for k in keywords):
        return True
    if "novostroyk" in text or "/novostroyka" in text:
        return True

    raw = listing.raw or {}

    if listing.source == Source.CIAN:
        if raw.get("fromDeveloper"):
            return True
        if raw.get("newbuilding") or raw.get("newBuilding"):
            return True
        if raw.get("jk") or raw.get("residentialComplex"):
            return True

    if listing.source == Source.AVITO:
        value = raw.get("value") or raw
        path = (value.get("urlPath") or "").lower()
        if "novostroyk" in path:
            return True

    if listing.source == Source.DOMCLICK:
        if raw.get("isNewBuilding") or raw.get("is_new_building"):
            return True
        if raw.get("offer_type") == "layout":
            return True
        if raw.get("fromDeveloper") or raw.get("from_developer"):
            return True

    return False


def apply_filters(listing: Listing, config: SearchConfig) -> bool:
    if config.secondary_only and is_new_building(listing):
        return False

    if listing.price <= 0 or listing.price > config.max_price:
        return False

    if listing.rooms is not None and listing.rooms not in config.rooms:
        return False

    if config.exclude_first_floor and listing.floor == 1:
        return False

    if config.exclude_last_floor:
        if listing.floor is not None and listing.floors_total is not None:
            if listing.floor >= listing.floors_total:
                return False

    if listing.lat is not None and listing.lon is not None:
        if not point_in_zone(listing.lat, listing.lon, config.geojson_path):
            return False
    elif listing.source == Source.AVITO and "казан" in (listing.address or "").lower():
        # Авито уже ищет по locationId=Казань; координат в списке часто нет
        pass
    elif not matches_district(listing, config.districts):
        return False

    return True
