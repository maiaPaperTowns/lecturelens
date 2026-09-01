"""Feedback storage + model-metrics aggregation."""
from __future__ import annotations

import io

import pytest


@pytest.fixture
def concept_id(client, sample_markdown) -> int:
    lecture_id = client.post(
        "/api/uploads",
        data={"course_name": "CS 201", "lecture_title": "Merge Sort"},
        files={"files": ("lecture.md", io.BytesIO(sample_markdown), "text/markdown")},
    ).json()["lecture"]["id"]
    client.post(f"/api/analyze/{lecture_id}")
    return client.get(f"/api/lectures/{lecture_id}/concepts").json()["concepts"][0]["id"]


def test_submit_classification_feedback(client, concept_id):
    resp = client.post(
        f"/api/concepts/{concept_id}/feedback",
        json={"classification_is_correct": False, "corrected_label": "definition"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["corrected_label"] == "definition"
    assert body["predicted_label"] is not None


def test_submit_difficulty_feedback(client, concept_id):
    resp = client.post(
        f"/api/concepts/{concept_id}/feedback",
        json={"difficulty_direction": "too_hard"},
    )
    assert resp.status_code == 201
    assert resp.json()["difficulty_direction"] == "too_hard"


def test_empty_feedback_rejected(client, concept_id):
    assert client.post(f"/api/concepts/{concept_id}/feedback", json={}).status_code == 422


def test_invalid_corrected_label_rejected(client, concept_id):
    resp = client.post(
        f"/api/concepts/{concept_id}/feedback", json={"corrected_label": "not_a_real_type"}
    )
    assert resp.status_code == 422


def test_feedback_on_missing_concept(client):
    assert (
        client.post("/api/concepts/999999/feedback", json={"classification_is_correct": True}).status_code
        == 404
    )


def test_metrics_endpoint_counts_feedback(client, concept_id):
    client.post(
        f"/api/concepts/{concept_id}/feedback",
        json={"classification_is_correct": False, "corrected_label": "example"},
    )
    metrics = client.get("/api/models/metrics").json()
    assert metrics["feedback"]["total"] == 1
    assert metrics["feedback"]["classification_flagged_incorrect"] == 1
    assert metrics["predictions"]["total_predictions"] > 0
    assert len(metrics["models"]) >= 2
