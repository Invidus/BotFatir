from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Source(str, Enum):
    CIAN = "cian"
    AVITO = "avito"
    DOMCLICK = "domclick"


@dataclass
class Listing:
    source: Source
    external_id: str
    url: str
    title: str
    price: int
    rooms: int | None
    area: float | None
    floor: int | None
    floors_total: int | None
    address: str
    district: str | None = None
    lat: float | None = None
    lon: float | None = None
    photo_url: str | None = None
    published_at: datetime | None = None
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def dedup_key(self) -> str:
        return f"{self.source.value}:{self.external_id}"

    def format_message(self) -> str:
        floor_str = "—"
        if self.floor is not None and self.floors_total is not None:
            floor_str = f"{self.floor}/{self.floors_total}"
        elif self.floor is not None:
            floor_str = str(self.floor)

        rooms_str = f"{self.rooms}к" if self.rooms else "—"
        area_str = f"{self.area:.1f} м²" if self.area else "—"
        district_str = f", {self.district}" if self.district else ""

        lines = [
            f"🏠 <b>Новая квартира</b> ({self.source.value})",
            f"💰 <b>{self.price:,}</b> ₽".replace(",", " "),
            f"📐 {rooms_str} · {area_str} · этаж {floor_str}",
            f"📍 {self.address}{district_str}",
            f'<a href="{self.url}">Открыть объявление</a>',
        ]
        return "\n".join(lines)
