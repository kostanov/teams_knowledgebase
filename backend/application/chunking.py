import re

PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")

PARAGRAPH_MAX_LENGTH = 1000
SENTENCE_OVERLAP = 100


def chunk_text(text: str) -> list[str]:
    paragraphs = [part.strip() for part in PARAGRAPH_SPLIT.split(text) if part.strip()]
    if not paragraphs:
        stripped = text.strip()
        return [stripped] if stripped else []

    chunks: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= PARAGRAPH_MAX_LENGTH:
            chunks.append(paragraph)
            continue
        chunks.extend(_split_long_paragraph(paragraph))
    return chunks


def _split_long_paragraph(paragraph: str) -> list[str]:
    sentences = [
        part.strip() for part in SENTENCE_SPLIT.split(paragraph) if part.strip()
    ]
    if not sentences:
        return [paragraph]

    parts: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= PARAGRAPH_MAX_LENGTH:
            current = candidate
            continue
        if current:
            parts.append(current)
        if len(sentence) <= PARAGRAPH_MAX_LENGTH:
            current = sentence
            continue
        parts.extend(_split_by_size(sentence))
        current = ""
    if current:
        parts.append(current)
    return parts


def _split_by_size(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + PARAGRAPH_MAX_LENGTH, len(text))
        parts.append(text[start:end])
        if end >= len(text):
            break
        start = max(end - SENTENCE_OVERLAP, start + 1)
    return parts
