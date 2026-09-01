"""Unit tests for the preprocessing pipeline (extraction, cleaning, chunking)."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import InvalidFileError
from app.ml.preprocessing import chunk_document, clean_text, detect_file_type, extract_document
from app.ml.preprocessing.clean import remove_repeated_headers, sentence_split


def test_detect_file_type():
    assert detect_file_type("notes.pdf") == "pdf"
    assert detect_file_type("notes.TXT") == "txt"
    assert detect_file_type("readme.md") == "md"
    with pytest.raises(InvalidFileError):
        detect_file_type("archive.zip")


def test_clean_text_normalises_whitespace_and_hyphenation():
    raw = "This is a sen-\ntence with   extra    spaces.\n\n\n\nAnd  page 3\n"
    cleaned = clean_text(raw)
    assert "sentence" in cleaned
    assert "   " not in cleaned
    assert "\n\n\n" not in cleaned


def test_remove_repeated_headers():
    pages = [f"CS 101 Header\nUseful content {i}\nFooter line" for i in range(5)]
    result = remove_repeated_headers(pages)
    assert all("CS 101 Header" not in page for page in result)
    assert all("Useful content" in page for page in result)


def test_sentence_split():
    assert sentence_split("First sentence. Second one! Third?") == [
        "First sentence.",
        "Second one!",
        "Third?",
    ]


def test_extract_and_chunk_markdown(tmp_path: Path, sample_markdown: bytes):
    path = tmp_path / "lecture.md"
    path.write_bytes(sample_markdown)

    doc = extract_document(path)
    assert doc.file_type == "md"
    assert doc.page_count == 1

    chunks = chunk_document(doc)
    assert len(chunks) >= 4
    sections = {c.section_title for c in chunks if c.section_title}
    assert "Definition" in sections
    # chunks carry ordering + paragraph metadata
    assert [c.order_index for c in chunks] == sorted(c.order_index for c in chunks)
    assert all(c.char_count == len(c.text) for c in chunks)


def test_extract_rejects_empty_file(tmp_path: Path):
    path = tmp_path / "empty.txt"
    path.write_bytes(b"   \n  ")
    with pytest.raises(InvalidFileError):
        extract_document(path)


def test_chunking_deduplicates(tmp_path: Path):
    repeated = ("This paragraph is repeated verbatim several times in the source. " * 3 + "\n\n") * 4
    path = tmp_path / "dupes.txt"
    path.write_text(repeated)
    chunks = chunk_document(extract_document(path))
    assert len(chunks) == 1
