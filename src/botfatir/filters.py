from __future__ import annotations

from botfatir.config import SearchConfig
from botfatir.geo import point_in_zone
from botfatir.models import Listing


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


def apply_filters(listing: Listing, config: SearchConfig) -> bool:
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
    elif not matches_district(listing, config.districts):
        return False

    return True
