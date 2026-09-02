"""Unit tests for the preprocessing pipeline (extraction, cleaning, chunking)."""
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import pytest

from app.core.exceptions import InvalidFileError
from app.ml.preprocessing import chunk_document, clean_text, detect_file_type, extract_document
from app.ml.preprocessing.clean import remove_repeated_headers, sentence_split

_HAS_OCR = (
    shutil.which("tesseract") is not None
    and importlib.util.find_spec("pytesseract") is not None
    and importlib.util.find_spec("PIL") is not None
)


def _text_image(path: Path, lines: list[str]) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (960, 90 + 60 * len(lines)), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 34)
    except OSError:
        font = ImageFont.load_default(size=34)
    for i, line in enumerate(lines):
        draw.text((40, 40 + i * 60), line, fill="black", font=font)
    img.save(path)
    return path


def test_detect_file_type():
    assert detect_file_type("notes.pdf") == "pdf"
    assert detect_file_type("notes.TXT") == "txt"
    assert detect_file_type("readme.md") == "md"
    assert detect_file_type("slide.JPG") == "image"
    assert detect_file_type("whiteboard.png") == "image"
    assert detect_file_type("scan.jpeg") == "image"
    with pytest.raises(InvalidFileError):
        detect_file_type("archive.zip")


@pytest.mark.skipif(not _HAS_OCR, reason="tesseract / pytesseract not available")
def test_extract_image_runs_ocr(tmp_path: Path):
    path = _text_image(
        tmp_path / "notes.png",
        [
            "Binary Search",
            "Binary search locates a target value in a sorted array",
            "by repeatedly halving the search interval.",
        ],
    )
    doc = extract_document(path)
    assert doc.file_type == "image"
    assert doc.page_count == 1
    assert doc.pages[0].kind == "image"
    assert "binary search" in doc.full_text.lower()
    assert len(chunk_document(doc)) >= 1


@pytest.mark.skipif(not _HAS_OCR, reason="tesseract / pytesseract not available")
def test_extract_image_rejects_textless(tmp_path: Path):
    from PIL import Image

    blank = tmp_path / "blank.png"
    Image.new("RGB", (400, 300), "white").save(blank)
    with pytest.raises(InvalidFileError):
        extract_document(blank)


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
