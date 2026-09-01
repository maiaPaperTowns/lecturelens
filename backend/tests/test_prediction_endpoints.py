"""Tests for the analyze pipeline + concept/cluster read endpoints."""
from __future__ import annotations

import io

import pytest


@pytest.fixture
def analyzed_lecture(client, sample_markdown) -> int:
    lecture_id = client.post(
        "/api/uploads",
        data={"course_name": "CS 201", "lecture_title": "Merge Sort"},
        files={"files": ("lecture.md", io.BytesIO(sample_markdown), "text/markdown")},
    ).json()["lecture"]["id"]
    resp = client.post(f"/api/analyze/{lecture_id}")
    assert resp.status_code == 200, resp.text
    return lecture_id


def test_analyze_populates_concepts_and_clusters(client, analyzed_lecture):
    detail = client.get(f"/api/uploads/{analyzed_lecture}").json()
    assert detail["status"] == "analyzed"
    assert detail["concept_count"] > 0
    assert detail["cluster_count"] >= 1
    assert detail["chunk_count"] > 0


def test_concepts_endpoint_filters_and_sorts(client, analyzed_lecture):
    resp = client.get(f"/api/lectures/{analyzed_lecture}/concepts?sort_by=difficulty&descending=true")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == len(body["concepts"])
    scores = [c["difficulty_score"] or 0 for c in body["concepts"]]
    assert scores == sorted(scores, reverse=True)

    for concept in body["concepts"]:
        assert concept["concept_type"] is not None
        assert concept["difficulty_label"] in ("easy", "medium", "hard")

    # filter by difficulty
    hard = client.get(f"/api/lectures/{analyzed_lecture}/concepts?difficulty=hard").json()
    assert all(c["difficulty_label"] == "hard" for c in hard["concepts"])


def test_clusters_endpoint_returns_projection_points(client, analyzed_lecture):
    body = client.get(f"/api/lectures/{analyzed_lecture}/clusters").json()
    assert body["total"] >= 1
    cluster = body["clusters"][0]
    assert cluster["concept_count"] == len(cluster["concepts"])
    assert set(cluster["difficulty_distribution"]) == {"easy", "medium", "hard"}
    assert len(cluster["points"]) == cluster["concept_count"]
    assert all("x" in p and "y" in p for p in cluster["points"])


def test_concept_detail_has_predictions_and_related(client, analyzed_lecture):
    concept_id = client.get(f"/api/lectures/{analyzed_lecture}/concepts").json()["concepts"][0]["id"]
    detail = client.get(f"/api/concepts/{concept_id}").json()
    assert detail["snippet"]
    assert detail["original_text"]
    assert {p["task"] for p in detail["predictions"]} <= {"concept_type", "difficulty"}
    assert "concept_type" in detail["model_versions"]
    assert isinstance(detail["related_concepts"], list)


def test_analyze_missing_lecture_returns_404(client):
    assert client.post("/api/analyze/424242").status_code == 404


def test_reanalyze_is_idempotent(client, analyzed_lecture):
    first = client.get(f"/api/lectures/{analyzed_lecture}/concepts").json()["total"]
    client.post(f"/api/analyze/{analyzed_lecture}")
    second = client.get(f"/api/lectures/{analyzed_lecture}/concepts").json()["total"]
    assert first == second
