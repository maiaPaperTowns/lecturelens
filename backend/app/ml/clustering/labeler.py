"""Generate human-readable labels for concept clusters (no LLM)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


@dataclass
class ClusterSummary:
    label: str
    keywords: list[str]
    representative_concept_ids: list[int]


def _representative_order(embeddings: np.ndarray) -> list[int]:
    centroid = embeddings.mean(axis=0, keepdims=True)
    dists = np.linalg.norm(embeddings - centroid, axis=1)
    return list(np.argsort(dists))


def label_cluster(
    concept_ids: list[int],
    concept_names: list[str],
    concept_snippets: list[str],
    embeddings: np.ndarray,
) -> ClusterSummary:
    """Label = top representative concept names; keywords = TF-IDF over snippets."""
    if not concept_ids:
        return ClusterSummary(label="Empty cluster", keywords=[], representative_concept_ids=[])

    order = _representative_order(embeddings)
    rep_ids = [concept_ids[i] for i in order[:3]]
    rep_names = [concept_names[i] for i in order[:3]]

    keywords: list[str] = []
    if len(concept_snippets) >= 2:
        try:
            vec = TfidfVectorizer(
                stop_words="english", ngram_range=(1, 2), max_features=400, sublinear_tf=True
            )
            tfidf = vec.fit_transform(concept_snippets)
            weights = np.asarray(tfidf.mean(axis=0)).ravel()
            names = np.array(vec.get_feature_names_out())
            keywords = [str(k) for k in names[np.argsort(weights)[::-1][:6]]]
        except ValueError:
            keywords = []

    # Label = the most central concept whose name is short and specific.
    ranked_names = sorted(rep_names, key=lambda n: (len(n.split()), len(n)))
    label = ranked_names[0] if ranked_names else (keywords[0].title() if keywords else "Cluster")

    _NOISE = {
        "is", "are", "the", "then", "than", "of", "to", "in", "for", "and", "or",
        "finally", "next", "first", "always", "never", "such", "very", "does",
        "equals", "stops", "costs", "increases", "along", "observe", "yields",
    }
    clean_keywords = [
        k for k in keywords if not any(w in _NOISE for w in k.lower().split())
    ][:5]
    return ClusterSummary(
        label=label.strip()[:60],
        keywords=clean_keywords or keywords[:3],
        representative_concept_ids=rep_ids,
    )
