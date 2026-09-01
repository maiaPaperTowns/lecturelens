"""Text cleaning / normalisation helpers.

Pure functions, no I/O, so they are trivial to unit-test and reuse.
"""
from __future__ import annotations

import re
import unicodedata

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_MULTISPACE_RE = re.compile(r"[ \t]{2,}")
_MULTINEWLINE_RE = re.compile(r"\n{3,}")
_HYPHEN_LINEBREAK_RE = re.compile(r"(\w)-\n(\w)")
_BULLET_RE = re.compile(r"^\s*[•▪●‣⁃\-\*]\s+", re.MULTILINE)
_PAGE_NUMBER_LINE_RE = re.compile(r"^\s*(page\s+)?\d+\s*(/\s*\d+)?\s*$", re.IGNORECASE | re.MULTILINE)
_URL_RE = re.compile(r"https?://\S+")


def normalise_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def clean_text(text: str, *, strip_urls: bool = False) -> str:
    """Normalise whitespace, join hyphenated line breaks, drop control chars."""
    if not text:
        return ""
    text = normalise_unicode(text)
    text = _CONTROL_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _HYPHEN_LINEBREAK_RE.sub(r"\1\2", text)
    text = _BULLET_RE.sub("", text)
    text = _PAGE_NUMBER_LINE_RE.sub("", text)
    if strip_urls:
        text = _URL_RE.sub("", text)
    text = _MULTISPACE_RE.sub(" ", text)
    text = _MULTINEWLINE_RE.sub("\n\n", text)
    lines = [ln.rstrip() for ln in text.split("\n")]
    return "\n".join(lines).strip()


def remove_repeated_headers(pages: list[str], *, min_repeats: int = 3) -> list[str]:
    """Strip lines (e.g. running headers/footers) that recur on most pages."""
    if len(pages) < min_repeats:
        return pages
    from collections import Counter

    counter: Counter[str] = Counter()
    for page in pages:
        for line in {ln.strip() for ln in page.splitlines() if 3 < len(ln.strip()) < 80}:
            counter[line] += 1
    threshold = max(min_repeats, int(len(pages) * 0.6))
    boilerplate = {line for line, count in counter.items() if count >= threshold}
    if not boilerplate:
        return pages
    cleaned = []
    for page in pages:
        kept = [ln for ln in page.splitlines() if ln.strip() not in boilerplate]
        cleaned.append("\n".join(kept))
    return cleaned


def sentence_split(text: str) -> list[str]:
    """Lightweight sentence splitter (no heavy NLP dependency)."""
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    return [p.strip() for p in parts if p.strip()]


def normalise_for_dedup(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
