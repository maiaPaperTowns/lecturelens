"""Tests for concept detection, classification and difficulty estimation."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from app.ml.classification.concept_extractor import ConceptExtractor
from app.ml.classification.features import build_feature_matrix, lexical_features
from app.ml.classification.pipeline import HeuristicConceptTypeClassifier
from app.ml.difficulty.features import DifficultyContext, difficulty_features
from app.ml.difficulty.pipeline import HeuristicDifficultyClassifier
from app.ml.embeddings.encoder import TextEmbedder
from app.ml.preprocessing import chunk_document, extract_document


def _chunks(tmp_path: Path, text: bytes):
    path = tmp_path / "l.md"
    path.write_bytes(text)
    return chunk_document(extract_document(path))


def test_concept_extractor_finds_domain_phrases(tmp_path: Path, sample_markdown: bytes):
    candidates = ConceptExtractor(max_concepts=15).extract(_chunks(tmp_path, sample_markdown))
    assert candidates
    names = " ".join(c.name.lower() for c in candidates)
    # picks up multi-word domain phrases, not clause fragments
    assert any(kw in names for kw in ("merge sort", "quicksort", "recursion", "master theorem"))
    assert all(" is " not in f" {n.lower()} " for n in [c.name for c in candidates])
    # relevance scores are normalised to [0, 1] and sorted descending
    scores = [c.relevance_score for c in candidates]
    assert max(scores) <= 1.0 and min(scores) >= 0.0
    assert scores == sorted(scores, reverse=True)
    # every candidate keeps a traceable source
    assert all(c.snippet for c in candidates)


def test_lexical_features_shape_and_signal():
    definition = lexical_features("Merge sort is defined as a divide-and-conquer algorithm.")
    example = lexical_features("For example, sorting [5, 2, 4, 1] yields [1, 2, 4, 5].")
    assert definition.shape == example.shape
    assert definition[0] > 0  # cue_def fires
    assert example[1] > 0  # cue_example fires


def test_feature_matrix_concatenates_embedding_and_lexical():
    embedder = TextEmbedder(dim=16).fit(["alpha beta gamma", "delta epsilon zeta", "eta theta"])
    texts = ["Theorem: the bound holds.", "First, do X. Then do Y."]
    emb = embedder.transform(texts)
    matrix = build_feature_matrix(texts, emb)
    assert matrix.shape[0] == 2
    assert matrix.shape[1] == emb.shape[1] + lexical_features(texts[0]).shape[0]


def test_heuristic_concept_classifier_labels_are_valid():
    from app.core.taxonomy import CONCEPT_TYPES

    clf = HeuristicConceptTypeClassifier()
    preds = clf.predict(
        [
            "X is defined as the set of all Y.",
            "For example, consider the array [1, 2, 3].",
            "Step 1: initialise. Step 2: iterate until done.",
        ]
    )
    assert [p.label for p in preds][0] == "definition"
    assert all(p.label in CONCEPT_TYPES for p in preds)
    assert all(0.0 <= p.confidence <= 1.0 for p in preds)
    assert all(p.latency_ms is not None for p in preds)


def test_heuristic_difficulty_orders_easy_before_hard():
    ctx = DifficultyContext(all_concept_names=["Variable", "KKT Conditions"], lecture_text_lower="")
    clf = HeuristicDifficultyClassifier()
    easy, hard = clf.predict(
        ["Variable", "KKT Conditions"],
        [
            "A variable simply stores one value you can read or update.",
            "The KKT conditions combine stationarity, primal and dual feasibility, and "
            "complementary slackness; the derivation relies on constraint qualifications "
            "and a careful Lagrangian analysis that many students find demanding.",
        ],
        ctx,
    )
    assert easy.score is not None and hard.score is not None
    assert easy.score < hard.score
    assert easy.label in ("easy", "medium")


def test_difficulty_features_capture_dependencies():
    ctx = DifficultyContext(
        all_concept_names=["gradient", "learning rate", "loss function"],
        lecture_text_lower="gradient descent uses the learning rate and the loss function",
    )
    feats = difficulty_features(
        "gradient descent",
        "Gradient descent uses the learning rate to minimise the loss function.",
        ctx,
    )
    assert feats.shape[0] == len(
        __import__("app.ml.difficulty.features", fromlist=["DIFFICULTY_FEATURE_NAMES"]).DIFFICULTY_FEATURE_NAMES
    )
    assert np.all(np.isfinite(feats))
