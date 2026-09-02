"""Upload endpoint + invalid-file handling."""
from __future__ import annotations

import importlib.util
import io
import shutil

import pytest

_HAS_OCR = (
    shutil.which("tesseract") is not None
    and importlib.util.find_spec("pytesseract") is not None
    and importlib.util.find_spec("PIL") is not None
)


def _upload(client, filename: str, content: bytes, content_type: str = "text/markdown"):
    return client.post(
        "/api/uploads",
        data={"course_name": "CS 201", "lecture_title": "Test Lecture"},
        files={"files": (filename, io.BytesIO(content), content_type)},
    )


def _png_with_text(text: str) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 40)
    except OSError:
        font = ImageFont.load_default(size=40)
    img = Image.new("RGB", (1100, 260), "white")
    ImageDraw.Draw(img).text((40, 90), text, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_upload_markdown_succeeds(client, sample_markdown):
    resp = _upload(client, "lecture.md", sample_markdown)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["lecture"]["status"] == "uploaded"
    assert body["lecture"]["files"][0]["file_type"] == "md"
    assert body["lecture"]["files"][0]["size_bytes"] == len(sample_markdown)


def test_upload_rejects_unsupported_extension(client):
    resp = _upload(client, "notes.docx", b"junk", "application/octet-stream")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_file"


def test_upload_rejects_empty_file(client):
    resp = _upload(client, "empty.txt", b"", "text/plain")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_file"


@pytest.mark.skipif(not _HAS_OCR, reason="tesseract / pytesseract not available")
def test_upload_image_runs_ocr(client):
    png = _png_with_text("Merge Sort divides the list in half")
    resp = _upload(client, "slide.png", png, "image/png")
    assert resp.status_code == 201, resp.text
    file_row = resp.json()["lecture"]["files"][0]
    assert file_row["file_type"] == "image"
    assert file_row["page_count"] == 1


@pytest.mark.skipif(not _HAS_OCR, reason="tesseract / pytesseract not available")
def test_upload_rejects_textless_image(client):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (300, 200), "white").save(buf, format="PNG")
    resp = _upload(client, "blank.png", buf.getvalue(), "image/png")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_file"


def test_upload_requires_course_and_title(client, sample_markdown):
    resp = client.post(
        "/api/uploads",
        data={"course_name": "", "lecture_title": ""},
        files={"files": ("l.md", io.BytesIO(sample_markdown), "text/markdown")},
    )
    assert resp.status_code == 422


def test_list_and_get_upload(client, sample_markdown):
    created = _upload(client, "lecture.md", sample_markdown).json()["lecture"]["id"]

    listing = client.get("/api/uploads")
    assert listing.status_code == 200
    assert any(item["id"] == created for item in listing.json())

    detail = client.get(f"/api/uploads/{created}")
    assert detail.status_code == 200
    assert detail.json()["chunk_count"] == 0  # not analysed yet


def test_get_missing_upload_returns_404(client):
    resp = client.get("/api/uploads/999999")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"
