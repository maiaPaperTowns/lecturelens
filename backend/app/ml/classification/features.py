"""Feature extraction for concept-type classification.

Features = dense LSA embedding  ++  hand-crafted lexical-cue features.
The lexical cues encode the linguistic signals that distinguish a
"definition" from an "example" from a "process", etc.
"""
from __future__ import annotations

import re

import numpy as np

CUE_PATTERNS: dict[str, list[str]] = {
    "def": [
        r"\bis defined as\b", r"\brefers to\b", r"\bis a\b", r"\bare\b .*\bthat\b",
        r"\bmeans\b", r"\bknown as\b", r"\bdenotes?\b", r"\bterm(?:inology)?\b",
    ],
    "example": [
        r"\bfor example\b", r"\bfor instance\b", r"\be\.g\.\b", r"\bsuch as\b",
        r"\bconsider (?:the|a|an)\b", r"\bimagine\b", r"\bsuppose\b",
    ],
    "theorem": [
        r"\btheorem\b", r"\blemma\b", r"\bcorollary\b", r"\bproof\b", r"\bif and only if\b",
        r"\bproperty\b", r"\bguarantees?\b", r"\binvariant\b", r"\bmust\b", r"\balways\b",
    ],
    "process": [
        r"\bstep \d\b", r"\bfirst,\b", r"\bthen\b", r"\bnext,\b", r"\bfinally,\b",
        r"\balgorithm\b", r"\bprocedure\b", r"\brepeat\b", r"\buntil\b", r"\biterat",
    ],
    "comparison": [
        r"\bversus\b", r"\bvs\.?\b", r"\bcompared to\b", r"\bwhereas\b", r"\bunlike\b",
        r"\bin contrast\b", r"\btrade-?off\b", r"\bbetter than\b", r"\bslower than\b",
    ],
    "impl": [
        r"\bO\([^)]+\)", r"\bcomplexity\b", r"\bimplementation\b", r"\bcode\b", r"\bfunction\b",
        r"\breturn\b", r"\bpseudocode\b", r"\bpointer\b", r"\barray\b", r"[{}();]=?",
    ],
    "background": [
        r"\bhistor", r"\bin \d{4}\b", r"\boriginally\b", r"\bmotivation\b", r"\bcontext\b",
        r"\boverview\b", r"\bintroduction\b", r"\bwe will\b", r"\bthis lecture\b",
    ],
}

_COMPILED = {k: [re.compile(p, re.IGNORECASE) for p in pats] for k, pats in CUE_PATTERNS.items()}

LEXICAL_FEATURE_NAMES = [
    *[f"cue_{k}" for k in CUE_PATTERNS],
    "len_words",
    "avg_word_len",
    "digit_ratio",
    "punct_symbol_ratio",
    "capitalised_ratio",
    "starts_capitalised_phrase",
    "has_colon_definition",
]


def lexical_features(text: str) -> np.ndarray:
    t = text or ""
    lower = t.lower()
    words = re.findall(r"[A-Za-z']+", t)
    n_words = max(len(words), 1)

    cue_counts = [
        sum(bool(rx.search(lower)) for rx in rxs) / len(rxs) for rxs in _COMPILED.values()
    ]
    avg_word_len = float(np.mean([len(w) for w in words])) if words else 0.0
    digit_ratio = sum(c.isdigit() for c in t) / max(len(t), 1)
    symbol_ratio = len(re.findall(r"[{}()\[\];:=<>/*+]", t)) / max(len(t), 1)
    capitalised = sum(1 for w in words if w[:1].isupper()) / n_words
    starts_phrase = 1.0 if re.match(r"^[A-Z][a-zA-Z]+(?:\s+[a-z]+){0,3}\s+(is|are|refers)", t) else 0.0
    has_colon_def = 1.0 if re.search(r"^[A-Z][\w\s-]{2,40}:\s+\w", t) else 0.0

    return np.array(
        [
            *cue_counts,
            min(n_words / 60.0, 2.0),
            avg_word_len / 10.0,
            digit_ratio,
            symbol_ratio,
            capitalised,
            starts_phrase,
            has_colon_def,
        ],
        dtype=np.float32,
    )


def build_feature_matrix(texts: list[str], embeddings: np.ndarray) -> np.ndarray:
    """Concatenate [embedding | lexical] features for a batch of texts."""
    if texts:
        lex = np.vstack([lexical_features(t) for t in texts])
    else:
        lex = np.zeros((0, len(LEXICAL_FEATURE_NAMES)))
    if embeddings.shape[0] != lex.shape[0]:
        raise ValueError("embeddings and texts must have the same batch size")
    return np.hstack([embeddings.astype(np.float32), lex]).astype(np.float32)
