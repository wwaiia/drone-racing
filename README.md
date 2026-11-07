# Агрегатор соревнований по дрон-рейсингу

MVP по ТЗ.md: FastAPI (бэкенд + парсеры) + Next.js 15 (фронт) + SQLAlchemy
(локально SQLite, в проде PostgreSQL через переменную окружения).

## Структура
```
backend/            FastAPI + SQLAlchemy + экстрактор + коллекторы
  app/
    extract.py      regex-извлечение полей из постов (первая ступень конвейера)
    importer.py     сырой пост -> Event (дедуп по norm_title+date+region)
    region_match.py сопоставление текста поста со справочником субъектов РФ
    region_data.py  78 субъектов РФ с ключевыми словами и координатами
    source_data.py  официальные источники ФГДР (2 федеральных + ~65 региональных отделений)
    seed.py         сиды: регионы, источники ФГДР, 7 демо-событий
    api/routes.py   /api/v1/events, /regions, /stats, admin-moderation
    collectors/     заготовки VK API и Telethon (реальные токены — в .env)
frontend/           Next.js 15 (App Router) + Tailwind 4
  src/app/page.tsx  два режима: «По регионам» и «Общие соревнования»
  src/components/   EventCard (карточка со статусом/призовым фондом), RegionPicker
```

## Запуск (2 консоли)

Бэкенд (порт 8000):
```
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```
Сид регионов и демо-событий выполняется автоматически при старте.

Фронтенд (порт 3000):
```
cd frontend
npm run dev
```
Открыть http://localhost:3000

## Сборка фронтенда (prod)
```
cd frontend
npx next build && npx next start
```
Замечание: под Node 20.18 в проекте уже применён локальный патч
`node_modules/@tailwindcss/node/node_modules/magic-string` на версию 0.30.5
(в Node 20.19+ патч не нужен).

## API примеры
- `GET /api/v1/events?mode=by_region&region_id=3` — региональные старты области
- `GET /api/v1/events?mode=national` — крупные и всероссийские
- `GET /api/v1/regions?only_with_events=true` — регионы со счётчиком будущих стартов
- `GET /api/v1/stats` — сводка для шапки
- Доп. фильтры: `status`, `has_prize`, `q`, `date_from`, `date_to`, `only_upcoming`

## Админка (MVP — HTTP)
- `POST /api/v1/admin/events/{id}/approve` и `/reject` с заголовком `X-Admin-Token`
- `POST /api/v1/admin/raw-posts?text=...` — просим переварить сырой пост

## Дальше (см. ТЗ.md, этапы 2–5)
- LLM-экстракция постов ниже порога regex (переменные LLM_* в .env)
- Карта России (Yandex Maps) с подсветкой активных регионов

## Автономный сбор на бесплатном хосте (Render + Vercel + cron-job.org)

Публичные Telegram-каналы собираются БЕЗ аккаунтов и токенов — веб-коллектор
читает открытые страницы `https://t.me/s/<канал>` (`app/collectors/telegram_web.py`).
Локально на РФ-сети t.me может не открываться — на хостинге (EU/US) работает как есть.

Порядок:
1. В `.env`/Render-переменных перечислить каналы: `COLLECT_CHANNELS=канал1,канал2`
2. По крону (cron-job.org, раз в 3 часа) дёргать:
   `POST /api/v1/admin/run_collect` с заголовком `X-Admin-Token`
3. Управление источниками: `POST/GET /api/v1/admin/sources`
4. Локальный тест: `python run_collect.py`

Samotest веб-коллектора: `python tests/test_telegram_web.py` → PASS
(фикстура markup t.me/s: извлечение постов, фильтрация коротких, создание события).

## Источники (уже в базе, из fgdr.ru/contacts, 2026-11)
- **Федеральные**: t.me/droneracingfederation, партн ньюс-фид fgdr.ru (Tilda feeds API)
  — федеральный фид парсится «с силой» (force_approve): доверенный источник.
- **Региональные (~65 отделений)**: official handle от ФГДР —
  telegram_web (без токенов, на хостинге) + vk (ждёт VK_SERVICE_TOKEN).
- Каналы начинают собираться сразу после деплоя; недоступные/несуществующие
  автоматически отключаются после 3 неудач (circuit breaker).
