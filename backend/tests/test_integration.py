"""End-to-end integration test: upload -> analyze -> dashboard -> feedback -> metrics."""
from __future__ import annotations

import io


def test_full_study_map_flow(client):
    lecture_text = (
        b"# Hash Tables\n\n"
        b"## Definition\n\nA hash table is defined as a data structure that maps keys to "
        b"values using a hash function to compute an index into an array of buckets.\n\n"
        b"## Collision Rule\n\nRule: when two keys hash to the same bucket, a collision "
        b"occurs; separate chaining stores colliding entries in a linked list.\n\n"
        b"## Example\n\nFor example, inserting the key 'apple' might hash to bucket 3 while "
        b"'banana' hashes to bucket 7.\n\n"
        b"## Load Factor\n\nThe load factor is the ratio of stored entries to buckets; once "
        b"it exceeds a threshold the table is resized and every entry is rehashed.\n\n"
        b"## Implementation\n\nThe implementation stores an array of bucket heads and grows "
        b"by doubling capacity, which keeps amortised insertion cost constant.\n\n"
        b"## Comparison\n\nUnlike a balanced binary search tree, a hash table offers average "
        b"constant-time lookup but does not preserve key ordering.\n"
    )

    # 1. upload
    upload = client.post(
        "/api/uploads",
        data={"course_name": "CS 201", "lecture_title": "Hash Tables"},
        files={"files": ("hash.md", io.BytesIO(lecture_text), "text/markdown")},
    )
    assert upload.status_code == 201
    lecture_id = upload.json()["lecture"]["id"]

    # 2. analyze
    analysis = client.post(f"/api/analyze/{lecture_id}").json()
    assert analysis["status"] == "analyzed"
    assert analysis["concept_count"] >= 4
    assert analysis["duration_ms"] > 0
    assert set(analysis["model_versions"]) == {"concept_classifier", "difficulty"}

    # 3. dashboard data
    concepts = client.get(f"/api/lectures/{lecture_id}/concepts").json()
    clusters = client.get(f"/api/lectures/{lecture_id}/clusters").json()
    assert concepts["total"] == analysis["concept_count"]
    assert sum(c["concept_count"] for c in clusters["clusters"]) == concepts["total"]

    # 4. concept detail + feedback
    target = concepts["concepts"][0]
    detail = client.get(f"/api/concepts/{target['id']}").json()
    assert detail["id"] == target["id"]

    feedback = client.post(
        f"/api/concepts/{target['id']}/feedback",
        json={"difficulty_direction": "too_easy", "note": "felt harder than rated"},
    )
    assert feedback.status_code == 201

    # 5. metrics reflect the run
    metrics = client.get("/api/models/metrics").json()
    assert metrics["lectures_analyzed"] == 1
    assert metrics["concepts_total"] == concepts["total"]
    assert metrics["feedback"]["total"] == 1

    # 6. health
    health = client.get("/api/health").json()
    assert health["status"] in ("ok", "degraded")
    assert "concept_classifier" in health["models"]
