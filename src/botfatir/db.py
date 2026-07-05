from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from botfatir.config import ROOT_DIR
from botfatir.models import Listing

DB_PATH = ROOT_DIR / "data" / "listings.db"


class Database:
    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = path

    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS listings (
                    dedup_key TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT,
                    price INTEGER,
                    address TEXT,
                    first_seen_at TEXT NOT NULL,
                    notified_at TEXT
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS poll_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    source TEXT,
                    found INTEGER DEFAULT 0,
                    new_count INTEGER DEFAULT 0,
                    error TEXT
                )
                """
            )
            await db.commit()

    async def is_known(self, dedup_key: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM listings WHERE dedup_key = ?", (dedup_key,)
            )
            return await cursor.fetchone() is not None

    async def save_listing(self, listing: Listing) -> bool:
        """Сохраняет объявление. Возвращает True если это новое."""
        if await self.is_known(listing.dedup_key):
            return False

        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO listings
                (dedup_key, source, external_id, url, title, price, address, first_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    listing.dedup_key,
                    listing.source.value,
                    listing.external_id,
                    listing.url,
                    listing.title,
                    listing.price,
                    listing.address,
                    now,
                ),
            )
            await db.commit()
        return True

    async def mark_notified(self, dedup_key: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE listings SET notified_at = ? WHERE dedup_key = ?",
                (now, dedup_key),
            )
            await db.commit()

    async def log_poll(
        self,
        source: str,
        found: int,
        new_count: int,
        error: str | None = None,
        started_at: str | None = None,
    ) -> None:
        started = started_at or datetime.now(timezone.utc).isoformat()
        finished = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO poll_log (started_at, finished_at, source, found, new_count, error)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (started, finished, source, found, new_count, error),
            )
            await db.commit()

    async def stats(self) -> dict:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            total = await (
                await db.execute("SELECT COUNT(*) AS c FROM listings")
            ).fetchone()
            by_source = await (
                await db.execute(
                    "SELECT source, COUNT(*) AS c FROM listings GROUP BY source"
                )
            ).fetchall()
            last_polls = await (
                await db.execute(
                    """
                    SELECT source, started_at, found, new_count, error
                    FROM poll_log ORDER BY id DESC LIMIT 6
                    """
                )
            ).fetchall()

        return {
            "total": total["c"] if total else 0,
            "by_source": {row["source"]: row["c"] for row in by_source},
            "last_polls": [dict(row) for row in last_polls],
        }
