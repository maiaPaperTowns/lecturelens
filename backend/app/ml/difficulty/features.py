"""Feature engineering for concept-difficulty estimation.

Produces an interpretable feature vector per concept, optionally concatenated
with the dense LSA embedding for the neural model.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np

from app.ml.preprocessing.clean import sentence_split

# A compact technical lexicon + morphology cues (domain-agnostic-ish).
_TECH_LEXICON = set(
    """algorithm complexity asymptotic invariant theorem lemma proof recursion recursive iteration
    pointer allocation heap stack queue hash boolean vector matrix gradient probability entropy
    variance derivative integral polynomial logarithm exponential concurrency deadlock mutex
    semaphore throughput latency bandwidth kernel syscall paging segmentation cache coherence
    normalization regularization overfitting eigenvalue orthogonal manifold optimization
    complexity np-hard heuristic amortized""".split()
)
_TECH_SUFFIX_RE = re.compile(r"(tion|sion|ity|ism|ology|ivity|ance|ence|aic|oid)$", re.IGNORECASE)
_MATH_SYMBOL_RE = re.compile(r"[=<>±≤≥∑∏∫√∞θλμσ]|O\([^)]*\)|\b\d+\^\d+\b")

DIFFICULTY_FEATURE_NAMES = [
    "avg_sentence_len",
    "max_sentence_len",
    "mean_word_len",
    "long_word_ratio",
    "type_token_ratio",
    "technical_term_ratio",
    "math_symbol_density",
    "concept_frequency",
    "concept_name_length",
    "dependency_count",
    "dependency_ratio",
    "snippet_length",
    "rare_capitalised_ratio",
]


@dataclass
class DifficultyContext:
    """Lecture-level context needed to compute relational features."""

    all_concept_names: list[str]
    lecture_text_lower: str


def _syllable_ish(word: str) -> int:
    return max(1, len(re.findall(r"[aeiouy]+", word.lower())))


def difficulty_features(
    name: str, snippet: str, ctx: DifficultyContext
) -> np.ndarray:
    text = f"{name}. {snippet}".strip()
    sentences = sentence_split(snippet) or [snippet]
    words = re.findall(r"[A-Za-z][A-Za-z\-']+", text)
    n_words = max(len(words), 1)
    lower_words = [w.lower() for w in words]

    sent_lens = [len(re.findall(r"\S+", s)) for s in sentences] or [0]
    long_words = sum(1 for w in words if len(w) >= 8 or _syllable_ish(w) >= 4)
    technical = sum(
        1 for w in lower_words if w in _TECH_LEXICON or _TECH_SUFFIX_RE.search(w)
    )
    math_hits = len(_MATH_SYMBOL_RE.findall(text))

    other_names = [n.lower() for n in ctx.all_concept_names if n.lower() != name.lower()]
    dependency_count = sum(1 for n in other_names if n and n in snippet.lower())
    concept_freq = ctx.lecture_text_lower.count(name.lower())
    rare_caps = sum(1 for w in words if w[:1].isupper() and w.lower() not in _TECH_LEXICON)

    feats = [
        float(np.mean(sent_lens)),
        float(np.max(sent_lens)),
        float(np.mean([len(w) for w in words])) if words else 0.0,
        long_words / n_words,
        len(set(lower_words)) / n_words,
        technical / n_words,
        math_hits / max(len(text) / 100.0, 1.0),
        math.log1p(concept_freq),
        len(name.split()),
        float(dependency_count),
        dependency_count / max(len(other_names), 1),
        math.log1p(len(snippet)),
        rare_caps / n_words,
    ]
    return np.array(feats, dtype=np.float32)


def build_difficulty_matrix(
    names: list[str],
    snippets: list[str],
    ctx: DifficultyContext,
    embeddings: np.ndarray | None = None,
) -> np.ndarray:
    base = np.vstack(
        [difficulty_features(n, s, ctx) for n, s in zip(names, snippets, strict=True)]
    ) if names else np.zeros((0, len(DIFFICULTY_FEATURE_NAMES)), dtype=np.float32)
    if embeddings is None:
        return base.astype(np.float32)
    return np.hstack([base, embeddings.astype(np.float32)]).astype(np.float32)
