"""Dense text embeddings via TF-IDF + Truncated SVD (Latent Semantic Analysis).

This deliberately avoids any external embedding API: it is a fully offline,
deterministic representation trained on the project corpus. It is good enough
for concept relevance ranking, clustering, and 2-D projection, and it doubles
as the feature backbone for the PyTorch classifiers.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import Normalizer

from app.core.logging import get_logger

logger = get_logger(__name__)

_ARTIFACT_NAME = "embedder.joblib"


@dataclass
class EmbedderMeta:
    dim: int
    vocab_size: int
    n_docs_fitted: int


class TextEmbedder:
    """Fit/transform wrapper around a TF-IDF -> SVD -> L2-normalise pipeline."""

    def __init__(self, dim: int = 128, min_df: int = 1, ngram_range: tuple[int, int] = (1, 2)):
        self.dim = dim
        self.min_df = min_df
        self.ngram_range = ngram_range
        self._pipe: Pipeline | None = None
        self.meta: EmbedderMeta | None = None

    # -- lifecycle ---------------------------------------------------------
    @property
    def is_fitted(self) -> bool:
        return self._pipe is not None

    def fit(self, documents: list[str]) -> TextEmbedder:
        docs = [d for d in documents if d and d.strip()]
        if len(docs) < 2:
            docs = docs + ["placeholder document one", "placeholder document two"]
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=self.ngram_range,
            min_df=min(self.min_df, len(docs)),
            max_df=0.95,
            sublinear_tf=True,
        )
        tfidf = vectorizer.fit_transform(docs)
        n_features = tfidf.shape[1]
        components = max(2, min(self.dim, n_features - 1, len(docs) - 1))
        svd = TruncatedSVD(n_components=components, random_state=42)
        self._pipe = Pipeline(
            [("tfidf", vectorizer), ("svd", svd), ("norm", Normalizer(copy=False))]
        )
        # vectorizer already fitted; re-fit the whole pipe for a clean state
        self._pipe.fit(docs)
        self.dim = components
        self.meta = EmbedderMeta(dim=components, vocab_size=n_features, n_docs_fitted=len(docs))
        logger.info(
            "TextEmbedder fitted: dim=%d vocab=%d docs=%d", components, n_features, len(docs)
        )
        return self

    def transform(self, texts: list[str]) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("TextEmbedder must be fitted or loaded before transform().")
        safe = [t if (t and t.strip()) else " " for t in texts]
        return np.asarray(self._pipe.transform(safe), dtype=np.float32)

    def fit_transform(self, documents: list[str]) -> np.ndarray:
        return self.fit(documents).transform(documents)

    # -- persistence -----------------------------------------------------
    def save(self, directory: str | Path) -> Path:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / _ARTIFACT_NAME
        joblib.dump({"pipe": self._pipe, "dim": self.dim, "meta": self.meta}, path)
        return path

    @classmethod
    def load(cls, directory: str | Path) -> TextEmbedder:
        path = Path(directory) / _ARTIFACT_NAME
        if not path.exists():
            raise FileNotFoundError(f"No embedder artifact at {path}")
        blob = joblib.load(path)
        obj = cls(dim=blob["dim"])
        obj._pipe = blob["pipe"]
        obj.meta = blob.get("meta")
        return obj

    @classmethod
    def load_or_fit(cls, directory: str | Path, corpus: list[str], dim: int = 128) -> TextEmbedder:
        try:
            return cls.load(directory)
        except FileNotFoundError:
            logger.warning("No embedder found in %s; fitting an ad-hoc embedder.", directory)
            return cls(dim=dim).fit(corpus)
