"""Upload endpoint + invalid-file handling."""
from __future__ import annotations

import io


def _upload(client, filename: str, content: bytes, content_type: str = "text/markdown"):
    return client.post(
        "/api/uploads",
        data={"course_name": "CS 201", "lecture_title": "Test Lecture"},
        files={"files": (filename, io.BytesIO(content), content_type)},
    )


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
