"""Dimensionality reduction for concept-embedding visualisation."""
from __future__ import annotations

import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

from app.core.logging import get_logger

logger = get_logger(__name__)


def project_2d(embeddings: np.ndarray, method: str = "auto") -> np.ndarray:
    """Return an (n, 2) array of 2-D coordinates for scatter-plot display."""
    X = np.asarray(embeddings, dtype=np.float32)
    n = len(X)
    if n == 0:
        return np.zeros((0, 2), dtype=np.float32)
    if n < 3 or X.shape[1] < 2:
        pad = np.zeros((n, 2), dtype=np.float32)
        pad[:, : min(2, X.shape[1])] = X[:, : min(2, X.shape[1])]
        return pad

    if method == "auto":
        method = "tsne" if 3 <= n <= 500 else "pca"

    try:
        if method == "tsne":
            perplexity = max(2.0, min(30.0, (n - 1) / 3.0))
            coords = TSNE(
                n_components=2, perplexity=perplexity, init="pca", random_state=42, learning_rate="auto"
            ).fit_transform(X)
        else:
            coords = PCA(n_components=2, random_state=42).fit_transform(X)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Projection (%s) failed: %s; falling back to PCA-2.", method, exc)
        coords = PCA(n_components=min(2, X.shape[1]), random_state=42).fit_transform(X)

    # scale to a friendly range for the frontend
    coords = np.asarray(coords, dtype=np.float32)
    span = np.ptp(coords, axis=0)
    span[span == 0] = 1.0
    return (coords - coords.min(axis=0)) / span * 100.0
