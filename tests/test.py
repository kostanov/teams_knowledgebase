"""Тестирование API через вопросы из tests_data/kb_questions.jsonl."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUESTIONS_PATH = PROJECT_ROOT / "tests_data" / "kb_questions.jsonl"
DEFAULT_API_BASE_URL = "http://localhost:8000"


@dataclass
class TestQuestion:
    number: int
    question: str
    expected_needs_review: bool
    why: str


@dataclass
class TestResult:
    number: int
    expected: bool
    result: bool | None
    reason: str
    document: str
    passed: bool
    error: str | None = None


def read_questions(path: Path = DEFAULT_QUESTIONS_PATH) -> list[TestQuestion]:
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    questions: list[TestQuestion] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise ValueError(f"Невалидный JSON в {path}:{line_number}") from error

            question = payload.get("question", "").strip()
            if not question:
                raise ValueError(f"Пустой question в {path}:{line_number}")

            questions.append(
                TestQuestion(
                    number=len(questions) + 1,
                    question=question,
                    expected_needs_review=bool(payload["expected_needs_review"]),
                    why=str(payload.get("why", "")).strip(),
                )
            )
    return questions


def api_request(
    *,
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> Any:
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url=f"{base_url.rstrip('/')}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode()
    except urllib.error.HTTPError as error:
        details = error.read().decode()
        raise RuntimeError(f"Ошибка API {error.code} {path}: {details}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Не удалось подключиться к API {base_url}. Запущен ли backend?"
        ) from error

    return json.loads(body) if body else None


def fetch_document_titles(base_url: str) -> dict[str, str]:
    documents = api_request(base_url=base_url, method="GET", path="/kb/documents")
    return {item["id"]: item["title"] for item in documents}


def ask_question(base_url: str, question: str) -> dict[str, Any]:
    return api_request(
        base_url=base_url,
        method="POST",
        path="/kb/ask",
        payload={"question": question},
    )


def format_document_names(
    sources: list[dict[str, Any]],
    titles_by_id: dict[str, str],
) -> str:
    if not sources:
        return "—"

    names: list[str] = []
    seen: set[str] = set()
    for source in sources:
        document_id = source.get("document_id", "")
        title = titles_by_id.get(document_id, document_id or "неизвестно")
        if title not in seen:
            seen.add(title)
            names.append(title)
    return ", ".join(names)


def evaluate_question(
    item: TestQuestion,
    *,
    base_url: str,
    titles_by_id: dict[str, str],
) -> TestResult:
    try:
        response = ask_question(base_url, item.question)
    except RuntimeError as error:
        return TestResult(
            number=item.number,
            expected=item.expected_needs_review,
            result=None,
            reason=item.why,
            document="—",
            passed=False,
            error=str(error),
        )

    actual = bool(response["needs_review"])
    sources = response.get("sources", [])
    document = format_document_names(sources, titles_by_id)

    passed = actual == item.expected_needs_review
    if item.expected_needs_review is False and not sources:
        passed = False

    return TestResult(
        number=item.number,
        expected=item.expected_needs_review,
        result=actual,
        reason=item.why,
        document=document,
        passed=passed,
    )


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "error"
    return "true" if value else "false"


def print_table_header() -> None:
    print(
        f"{'№':>3} | {'expected':>8} | {'result':>8} | {'reason':<50} | document",
        flush=True,
    )
    print("-" * 120, flush=True)


def print_table_row(result: TestResult) -> None:
    result_value = _format_bool(result.result)
    if result.error:
        result_value = "error"
    reason = result.reason
    if result.error:
        reason = f"{reason} [{result.error}]"
    if len(reason) > 50:
        reason = reason[:47] + "..."

    print(
        f"{result.number:>3} | {_format_bool(result.expected):>8} | "
        f"{result_value:>8} | {reason:<50} | {result.document}",
        flush=True,
    )


def print_summary(results: list[TestResult]) -> None:
    passed = sum(1 for item in results if item.passed)
    failed = len(results) - passed
    print("-" * 120)
    print(f"Итог: {passed}/{len(results)} успешно, {failed} с расхождением")
    if failed:
        failed_numbers = ", ".join(
            str(item.number) for item in results if not item.passed
        )
        print(f"Не прошли вопросы: {failed_numbers}")
        sys.exit(1)


def run_api_tests(
    *,
    path: Path = DEFAULT_QUESTIONS_PATH,
    base_url: str | None = None,
) -> list[TestResult]:
    api_base_url = base_url or os.getenv("SEED_API_BASE_URL", DEFAULT_API_BASE_URL)
    questions = read_questions(path)
    titles_by_id = fetch_document_titles(api_base_url)

    print_table_header()
    results: list[TestResult] = []
    for item in questions:
        result = evaluate_question(
            item, base_url=api_base_url, titles_by_id=titles_by_id
        )
        results.append(result)
        print_table_row(result)

    print_summary(results)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Тестирование POST /kb/ask")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_QUESTIONS_PATH,
        help="путь к kb_questions.jsonl",
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("SEED_API_BASE_URL", DEFAULT_API_BASE_URL),
        help="базовый URL backend API",
    )
    args = parser.parse_args(argv)

    try:
        run_api_tests(path=args.file, base_url=args.api_base_url)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
