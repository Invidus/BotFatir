# BotFatir — контекст проекта

> Подключай этот файл (@CONTEXT.md) в начале сессии, чтобы не объяснять проект заново.

## Цель

Telegram-бот мониторит **новые** объявления о продаже квартир в **Казани** и присылает уведомления.

## Источники

| Площадка | Метод | Эндпоинт |
|----------|-------|----------|
| Циан | POST JSON | `https://api.cian.ru/search-offers/v2/search-offers-desktop/` |
| Авито | GET JSON | `https://www.avito.ru/web/1/main/items` |
| Домклик | GET JSON | `https://offers-service.domclick.ru/offers/v2/offers` |

Парсинг через внутренние API (не официальные). Площадки могут менять API и блокировать IP.

## Фильтры поиска

- **Город:** Казань
- **Комнаты:** 2 и 3
- **Цена:** до 10 300 000 ₽
- **Тип:** только вторичка (без новостроек)
- **Этаж:** не первый, не последний
- **Районы:** Вахитовский, Советский, Ново-Савиновский, восточная часть Кировского (у Новосавиновского)
- **Геозона:** полигон в `data/search_zone.geojson` (красная зона на карте пользователя)

## Инфраструктура

- **Деплой:** VPS в Нидерландах — запросы с него допустимы; при блокировке нужен RU-прокси (`HTTP_PROXY` в `.env`)
- **БД:** SQLite (`data/listings.db`) — дедупликация по `(source, external_id)`
- **Интервал опроса:** 10 мин (настраивается в `config.yaml`)

## Стек

Python 3.11+, aiogram 3, httpx, aiosqlite, shapely, APScheduler

## Структура кода

```
src/botfatir/
  config.py      — загрузка config.yaml + .env
  models.py      — Listing dataclass
  db.py          — SQLite
  geo.py         — point-in-polygon
  filters.py     — пост-фильтрация объявлений
  notifier.py    — отправка в Telegram
  scheduler.py   — цикл опроса
  scrapers/      — cian, avito, domclick
  bot/handlers.py — команды бота
```

## Переменные окружения (.env)

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...   # куда слать уведомления
HTTP_PROXY=            # опционально, RU-прокси
```

## Команды бота

- `/start` — приветствие
- `/status` — статистика БД и последний опрос
- `/check` — принудительный опрос сейчас
- `/pause` / `/resume` — пауза уведомлений

## Текущий статус

См. `ROADMAP.md`. MVP: три скрапера + бот + дедупликация + геофильтр.

## Важно при доработке

1. Не ломать единый формат `Listing` в `models.py`
2. Новые фильтры — в `config.yaml` и `filters.py`
3. При смене API площадки — править только соответствующий файл в `scrapers/`
4. Полигон зоны — только в `data/search_zone.geojson`
