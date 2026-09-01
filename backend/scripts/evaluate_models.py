"""Compare the scikit-learn baseline and the PyTorch model, head-to-head.

For each task (concept-type, difficulty) this trains both families on an
identical stratified split and reports accuracy / precision / recall / F1 /
confusion matrix on the held-out set. It also evaluates clustering quality on
the demo lectures and measures inference latency.

Output: a console report + ``models/evaluation_report.json``.

Run::

    python scripts/evaluate_models.py
    python scripts/evaluate_models.py --json-only
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # allow `python scripts/x.py`

import numpy as np
from sklearn.model_selection import train_test_split

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.ml.clustering import choose_k, get_clusterer
from app.ml.evaluation.latency import measure_latency
from app.ml.evaluation.metrics import classification_metrics, clustering_metrics
from app.ml.preprocessing import chunk_document, extract_document
from app.ml.sklearn_models import ALGORITHMS, SklearnTabularClassifier
from scripts._dataset import (
    DEMO_DIR,
    build_embedder,
    concept_dataset,
    difficulty_dataset,
)

logger = get_logger("evaluate")

try:
    from app.ml.torch_models import TorchTabularClassifier, TrainConfig

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    TORCH_AVAILABLE = False


def _evaluate_task(name: str, X: np.ndarray, y: np.ndarray, sklearn_algo: str) -> dict:
    classes = sorted(set(y))
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=7, stratify=y)

    skl = SklearnTabularClassifier(algorithm=sklearn_algo).fit(X_tr, y_tr)
    skl_pred = list(skl.predict(X_te))
    result = {
        "classes": classes,
        "n_train": int(len(X_tr)),
        "n_test": int(len(X_te)),
        "sklearn": {
            "algorithm": sklearn_algo,
            "metrics": classification_metrics(list(y_te), skl_pred, classes),
            "latency": measure_latency(
                lambda row: skl.predict(row.reshape(1, -1)), list(X_te), repeats=3
            ),
        },
    }
    if TORCH_AVAILABLE:
        torch_clf = TorchTabularClassifier(
            classes=classes, config=TrainConfig(max_epochs=120)
        ).fit(X_tr, y_tr)
        torch_pred = list(torch_clf.predict(X_te))
        result["pytorch"] = {
            "metrics": classification_metrics(list(y_te), torch_pred, classes),
            "latency": measure_latency(
                lambda row: torch_clf.predict(row.reshape(1, -1)), list(X_te), repeats=3
            ),
            "history": torch_clf.history,
        }
    else:
        result["pytorch"] = {"skipped": "torch not installed"}
    return result


def _evaluate_clustering(embedder) -> list[dict]:
    from app.ml.classification.concept_extractor import ConceptExtractor

    results = []
    for file in sorted(DEMO_DIR.glob("*")):
        if file.suffix.lower() not in {".md", ".txt"}:
            continue
        doc = extract_document(file, file_name=file.name)
        chunks = chunk_document(doc)
        concepts = ConceptExtractor(max_concepts=40).extract(chunks)
        if len(concepts) < 4:
            continue
        emb = embedder.transform([f"{c.name}. {c.snippet}" for c in concepts])
        per_algo = {}
        k = choose_k(emb)
        for algo in ("kmeans", "agglomerative", "dbscan"):
            try:
                labels = get_clusterer(algo, n_clusters=k).fit_predict(emb)
                per_algo[algo] = clustering_metrics(emb, labels)
            except Exception as exc:  # pragma: no cover - defensive
                per_algo[algo] = {"error": str(exc)}
        results.append(
            {
                "lecture": file.stem,
                "n_concepts": len(concepts),
                "chosen_k": k,
                "algorithms": per_algo,
            }
        )
    return results


def _print_report(report: dict) -> None:
    print("\n" + "=" * 72)
    print("LectureLens - Model Evaluation Report")
    print("=" * 72)
    for task, data in report["classification"].items():
        print(f"\n### {task}  (train={data['n_train']}, test={data['n_test']})")
        skl_m = data["sklearn"]["metrics"]
        torch_m = data["pytorch"].get("metrics")
        header = f"{'metric':<16}{'sklearn':>12}{'pytorch':>12}"
        print(header)
        print("-" * len(header))
        for metric in ("accuracy", "precision_macro", "recall_macro", "f1_macro"):
            tv = f"{torch_m[metric]:>12.3f}" if torch_m else f"{'n/a':>12}"
            print(f"{metric:<16}{skl_m[metric]:>12.3f}{tv}")
        tl = (
            f"{data['pytorch']['latency']['p95_ms']:>12.2f}"
            if torch_m
            else f"{'n/a':>12}"
        )
        print(f"{'p95 latency ms':<16}{data['sklearn']['latency']['p95_ms']:>12.2f}{tl}")
        if torch_m:
            winner = "pytorch" if torch_m["f1_macro"] >= skl_m["f1_macro"] else "sklearn"
            print(f"  -> winner by macro-F1: {winner}")
        else:
            print("  -> pytorch skipped (torch not installed)")

    print("\n### clustering (demo lectures)")
    for entry in report["clustering"]:
        print(f"  {entry['lecture']}: {entry['n_concepts']} concepts, k={entry['chosen_k']}")
        for algo, m in entry["algorithms"].items():
            sil = m.get("silhouette")
            print(f"    {algo:<14} silhouette={sil if sil is None else round(sil, 3)} "
                  f"clusters={m.get('n_clusters')}")
    print("\nFull JSON written to:", report["_output_path"])
    print("=" * 72 + "\n")


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--sklearn-algo", default="gradient_boosting", choices=ALGORITHMS)
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument(
        "--output", default=str(settings.models_dir / "evaluation_report.json")
    )
    args = parser.parse_args()

    logger.info("Building embedder ...")
    embedder = build_embedder()

    report: dict = {
        "generated_at": datetime.utcnow().isoformat(),
        "embedding_dim": embedder.dim,
        "classification": {},
        "clustering": [],
    }

    Xc, yc = concept_dataset(embedder)
    report["classification"]["concept_classifier"] = _evaluate_task(
        "concept_classifier", Xc, yc, args.sklearn_algo
    )
    Xd, yd = difficulty_dataset(embedder)
    report["classification"]["difficulty"] = _evaluate_task(
        "difficulty", Xd, yd, args.sklearn_algo
    )
    report["clustering"] = _evaluate_clustering(embedder)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    report["_output_path"] = str(out_path)

    if not args.json_only:
        _print_report(report)
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
