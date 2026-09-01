"""Model registry: discovers, loads and caches trained ML artifacts.

Directory layout (``MODELS_DIR``)::

    models/
      embeddings/        embedder.joblib
      concept_classifier/ metadata.json  sklearn-v1.joblib  pytorch-v1.pt
      difficulty/         metadata.json  sklearn-v1.joblib  pytorch-v1.pt

``metadata.json`` records every trained version, its metrics and which one is
``active``. When no artifact is present the registry returns a documented
heuristic model so the application is fully functional before training.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.ml.classification.pipeline import ConceptTypeClassifier, HeuristicConceptTypeClassifier
from app.ml.difficulty.pipeline import DifficultyClassifier, HeuristicDifficultyClassifier
from app.ml.embeddings.encoder import TextEmbedder

logger = get_logger(__name__)


@dataclass
class ModelCard:
    name: str
    family: str
    version: str
    trained_at: str | None
    metrics: dict
    is_active: bool
    artifact_path: str | None


class ModelRegistry:
    def __init__(self, models_dir: Path | None = None):
        self.models_dir = Path(models_dir or settings.models_dir)
        self._cache: dict[str, object] = {}

    # -- paths ----------------------------------------------------------
    def _dir(self, name: str) -> Path:
        return self.models_dir / name

    def _metadata(self, name: str) -> dict:
        path = self._dir(name) / "metadata.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            logger.warning("Corrupt metadata.json for %s", name)
            return {}

    # -- embedder -----------------------------------------------------
    def get_embedder(self, corpus_fallback: list[str] | None = None) -> TextEmbedder:
        if "embedder" in self._cache:
            return self._cache["embedder"]  # type: ignore[return-value]
        try:
            embedder = TextEmbedder.load(self._dir("embeddings"))
            logger.info("Loaded embedder from registry (dim=%s)", embedder.dim)
        except FileNotFoundError:
            corpus = corpus_fallback or ["placeholder text a", "placeholder text b"]
            embedder = TextEmbedder(dim=settings.embedding_dim).fit(corpus)
            logger.warning("No trained embedder; using ad-hoc embedder (dim=%s)", embedder.dim)
        self._cache["embedder"] = embedder
        return embedder

    # -- classifiers -----------------------------------------------
    def _load_estimator(self, name: str, family: str, artifact: str):
        path = self._dir(name) / artifact
        if family == "pytorch":
            from app.ml.torch_models import TorchTabularClassifier  # lazy: torch optional

            return TorchTabularClassifier.load(path)
        if family == "sklearn":
            from app.ml.sklearn_models import SklearnTabularClassifier

            return SklearnTabularClassifier.load(path)
        raise ValueError(f"Unknown model family '{family}'")

    def get_concept_classifier(self):
        if "concept_classifier" in self._cache:
            return self._cache["concept_classifier"]
        meta = self._metadata("concept_classifier")
        active = meta.get("active")
        versions = meta.get("versions", {})
        if active and active in versions:
            spec = versions[active]
            try:
                estimator = self._load_estimator("concept_classifier", spec["family"], spec["artifact"])
                clf = ConceptTypeClassifier(
                    estimator, self.get_embedder(), spec["family"], active
                )
                logger.info("Concept classifier: %s (%s)", active, spec["family"])
                self._cache["concept_classifier"] = clf
                return clf
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Failed to load concept classifier %s: %s", active, exc)
        clf = HeuristicConceptTypeClassifier()
        self._cache["concept_classifier"] = clf
        return clf

    def get_difficulty_classifier(self):
        if "difficulty" in self._cache:
            return self._cache["difficulty"]
        meta = self._metadata("difficulty")
        active = meta.get("active")
        versions = meta.get("versions", {})
        if active and active in versions:
            spec = versions[active]
            try:
                estimator = self._load_estimator("difficulty", spec["family"], spec["artifact"])
                clf = DifficultyClassifier(
                    estimator,
                    self.get_embedder(),
                    spec["family"],
                    active,
                    use_embeddings=spec.get("use_embeddings", True),
                )
                logger.info("Difficulty classifier: %s (%s)", active, spec["family"])
                self._cache["difficulty"] = clf
                return clf
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Failed to load difficulty classifier %s: %s", active, exc)
        clf = HeuristicDifficultyClassifier()
        self._cache["difficulty"] = clf
        return clf

    # -- introspection ---------------------------------------------
    def list_model_cards(self) -> list[ModelCard]:
        cards: list[ModelCard] = []
        for name in ("concept_classifier", "difficulty"):
            meta = self._metadata(name)
            active = meta.get("active")
            versions = meta.get("versions", {})
            if not versions:
                heuristic = (
                    HeuristicConceptTypeClassifier()
                    if name == "concept_classifier"
                    else HeuristicDifficultyClassifier()
                )
                cards.append(
                    ModelCard(name, "heuristic", heuristic.version, None, {}, True, None)
                )
                continue
            for version, spec in versions.items():
                cards.append(
                    ModelCard(
                        name=name,
                        family=spec.get("family", "unknown"),
                        version=version,
                        trained_at=spec.get("trained_at"),
                        metrics=spec.get("metrics", {}),
                        is_active=(version == active),
                        artifact_path=spec.get("artifact"),
                    )
                )
        return cards

    def write_metadata(self, name: str, metadata: dict) -> Path:
        directory = self._dir(name)
        directory.mkdir(parents=True, exist_ok=True)
        metadata.setdefault("updated_at", datetime.utcnow().isoformat())
        path = directory / "metadata.json"
        path.write_text(json.dumps(metadata, indent=2))
        return path

    def reload(self) -> None:
        self._cache.clear()


_registry: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
