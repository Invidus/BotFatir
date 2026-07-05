from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass
class SearchConfig:
    city: str
    max_price: int
    rooms: list[int]
    exclude_first_floor: bool
    exclude_last_floor: bool
    geojson_path: Path
    districts: list[str]


@dataclass
class ScraperConfig:
    poll_interval_minutes: int
    request_delay_seconds: float
    max_pages_per_source: int
    timeout_seconds: int


@dataclass
class SourceConfig:
    cian_enabled: bool
    cian_region_id: int
    avito_enabled: bool
    avito_location_id: int
    domclick_enabled: bool
    domclick_bbox: dict[str, float]


@dataclass
class AppConfig:
    search: SearchConfig
    scraper: ScraperConfig
    sources: SourceConfig
    telegram_bot_token: str
    telegram_chat_id: str
    http_proxy: str | None = field(default=None)


def load_config(config_path: Path | None = None) -> AppConfig:
    load_dotenv(ROOT_DIR / ".env")

    path = config_path or ROOT_DIR / "config.yaml"
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    search_raw = raw["search"]
    scraper_raw = raw["scraper"]
    sources_raw = raw["sources"]

    geo_path = ROOT_DIR / search_raw["geojson_path"]

    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    proxy = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")

    return AppConfig(
        search=SearchConfig(
            city=search_raw["city"],
            max_price=search_raw["max_price"],
            rooms=search_raw["rooms"],
            exclude_first_floor=search_raw["exclude_first_floor"],
            exclude_last_floor=search_raw["exclude_last_floor"],
            geojson_path=geo_path,
            districts=search_raw["districts"],
        ),
        scraper=ScraperConfig(
            poll_interval_minutes=scraper_raw["poll_interval_minutes"],
            request_delay_seconds=scraper_raw["request_delay_seconds"],
            max_pages_per_source=scraper_raw["max_pages_per_source"],
            timeout_seconds=scraper_raw["timeout_seconds"],
        ),
        sources=SourceConfig(
            cian_enabled=sources_raw["cian"]["enabled"],
            cian_region_id=sources_raw["cian"]["region_id"],
            avito_enabled=sources_raw["avito"]["enabled"],
            avito_location_id=sources_raw["avito"]["location_id"],
            domclick_enabled=sources_raw["domclick"]["enabled"],
            domclick_bbox=sources_raw["domclick"].get("kazan_bbox", {}),
        ),
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        http_proxy=proxy,
    )
