default:
    @just --list

back:
    uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

back-stop:
    #!/usr/bin/env bash
    set -euo pipefail
    if pkill -f "uvicorn backend.main:app"; then
        echo "Backend остановлен"
    else
        echo "Backend не запущен"
        exit 1
    fi

front:
    uv run uvicorn frontend.main:app --reload --host 0.0.0.0 --port 8080

front-stop:
    #!/usr/bin/env bash
    set -euo pipefail
    if pkill -f "uvicorn frontend.main:app"; then
        echo "Frontend остановлен"
    else
        echo "Frontend не запущен"
        exit 1
    fi

lint:
    uv run ruff check

fix:
    uv run ruff check --fix

format:
    uv run ruff format

clear:
    uv run python -m tests.seed --clear

load:
    uv run python -m tests.seed

test:
    uv run python -m tests.test

pytest:
    uv run pytest

