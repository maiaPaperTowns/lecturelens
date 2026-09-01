"""Concept-difficulty estimation: heuristic fallback + trained-model wrapper."""
from __future__ import annotations

import time

import numpy as np

from app.core.taxonomy import DIFFICULTY_LABELS, DIFFICULTY_TO_SCORE, score_to_difficulty
from app.ml.difficulty.features import (
    DifficultyContext,
    build_difficulty_matrix,
    difficulty_features,
)
from app.ml.embeddings.encoder import TextEmbedder
from app.ml.types import Prediction


def _expected_score(proba_row: np.ndarray, classes: list[str]) -> float:
    return float(sum(p * DIFFICULTY_TO_SCORE[c] for p, c in zip(proba_row, classes, strict=True)))


class HeuristicDifficultyClassifier:
    """Interpretable scoring model. Version ``heuristic-v1``."""

    name = "difficulty"
    family = "heuristic"
    version = "heuristic-v1"

    # weights over the interpretable features (index-aligned with DIFFICULTY_FEATURE_NAMES)
    _W = np.array([0.010, 0.004, 0.06, 0.9, -0.3, 2.2, 0.5, -0.05, 0.03, 0.12, 0.8, 0.05, 0.4])
    _BIAS = -0.55

    def predict(self, names: list[str], snippets: list[str], ctx: DifficultyContext) -> list[Prediction]:
        out: list[Prediction] = []
        for name, snippet in zip(names, snippets, strict=True):
            start = time.perf_counter()
            feats = difficulty_features(name, snippet, ctx)
            raw = float(self._W @ feats + self._BIAS)
            score = 1.0 / (1.0 + np.exp(-raw))
            label = score_to_difficulty(score)
            margin = min(abs(score - 0.4), abs(score - 0.7))
            out.append(
                Prediction(
                    label=label,
                    confidence=round(float(0.5 + min(margin * 1.5, 0.45)), 4),
                    score=round(score, 4),
                    model_name=self.name,
                    model_version=self.version,
                    latency_ms=round((time.perf_counter() - start) * 1000, 3),
                )
            )
        return out


class DifficultyClassifier:
    """Wraps a trained estimator (sklearn or torch)."""

    name = "difficulty"

    def __init__(
        self,
        estimator,
        embedder: TextEmbedder,
        family: str,
        version: str,
        use_embeddings: bool = True,
    ):
        self.estimator = estimator
        self.embedder = embedder
        self.family = family
        self.version = version
        self.use_embeddings = use_embeddings
        self.classes = list(getattr(estimator, "classes", DIFFICULTY_LABELS))

    def predict(self, names: list[str], snippets: list[str], ctx: DifficultyContext) -> list[Prediction]:
        if not names:
            return []
        start = time.perf_counter()
        emb = self.embedder.transform(snippets) if self.use_embeddings else None
        X = build_difficulty_matrix(names, snippets, ctx, emb)
        proba = self.estimator.predict_proba(X)
        elapsed = (time.perf_counter() - start) * 1000 / len(names)
        results = []
        for row in proba:
            i = int(np.argmax(row))
            score = _expected_score(row, self.classes)
            results.append(
                Prediction(
                    label=self.classes[i],
                    confidence=round(float(row[i]), 4),
                    score=round(score, 4),
                    model_name=self.name,
                    model_version=self.version,
                    latency_ms=round(elapsed, 3),
                )
            )
        return results
