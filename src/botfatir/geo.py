from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from shapely.geometry import Point, shape


@lru_cache(maxsize=1)
def load_polygon(geojson_path: str) -> object:
    with open(geojson_path, encoding="utf-8") as f:
        data = json.load(f)
    return shape(data["geometry"])


def point_in_zone(lat: float | None, lon: float | None, geojson_path: Path) -> bool:
    """Проверяет, попадает ли точка в полигон поиска."""
    if lat is None or lon is None:
        return True  # без координат — пропускаем на геофильтр, остальные фильтры решат
    polygon = load_polygon(str(geojson_path))
    return polygon.contains(Point(lon, lat))
