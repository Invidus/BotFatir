# BotFatir

Telegram-бот для мониторинга новых объявлений о продаже квартир в Казани.

**Источники:** Циан, Авито, Домклик  
**Фильтры:** 2–3 комнаты, до 11 млн ₽, не первый/последний этаж, геозона на карте

## Быстрый старт

### 1. Настройка

```bash
cp .env.example .env
# Заполни TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID
```

**Как узнать chat_id:** напиши боту [@userinfobot](https://t.me/userinfobot) или [@getidsbot](https://t.me/getidsbot).

### 2. Установка (локально или на VPS)

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
# или: pip install -e .
```

### 3. Запуск

```bash
python -m botfatir
```

### 4. Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Справка |
| `/status` | Статистика |
| `/check` | Опрос прямо сейчас |
| `/pause` | Пауза уведомлений |
| `/resume` | Возобновить |

## VPS в Нидерландах

Запросы с европейского VPS обычно работают. Если площадка отдаёт капчу или 403 — добавь в `.env` российский прокси:

```
HTTP_PROXY=http://user:pass@ru-proxy:8080
HTTPS_PROXY=http://user:pass@ru-proxy:8080
```

Telegram с любого VPS работает без ограничений.

## Конфигурация

- `config.yaml` — фильтры, интервал опроса, ID регионов
- `data/search_zone.geojson` — полигон зоны поиска (красная зона на карте)
- `.env` — секреты (токен бота, chat_id, прокси)

## Документация для разработки

- `CONTEXT.md` — краткий контекст проекта (подключай в чате Cursor)
- `ROADMAP.md` — план разработки

## Systemd (VPS)

```ini
[Unit]
Description=BotFatir apartment monitor
After=network.target

[Service]
Type=simple
User=botfatir
WorkingDirectory=/opt/BotFatir
Environment=PATH=/opt/BotFatir/.venv/bin
ExecStart=/opt/BotFatir/.venv/bin/python -m botfatir
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

## Структура

```
src/botfatir/
  scrapers/   cian.py, avito.py, domclick.py
  bot/        handlers.py
  poll.py     логика опроса
  filters.py  гео + этаж + цена
data/
  search_zone.geojson
  listings.db   (создаётся автоматически)
```
