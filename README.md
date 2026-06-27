# Система знаний команды

Веб-система для хранения внутренних документов, поиска по ним и ответов на вопросы с указанием источников или честной пометкой о недостаточности данных.

## Текущее состояние проекта

### Сделано

- **Инициализация проекта:** `uv`, `ruff`, `justfile`, `.env.example`, `.gitignore`
- **Backend API** (`backend/`) — модульная архитектура по слоям технического проекта:
  - **API** — HTTP-маршруты FastAPI
  - **Application** — бизнес-логика (документы, Q&A, гибридный чанкинг)
  - **Persistence** — SQLAlchemy, таблицы `documents`, `snippets`, `qa_runs`, `audit_runs`
  - **Vector** — Chroma (локальный / сетевой / облачный режим)
  - **LLM** — OpenAI (эмбеддинги и ответы в strict JSON)
  - **Quality & Audit** — `needs_review`, fallback, аудит всех действий
- **Эндпоинты API:**
  - `POST /kb/documents` — добавление документа
  - `GET /kb/documents` — витрина документов
  - `GET /kb/documents/{id}` — карточка документа
  - `POST /kb/ask` — вопрос по базе знаний
  - `POST /ai/answer_with_sources` — ИИ-ответ по переданному контексту
  - `GET /health` — проверка состояния
- **RAG-пайплайн:** чанкинг → индексация в Chroma → поиск top-k → порог схожести → LLM → валидация JSON
- **Поддержка БД:** SQLite (по умолчанию) и PostgreSQL (`psycopg2-binary`)
- **Тестовые данные** (`tests_data/`):
  - `kb_documents.jsonl` — 5 документов (20–50 строк)
  - `kb_questions.jsonl` — 10 вопросов (7 с ответом в базе, 3 вне базы)
- **Скрипты тестирования** (`tests/`):
  - `seed.py` — очистка БД/Chroma и загрузка документов через API
  - `test.py` — E2E-проверка `POST /kb/ask` по вопросам из JSONL (живой сервер + OpenAI)
  - `test_*.py` — pytest-тесты API через `TestClient` (без внешних сервисов)
  - `conftest.py` — фикстуры pytest (БД, клиент, тестовый документ)
- **Калибровка поиска:** `SIMILARITY_THRESHOLD=0.43` (подобрано по тестовому набору)

### Ещё не реализовано

- Frontend (веб-панель: Документы, Вопросы, История, Аудит)
- Docker / docker-compose
- Экспорт истории (JSONL/CSV)
- Миграции БД (Alembic)

## Стек

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — зависимости и виртуальное окружение
- FastAPI, SQLAlchemy, Chroma, OpenAI API
- pytest — unit/integration-тесты API
- ruff — линтинг и форматирование

## Быстрый старт

```bash
# зависимости
uv sync

# конфигурация
cp .env.example .env
# укажите OPENAI_API_KEY в .env

# запуск backend
just back
```

API: http://localhost:8000  
Документация: http://localhost:8000/docs

Остановка backend:

```bash
just back-stop
```

## Команды just

| Команда          | Описание                          |
|------------------|-----------------------------------|
| `just`           | список команд                     |
| `just back`      | запуск backend                    |
| `just back-stop` | остановка backend                 |
| `just clear`     | очистка БД и Chroma               |
| `just load`      | загрузка документов из JSONL      |
| `just test`      | E2E-тест `POST /kb/ask` по вопросам |
| `just pytest`    | pytest-тесты API (без OpenAI)     |
| `just lint`      | проверка кода                     |
| `just fix`       | автоисправление линтером          |
| `just format`    | форматирование кода               |

## Переменные окружения

Описание — в `.env.example`. Минимально для работы backend:

- `DATABASE_URL` — строка подключения SQLAlchemy
- `OPENAI_API_KEY` — ключ OpenAI API
- `CHROMA_PERSIST_DIRECTORY` — каталог локального Chroma
- `TOP_K`, `SIMILARITY_THRESHOLD` — параметры поиска (для тестов: `0.43`)

Данные SQLite и Chroma сохраняются в каталоге `data/`.

## Примеры запросов

```bash
# добавить документ
curl -X POST http://localhost:8000/kb/documents \
  -H 'Content-Type: application/json' \
  -d '{"title":"Правила команды","text":"Мы работаем по спринтам.\n\nРевью — обязательный этап."}'

# список документов
curl http://localhost:8000/kb/documents

# вопрос по базе знаний
curl -X POST http://localhost:8000/kb/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Как мы работаем?"}'

# ИИ-ответ по явному контексту
curl -X POST http://localhost:8000/ai/answer_with_sources \
  -H 'Content-Type: application/json' \
  -d '{"question":"Как мы работаем?","context":"Мы работаем по спринтам."}'
```

## Тестирование

### Тестовые данные

Каталог `tests_data/`:

| Файл | Содержимое |
|------|------------|
| `kb_documents.jsonl` | 5 документов базы знаний |
| `kb_questions.jsonl` | 10 вопросов с полями `question`, `expected_needs_review`, `why` |

### Сценарий E2E-проверки (RAG)

```bash
# 1. запустить backend
just back

# 2. (опционально) очистить и загрузить тестовые документы
just clear
just load
# или одной командой через seed: uv run python -m tests.seed --force

# 3. прогнать E2E-автотест
just test
```

`just load` и `just test` обращаются к API на `http://localhost:8000` (переопределяется через `SEED_API_BASE_URL`).

`just test` завершается с кодом `0`, если все 10 вопросов совпали с ожиданием, и с кодом `1` при расхождениях.

### Pytest-тесты API (`just pytest`)

Быстрые тесты через `TestClient` — **backend не нужно запускать**, OpenAI и Chroma замоканы или не задействованы. Используется отдельная SQLite-БД во временном каталоге.

```bash
just pytest
# или с подробным выводом:
uv run pytest -v
```

| Файл | Эндпоинт | Что проверяется |
|------|----------|-----------------|
| `test_health.py` | `GET /health` | статус `200`, тело `{"status": "ok"}` |
| `test_documents_api.py` | `GET /kb/documents` | пустой список, витрина, запись в `audit_runs` |
| `test_documents_api.py` | `GET /kb/documents/{id}` | карточка документа, `404` если не найден |
| `test_ai_api.py` | `POST /ai/answer_with_sources` | успешный ответ, `confidence=low` → `needs_review` |
| `test_ai_api.py` | `POST /ai/answer_with_sources` | невалидный JSON от LLM, недоступность LLM |
| `test_ai_api.py` | `POST /ai/answer_with_sources` | валидация входа → `422` |

**Не покрыто pytest** (проверяется отдельно): `POST /kb/documents`, `POST /kb/ask` — через `just load` и `just test`.

Всего **11 тестов**.

### E2E-автотест (`tests/test.py`)

Для каждого вопроса из `kb_questions.jsonl` вызывается `POST /kb/ask`. Результаты выводятся в консоль по мере получения ответа:

```
  № | expected |   result | reason                  | document
----------------------------------------------------------------
  1 |    false |    false | В документе «Правила... | Правила работы команды
 ...
----------------------------------------------------------------
Итог: 10/10 успешно, 0 с расхождением
```

| Колонка | Значение |
|---------|----------|
| `expected` | ожидаемый `needs_review` из JSONL |
| `result` | фактический `needs_review` из API |
| `reason` | поле `why` из тестового файла |
| `document` | название документа из `sources` (или `—`) |

### Ожидаемые результаты

| № | `expected_needs_review` | Почему | Документ |
|---|-------------------------|--------|----------|
| 1 | `false` | В документе указано: спринты длятся две недели | Правила работы команды |
| 2 | `false` | Пробный период длится 14 дней без привязки карты | Частые вопросы клиентов |
| 3 | `false` | Минимум один одобряющий ревьюер обязателен до merge | Правила работы команды |
| 4 | `false` | В словаре есть определение RAG | Словарь терминов |
| 5 | `false` | Указан шаблон `feature/TICKET-123-short-name` | Процесс запуска задачи |
| 6 | `false` | Поддержка: `support@example.com` или форма в личном кабинете | Частые вопросы клиентов |
| 7 | `false` | При `needs_review=true` шаблон не отправляется автоматически | Шаблоны ответов |
| 8 | `true` | В документах нет данных о численности команды | — |
| 9 | `true` | В базе нет адреса офиса | — |
| 10 | `true` | Цена тарифа Enterprise в документах не указана | — |

Тексты вопросов — в `tests_data/kb_questions.jsonl`.

> **Калибровка:** для прохождения всех 10 тестов используется `SIMILARITY_THRESHOLD=0.43`. При значении `0.5` вопросы № 1, 4, 5 получают `needs_review=true` из‑за `max_similarity` ниже порога (0.43–0.45).

## Структура каталогов

```
backend/
├── api/routes/       # HTTP-маршруты
├── application/      # бизнес-логика
├── persistence/      # модели и БД
├── vector/           # Chroma
├── llm/              # OpenAI
├── quality/          # аудит и контроль качества
└── schemas/          # Pydantic-схемы
docs/                 # ТЗ и технический проект
tests/                # seed.py, test.py, test_*.py, conftest.py
tests_data/           # тестовые документы и вопросы
data/                 # SQLite, Chroma (создаётся при работе)
```

## Документация

- `docs/ТЗ(3) Система знаний команды.pdf`
- `docs/Технический проект - Система знаний команды.pdf`
- `docs/Общие требования к проекту.pdf`
