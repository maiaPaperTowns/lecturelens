"""scikit-learn baseline classifiers (shared by concept-type + difficulty tasks)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ALGORITHMS = ("logreg", "random_forest", "gradient_boosting")


def _make_estimator(algorithm: str):
    if algorithm == "logreg":
        return LogisticRegression(max_iter=1000, class_weight="balanced", C=1.0)
    if algorithm == "random_forest":
        return RandomForestClassifier(
            n_estimators=300, max_depth=None, class_weight="balanced", random_state=42, n_jobs=-1
        )
    if algorithm == "gradient_boosting":
        return GradientBoostingClassifier(random_state=42)
    raise ValueError(f"Unknown algorithm '{algorithm}'. Choose from {ALGORITHMS}.")


@dataclass
class SklearnTabularClassifier:
    algorithm: str = "logreg"
    classes: list[str] = field(default_factory=list)
    pipeline: Pipeline | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> SklearnTabularClassifier:
        X = np.asarray(X, dtype=np.float64)
        self.classes = sorted(set(map(str, y)))
        self.pipeline = Pipeline(
            [("scaler", StandardScaler()), ("clf", _make_estimator(self.algorithm))]
        )
        self.pipeline.fit(X, np.asarray(list(map(str, y))))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        self._require()
        return self.pipeline.predict(np.asarray(X, dtype=np.float64))

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        self._require()
        proba = self.pipeline.predict_proba(np.asarray(X, dtype=np.float64))
        # align columns to self.classes ordering
        model_classes = list(self.pipeline.named_steps["clf"].classes_)
        order = [model_classes.index(c) for c in self.classes]
        return proba[:, order]

    def save(self, path: str | Path) -> Path:
        self._require()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"algorithm": self.algorithm, "classes": self.classes, "pipeline": self.pipeline}, path
        )
        return path

    @classmethod
    def load(cls, path: str | Path) -> SklearnTabularClassifier:
        blob = joblib.load(Path(path))
        obj = cls(algorithm=blob["algorithm"], classes=blob["classes"])
        obj.pipeline = blob["pipeline"]
        return obj

    def _require(self) -> None:
        if self.pipeline is None:
            raise RuntimeError("Model is not trained/loaded.")
