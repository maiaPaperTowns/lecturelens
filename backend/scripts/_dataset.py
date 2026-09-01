"""Shared dataset-loading + feature-building helpers for the ML scripts."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from app.ml.classification.features import build_feature_matrix
from app.ml.difficulty.features import DifficultyContext, build_difficulty_matrix
from app.ml.embeddings.encoder import TextEmbedder

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TRAINING_DIR = BACKEND_ROOT / "data" / "training"
DEMO_DIR = BACKEND_ROOT / "data" / "demo"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def demo_corpus() -> list[str]:
    texts: list[str] = []
    for file in sorted(DEMO_DIR.glob("*")):
        if file.suffix.lower() in {".md", ".txt"}:
            texts.append(file.read_text(encoding="utf-8", errors="replace"))
    return texts


def build_embedder(dim: int = 128) -> TextEmbedder:
    concept_rows = load_jsonl(TRAINING_DIR / "concept_examples.jsonl")
    difficulty_rows = load_jsonl(TRAINING_DIR / "difficulty_examples.jsonl")
    corpus = (
        [r["text"] for r in concept_rows]
        + [r["text"] for r in difficulty_rows]
        + demo_corpus()
    )
    return TextEmbedder(dim=dim).fit(corpus)


def concept_dataset(embedder: TextEmbedder) -> tuple[np.ndarray, np.ndarray]:
    rows = load_jsonl(TRAINING_DIR / "concept_examples.jsonl")
    texts = [r["text"] for r in rows]
    labels = np.array([r["label"] for r in rows])
    X = build_feature_matrix(texts, embedder.transform(texts))
    return X, labels


def difficulty_dataset(embedder: TextEmbedder) -> tuple[np.ndarray, np.ndarray]:
    rows = load_jsonl(TRAINING_DIR / "difficulty_examples.jsonl")
    names = [r["name"] for r in rows]
    texts = [r["text"] for r in rows]
    labels = np.array([r["label"] for r in rows])
    ctx = DifficultyContext(all_concept_names=names, lecture_text_lower=" ".join(texts).lower())
    X = build_difficulty_matrix(names, texts, ctx, embedder.transform(texts))
    return X, labels
