"""Concept-type classification: heuristic fallback + trained-model wrapper."""
from __future__ import annotations

import time

import numpy as np

from app.core.taxonomy import CONCEPT_TYPES
from app.ml.classification.features import build_feature_matrix, lexical_features
from app.ml.embeddings.encoder import TextEmbedder
from app.ml.types import Prediction

_CUE_TO_TYPE = {
    "cue_def": "definition",
    "cue_example": "example",
    "cue_theorem": "theorem_or_rule",
    "cue_process": "process",
    "cue_comparison": "comparison",
    "cue_impl": "implementation_detail",
    "cue_background": "background_information",
}
_CUE_NAMES = list(_CUE_TO_TYPE.keys())


class HeuristicConceptTypeClassifier:
    """Rule-based classifier over lexical cue features. Version: ``heuristic-v1``.

    Not a placeholder: it is the documented cold-start model used until
    ``train_models.py`` produces a learned model. It is also a useful baseline.
    """

    name = "concept_classifier"
    family = "heuristic"
    version = "heuristic-v1"

    def predict(self, texts: list[str]) -> list[Prediction]:
        out: list[Prediction] = []
        for text in texts:
            start = time.perf_counter()
            feats = lexical_features(text)
            cue_slice = feats[: len(_CUE_NAMES)]
            if cue_slice.max() <= 0:
                label, conf = "background_information", 0.35
            else:
                idx = int(cue_slice.argmax())
                label = _CUE_TO_TYPE[_CUE_NAMES[idx]]
                total = cue_slice.sum() or 1.0
                conf = float(0.4 + 0.5 * cue_slice[idx] / total)
            out.append(
                Prediction(
                    label=label,
                    confidence=round(min(conf, 0.95), 4),
                    model_name=self.name,
                    model_version=self.version,
                    latency_ms=round((time.perf_counter() - start) * 1000, 3),
                )
            )
        return out


class ConceptTypeClassifier:
    """Wraps a trained estimator (sklearn or torch) + the shared embedder."""

    name = "concept_classifier"

    def __init__(self, estimator, embedder: TextEmbedder, family: str, version: str):
        self.estimator = estimator
        self.embedder = embedder
        self.family = family
        self.version = version
        self.classes = list(getattr(estimator, "classes", CONCEPT_TYPES))

    def predict(self, texts: list[str]) -> list[Prediction]:
        if not texts:
            return []
        start = time.perf_counter()
        emb = self.embedder.transform(texts)
        X = build_feature_matrix(texts, emb)
        proba = self.estimator.predict_proba(X)
        elapsed = (time.perf_counter() - start) * 1000 / len(texts)
        results = []
        for row in proba:
            i = int(np.argmax(row))
            results.append(
                Prediction(
                    label=self.classes[i],
                    confidence=round(float(row[i]), 4),
                    model_name=self.name,
                    model_version=self.version,
                    latency_ms=round(elapsed, 3),
                )
            )
        return results
