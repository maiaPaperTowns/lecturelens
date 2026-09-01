"""Evaluation metrics for classification and clustering."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    silhouette_score,
)


def classification_metrics(
    y_true: list[str], y_pred: list[str], labels: list[str] | None = None
) -> dict:
    labels = labels or sorted(set(y_true) | set(y_pred))
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision_macro": round(
            float(precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)), 4
        ),
        "recall_macro": round(
            float(recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)), 4
        ),
        "f1_macro": round(
            float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)), 4
        ),
        "f1_weighted": round(
            float(f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)), 4
        ),
        "labels": labels,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "support": int(len(y_true)),
    }


def clustering_metrics(X: np.ndarray, labels: np.ndarray) -> dict:
    X = np.asarray(X)
    labels = np.asarray(labels)
    unique, counts = np.unique(labels, return_counts=True)
    result: dict = {
        "n_clusters": int(len(unique)),
        "cluster_sizes": {int(u): int(c) for u, c in zip(unique, counts, strict=True)},
    }
    if len(unique) >= 2 and len(X) > len(unique):
        try:
            result["silhouette"] = round(float(silhouette_score(X, labels, metric="cosine")), 4)
        except ValueError:
            result["silhouette"] = None
    else:
        result["silhouette"] = None

    intra = []
    for u in unique:
        members = X[labels == u]
        if len(members) < 2:
            continue
        centroid = members.mean(axis=0, keepdims=True)
        norms = np.linalg.norm(members, axis=1, keepdims=True) * np.linalg.norm(centroid)
        cos = (members @ centroid.T) / np.clip(norms, 1e-9, None)
        intra.append(float(cos.mean()))
    result["mean_intra_cluster_similarity"] = round(float(np.mean(intra)), 4) if intra else None
    return result
