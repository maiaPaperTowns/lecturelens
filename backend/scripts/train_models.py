"""Train and persist the LectureLens models.

Produces, under ``MODELS_DIR``:

* ``embeddings/embedder.joblib``          - TF-IDF + SVD text encoder
* ``concept_classifier/`` sklearn + torch models  + ``metadata.json``
* ``difficulty/`` sklearn + torch models          + ``metadata.json``

The active model for each task is chosen by held-out macro-F1.

Run::

    python scripts/train_models.py                 # train everything
    python scripts/train_models.py --sklearn-algo random_forest
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # allow `python scripts/x.py`

import numpy as np
from sklearn.model_selection import train_test_split

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.ml.evaluation.metrics import classification_metrics
from app.ml.registry import get_registry
from app.ml.sklearn_models import SklearnTabularClassifier
from scripts._dataset import build_embedder, concept_dataset, difficulty_dataset

logger = get_logger("train")

try:
    from app.ml.torch_models import TorchTabularClassifier, TrainConfig

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover - torch is optional for baseline-only training
    TORCH_AVAILABLE = False

    class TrainConfig:  # type: ignore[no-redef]
        def __init__(self, **_: object) -> None: ...


def _train_task(
    task: str,
    X: np.ndarray,
    y: np.ndarray,
    sklearn_algo: str,
    torch_cfg: TrainConfig,
) -> dict:
    classes = sorted(set(y))
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    models_dir = settings.models_dir / task
    models_dir.mkdir(parents=True, exist_ok=True)
    trained_at = datetime.utcnow().isoformat()
    versions: dict[str, dict] = {}

    # --- scikit-learn baseline -------------------------------------------------
    skl = SklearnTabularClassifier(algorithm=sklearn_algo).fit(X_tr, y_tr)
    skl_metrics = classification_metrics(list(y_te), list(skl.predict(X_te)), classes)
    skl.save(models_dir / f"sklearn_{sklearn_algo}.joblib")
    versions[f"sklearn-{sklearn_algo}"] = {
        "family": "sklearn",
        "artifact": f"sklearn_{sklearn_algo}.joblib",
        "trained_at": trained_at,
        "metrics": skl_metrics,
        "use_embeddings": True,
    }
    logger.info("[%s] sklearn(%s) macro-F1=%.3f", task, sklearn_algo, skl_metrics["f1_macro"])

    # --- PyTorch neural classifier ------------------------------------------
    if TORCH_AVAILABLE:
        torch_clf = TorchTabularClassifier(classes=classes, config=torch_cfg).fit(X_tr, y_tr)
        torch_metrics = classification_metrics(list(y_te), list(torch_clf.predict(X_te)), classes)
        torch_clf.save(models_dir / "pytorch_mlp.pt")
        versions["pytorch-mlp-v1"] = {
            "family": "pytorch",
            "artifact": "pytorch_mlp.pt",
            "trained_at": trained_at,
            "metrics": torch_metrics,
            "use_embeddings": True,
        }
        logger.info("[%s] pytorch  macro-F1=%.3f", task, torch_metrics["f1_macro"])
    else:
        logger.warning("[%s] torch not installed - skipping neural model, baseline stays active", task)

    # --- pick the active model --------------------------------------------
    active = max(versions.items(), key=lambda kv: kv[1]["metrics"]["f1_macro"])[0]
    metadata = {"name": task, "active": active, "versions": versions}
    get_registry().write_metadata(task, metadata)
    logger.info("[%s] active -> %s", task, active)
    return metadata


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Train LectureLens models")
    parser.add_argument(
        "--sklearn-algo",
        default="gradient_boosting",
        choices=("logreg", "random_forest", "gradient_boosting"),
    )
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--embedding-dim", type=int, default=settings.embedding_dim)
    args = parser.parse_args()

    settings.models_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Fitting text embedder (dim=%d) ...", args.embedding_dim)
    embedder = build_embedder(dim=args.embedding_dim)
    embedder.save(settings.models_dir / "embeddings")
    logger.info("Embedder saved (effective dim=%d).", embedder.dim)

    torch_cfg = TrainConfig(max_epochs=args.epochs)

    logger.info("== Concept-type classifier ==")
    X_c, y_c = concept_dataset(embedder)
    _train_task("concept_classifier", X_c, y_c, args.sklearn_algo, torch_cfg)

    logger.info("== Difficulty classifier ==")
    X_d, y_d = difficulty_dataset(embedder)
    _train_task("difficulty", X_d, y_d, args.sklearn_algo, torch_cfg)

    get_registry().reload()
    logger.info("Training complete. Artifacts in %s", settings.models_dir)


if __name__ == "__main__":
    main()
