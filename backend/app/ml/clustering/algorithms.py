"""Switchable clustering algorithms behind a common interface."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
from sklearn.metrics import silhouette_score

from app.core.logging import get_logger

logger = get_logger(__name__)

SUPPORTED = ("kmeans", "agglomerative", "dbscan")


class Clusterer(Protocol):
    name: str

    def fit_predict(self, X: np.ndarray) -> np.ndarray: ...


@dataclass
class KMeansClusterer:
    n_clusters: int = 5
    name: str = "kmeans"

    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        k = max(2, min(self.n_clusters, len(X) - 1))
        return KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(X)


@dataclass
class AgglomerativeClusterer:
    n_clusters: int = 5
    linkage: str = "ward"
    name: str = "agglomerative"

    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        k = max(2, min(self.n_clusters, len(X) - 1))
        return AgglomerativeClustering(n_clusters=k, linkage=self.linkage).fit_predict(X)


@dataclass
class DBSCANClusterer:
    eps: float = 0.5
    min_samples: int = 3
    name: str = "dbscan"

    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        labels = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric="cosine").fit_predict(X)
        # relabel noise (-1) points into their own singleton clusters for downstream code
        next_id = labels.max() + 1 if labels.max() >= 0 else 0
        out = labels.copy()
        for i, lbl in enumerate(labels):
            if lbl == -1:
                out[i] = next_id
                next_id += 1
        return out


def get_clusterer(name: str, n_clusters: int | None = None, **kwargs) -> Clusterer:
    name = name.lower()
    if name == "kmeans":
        return KMeansClusterer(n_clusters=n_clusters or 5)
    if name == "agglomerative":
        return AgglomerativeClusterer(n_clusters=n_clusters or 5, **kwargs)
    if name == "dbscan":
        return DBSCANClusterer(**kwargs)
    raise ValueError(f"Unknown clusterer '{name}'. Choose from {SUPPORTED}.")


def choose_k(X: np.ndarray, k_min: int = 2, k_max: int = 8) -> int:
    """Pick the number of clusters that maximises silhouette score."""
    n = len(X)
    if n < 4:
        return max(1, n)
    best_k, best_score = 2, -1.0
    for k in range(k_min, min(k_max, n - 1) + 1):
        try:
            labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(X)
            if len(set(labels)) < 2:
                continue
            score = silhouette_score(X, labels, metric="cosine")
        except ValueError:
            continue
        if score > best_score:
            best_k, best_score = k, score
    logger.info("choose_k -> k=%d (silhouette=%.3f)", best_k, best_score)
    return best_k
