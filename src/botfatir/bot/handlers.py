from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from botfatir.config import AppConfig
from botfatir.db import Database
from botfatir.poll import PollService

logger = logging.getLogger(__name__)


def setup_handlers(poll_service: PollService, db: Database, config: AppConfig) -> Router:
    r = Router()

    @r.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        max_mln = config.search.max_price / 1_000_000
        market = "вторичка" if config.search.secondary_only else "все"
        await message.answer(
            "🏠 <b>BotFatir</b> — мониторинг квартир в Казани\n\n"
            f"Фильтры: 2–3к, до {max_mln:g} млн ₽, {market}, не 1/последний этаж\n"
            "Источники: Циан, Авито, Домклик\n\n"
            "Команды:\n"
            "/status — статистика\n"
            "/check — опрос сейчас\n"
            "/pause — пауза уведомлений\n"
            "/resume — возобновить",
            parse_mode="HTML",
        )

    @r.message(Command("status"))
    async def cmd_status(message: Message) -> None:
        stats = await db.stats()
        lines = [
            "📊 <b>Статус BotFatir</b>",
            f"Всего в базе: {stats['total']}",
            f"Пауза: {'да' if poll_service.paused else 'нет'}",
            "",
            "<b>По источникам:</b>",
        ]
        for src, count in stats.get("by_source", {}).items():
            lines.append(f"  • {src}: {count}")

        lines.append("\n<b>Последние опросы:</b>")
        for p in stats.get("last_polls", [])[:6]:
            err = f" ⚠️ {p['error'][:40]}" if p.get("error") else ""
            lines.append(
                f"  • {p['source']}: найдено {p['found']}, новых {p['new_count']}{err}"
            )

        await message.answer("\n".join(lines), parse_mode="HTML")

    @r.message(Command("check"))
    async def cmd_check(message: Message) -> None:
        await message.answer("⏳ Запускаю опрос всех площадок...")
        summary = await poll_service.run_poll()
        lines = [
            "✅ Опрос завершён",
            f"Новых объявлений: {summary['new_total']}",
        ]
        for src, info in summary["sources"].items():
            err = " (ошибка)" if info.get("error") else ""
            lines.append(f"  • {src}: {info['found']} найдено, {info['new']} новых{err}")
        await message.answer("\n".join(lines))

    @r.message(Command("pause"))
    async def cmd_pause(message: Message) -> None:
        poll_service.paused = True
        await message.answer("⏸ Уведомления приостановлены. Опрос продолжается.")

    @r.message(Command("resume"))
    async def cmd_resume(message: Message) -> None:
        poll_service.paused = False
        await message.answer("▶️ Уведомления возобновлены.")

    return r
