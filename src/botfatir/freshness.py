from __future__ import annotations

from datetime import datetime, timedelta, timezone

from botfatir.config import SearchConfig
from botfatir.models import Listing


def cutoff_time(config: SearchConfig) -> datetime | None:
    if not config.max_listing_age_hours:
        return None
    return datetime.now(timezone.utc) - timedelta(hours=config.max_listing_age_hours)


def normalize_dt(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_fresh_enough(listing: Listing, config: SearchConfig) -> bool:
    """Объявление опубликовано не раньше max_listing_age_hours."""
    limit = cutoff_time(config)
    if limit is None:
        return True
    if listing.published_at is None:
        return False
    return normalize_dt(listing.published_at) >= limit
