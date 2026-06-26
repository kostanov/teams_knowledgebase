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

### Ещё не реализовано

- Frontend (веб-панель: Документы, Вопросы, История, Аудит)
- Docker / docker-compose
- Seed-скрипт и тестовые данные (`tests_data/`)
- Экспорт истории (JSONL/CSV)
- Миграции БД (Alembic)

## Стек

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — зависимости и виртуальное окружение
- FastAPI, SQLAlchemy, Chroma, OpenAI API
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

| Команда      | Описание                          |
|--------------|-----------------------------------|
| `just`       | список команд                     |
| `just back`  | запуск backend                    |
| `just back-stop` | остановка backend             |
| `just lint`  | проверка кода                     |
| `just fix`   | автоисправление линтером          |
| `just format`| форматирование кода               |

## Переменные окружения

Описание — в `.env.example`. Минимально для работы backend:

- `DATABASE_URL` — строка подключения SQLAlchemy
- `OPENAI_API_KEY` — ключ OpenAI API
- `CHROMA_PERSIST_DIRECTORY` — каталог локального Chroma
- `TOP_K`, `SIMILARITY_THRESHOLD` — параметры поиска

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
data/                 # SQLite, Chroma (создаётся при работе)
```

## Документация

- `docs/ТЗ(3) Система знаний команды.pdf`
- `docs/Технический проект - Система знаний команды.pdf`
- `docs/Общие требования к проекту.pdf`
