"""Tests for the switchable clustering layer and cluster labelling."""
from __future__ import annotations

import numpy as np
import pytest

from app.ml.clustering import choose_k, get_clusterer, label_cluster
from app.ml.clustering.algorithms import SUPPORTED
from app.ml.evaluation.metrics import clustering_metrics


@pytest.fixture
def blobs() -> np.ndarray:
    rng = np.random.default_rng(0)
    a = rng.normal(loc=[5, 5], scale=0.3, size=(15, 2))
    b = rng.normal(loc=[-5, -5], scale=0.3, size=(15, 2))
    c = rng.normal(loc=[5, -5], scale=0.3, size=(15, 2))
    return np.vstack([a, b, c]).astype(np.float32)


@pytest.mark.parametrize("name", SUPPORTED)
def test_every_clusterer_returns_one_label_per_point(name: str, blobs: np.ndarray):
    clusterer = get_clusterer(name, n_clusters=3)
    labels = clusterer.fit_predict(blobs)
    assert len(labels) == len(blobs)
    assert len(set(labels)) >= 2


def test_choose_k_recovers_three_blobs(blobs: np.ndarray):
    assert choose_k(blobs, k_min=2, k_max=6) == 3


def test_get_clusterer_rejects_unknown():
    with pytest.raises(ValueError):
        get_clusterer("spectral")


def test_clustering_metrics_report_silhouette(blobs: np.ndarray):
    labels = get_clusterer("kmeans", n_clusters=3).fit_predict(blobs)
    metrics = clustering_metrics(blobs, labels)
    assert metrics["n_clusters"] == 3
    assert metrics["silhouette"] is not None and metrics["silhouette"] > 0.5
    assert sum(metrics["cluster_sizes"].values()) == len(blobs)


def test_label_cluster_uses_representative_concepts():
    emb = np.array([[0.0, 0.0], [0.1, 0.0], [5.0, 5.0]], dtype=np.float32)
    summary = label_cluster(
        [10, 11, 12],
        ["Hash Table", "Hash Function", "Unrelated Topic"],
        [
            "A hash table maps keys to buckets using a hash function.",
            "A hash function turns a key into an array index.",
            "Something entirely different about networking.",
        ],
        emb,
    )
    assert "Hash" in summary.label
    assert 10 in summary.representative_concept_ids
