"""Split an extracted document into metadata-rich chunks."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.ml.preprocessing.clean import (
    clean_text,
    normalise_for_dedup,
    remove_repeated_headers,
    sentence_split,
)
from app.ml.preprocessing.extract import ExtractedDocument

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_ALLCAPS_HEADING_RE = re.compile(r"^[A-Z0-9][A-Z0-9 \-:&/]{3,60}$")

MIN_CHUNK_CHARS = 120
MAX_CHUNK_CHARS = 900


@dataclass
class Chunk:
    order_index: int
    text: str
    char_count: int
    page_number: int | None = None
    slide_number: int | None = None
    paragraph_number: int | None = None
    section_title: str | None = None


def _iter_paragraphs(page_text: str):
    """Yield (paragraph_index, section_title, paragraph_text)."""
    section: str | None = None
    para_idx = 0
    buffer: list[str] = []

    def flush():
        nonlocal buffer, para_idx
        if buffer:
            para_idx += 1
            joined = " ".join(buffer).strip()
            buffer = []
            if joined:
                return para_idx, section, joined
        return None

    for raw_line in page_text.split("\n"):
        line = raw_line.strip()
        heading = _HEADING_RE.match(line)
        if heading:
            out = flush()
            if out:
                yield out
            section = heading.group(2).strip()
            continue
        if line and _ALLCAPS_HEADING_RE.match(line) and len(line.split()) <= 8:
            out = flush()
            if out:
                yield out
            section = line.title()
            continue
        if not line:
            out = flush()
            if out:
                yield out
            continue
        buffer.append(line)

    out = flush()
    if out:
        yield out


def _split_long(text: str) -> list[str]:
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]
    sentences = sentence_split(text)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > MAX_CHUNK_CHARS:
            pieces.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current.strip())
    return pieces or [text[:MAX_CHUNK_CHARS]]


def chunk_document(
    doc: ExtractedDocument,
    *,
    min_chars: int = MIN_CHUNK_CHARS,
    max_chars: int = MAX_CHUNK_CHARS,
) -> list[Chunk]:
    """Turn an ExtractedDocument into deduplicated, metadata-rich chunks."""
    page_texts = [clean_text(p.text) for p in doc.pages]
    page_texts = remove_repeated_headers(page_texts)
    is_slides = bool(doc.pages) and doc.pages[0].kind == "slide"
    is_single_doc = bool(doc.pages) and doc.pages[0].kind == "document"

    raw_chunks: list[Chunk] = []
    seen_hashes: set[str] = set()
    order = 0

    for page_pos, page_text in enumerate(page_texts, start=1):
        page_number = None if is_single_doc else page_pos
        slide_number = page_pos if is_slides else None

        for para_idx, section, para_text in _iter_paragraphs(page_text):
            for piece in _split_long(para_text):
                piece = piece.strip()
                if len(piece) < min_chars and raw_chunks and _can_merge(raw_chunks[-1], piece):
                    merged = f"{raw_chunks[-1].text} {piece}".strip()
                    raw_chunks[-1].text = merged
                    raw_chunks[-1].char_count = len(merged)
                    continue
                if len(piece) < 40:
                    continue
                fingerprint = hashlib.sha1(
                    normalise_for_dedup(piece)[:400].encode("utf-8")
                ).hexdigest()
                if fingerprint in seen_hashes:
                    continue
                seen_hashes.add(fingerprint)
                order += 1
                raw_chunks.append(
                    Chunk(
                        order_index=order,
                        text=piece,
                        char_count=len(piece),
                        page_number=page_number,
                        slide_number=slide_number,
                        paragraph_number=para_idx,
                        section_title=section,
                    )
                )

    return raw_chunks


def _can_merge(prev: Chunk, _piece: str) -> bool:
    return prev.char_count + len(_piece) <= MAX_CHUNK_CHARS
