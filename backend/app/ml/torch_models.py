"""Reusable PyTorch components shared by the concept and difficulty classifiers.

A small but genuine neural net: a configurable MLP with batch-norm + dropout,
trained with Adam + cross-entropy and early stopping on a validation split.
Wrapped in a scikit-learn-style estimator so it is a drop-in alternative to the
sklearn baselines and can be compared head-to-head by ``evaluate_models.py``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from app.core.logging import get_logger

logger = get_logger(__name__)

torch.manual_seed(42)
np.random.seed(42)


class MLPClassifier(nn.Module):
    """Feed-forward classifier: [Linear -> BatchNorm -> ReLU -> Dropout] x N -> Linear."""

    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden_dims: tuple[int, ...] = (256, 128),
        dropout: float = 0.3,
    ):
        super().__init__()
        layers: list[nn.Module] = []
        prev = input_dim
        for h in hidden_dims:
            layers += [nn.Linear(prev, h), nn.BatchNorm1d(h), nn.ReLU(), nn.Dropout(dropout)]
            prev = h
        layers.append(nn.Linear(prev, num_classes))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


@dataclass
class TrainConfig:
    hidden_dims: tuple[int, ...] = (256, 128)
    dropout: float = 0.3
    lr: float = 1e-3
    weight_decay: float = 1e-4
    batch_size: int = 32
    max_epochs: int = 120
    patience: int = 15
    val_fraction: float = 0.2


@dataclass
class TorchTabularClassifier:
    """scikit-learn-flavoured wrapper around :class:`MLPClassifier`."""

    classes: list[str]
    config: TrainConfig = field(default_factory=TrainConfig)
    model: MLPClassifier | None = None
    input_dim: int | None = None
    history: dict = field(default_factory=dict)

    # -- training --------------------------------------------------------
    def fit(self, X: np.ndarray, y: np.ndarray) -> TorchTabularClassifier:
        X = np.asarray(X, dtype=np.float32)
        y_idx = self._encode(y)
        self.input_dim = X.shape[1]

        rng = np.random.default_rng(42)
        perm = rng.permutation(len(X))
        n_val = max(1, int(len(X) * self.config.val_fraction)) if len(X) > 10 else 0
        val_idx, train_idx = perm[:n_val], perm[n_val:]

        class_counts = np.bincount(y_idx[train_idx], minlength=len(self.classes)).astype(np.float32)
        weights = torch.tensor(
            (class_counts.sum() / np.clip(class_counts, 1, None)), dtype=torch.float32
        )

        model = MLPClassifier(
            self.input_dim, len(self.classes), self.config.hidden_dims, self.config.dropout
        )
        opt = torch.optim.Adam(
            model.parameters(), lr=self.config.lr, weight_decay=self.config.weight_decay
        )
        loss_fn = nn.CrossEntropyLoss(weight=weights)

        train_ds = TensorDataset(
            torch.from_numpy(X[train_idx]), torch.from_numpy(y_idx[train_idx])
        )
        loader = DataLoader(
            train_ds, batch_size=min(self.config.batch_size, len(train_ds)), shuffle=True
        )

        best_state, best_metric, bad_epochs = None, -1.0, 0
        train_losses: list[float] = []
        for _epoch in range(self.config.max_epochs):
            model.train()
            epoch_loss = 0.0
            for xb, yb in loader:
                opt.zero_grad()
                loss = loss_fn(model(xb), yb)
                loss.backward()
                opt.step()
                epoch_loss += loss.item() * len(xb)
            train_losses.append(epoch_loss / len(train_ds))

            metric = self._eval_accuracy(
                model, X[val_idx], y_idx[val_idx]
            ) if n_val else -train_losses[-1]
            if metric > best_metric + 1e-4:
                best_metric, best_state, bad_epochs = metric, model.state_dict(), 0
            else:
                bad_epochs += 1
                if bad_epochs >= self.config.patience:
                    break

        if best_state is not None:
            model.load_state_dict(best_state)
        model.eval()
        self.model = model
        self.history = {
            "epochs_trained": len(train_losses),
            "final_train_loss": train_losses[-1] if train_losses else None,
            "best_val_metric": best_metric,
        }
        logger.info("Torch classifier trained: %s", self.history)
        return self

    # -- inference ------------------------------------------------------
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        self._require_model()
        X = np.asarray(X, dtype=np.float32)
        with torch.no_grad():
            logits = self.model(torch.from_numpy(X))
            return torch.softmax(logits, dim=1).cpu().numpy()

    def predict(self, X: np.ndarray) -> np.ndarray:
        proba = self.predict_proba(X)
        return np.array([self.classes[i] for i in proba.argmax(axis=1)])

    # -- persistence --------------------------------------------------
    def save(self, path: str | Path) -> Path:
        self._require_model()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dict": self.model.state_dict(),
                "classes": self.classes,
                "input_dim": self.input_dim,
                "config": self.config.__dict__,
                "history": self.history,
            },
            path,
        )
        path.with_suffix(".json").write_text(
            json.dumps({"classes": self.classes, "input_dim": self.input_dim, **self.history}, indent=2)
        )
        return path

    @classmethod
    def load(cls, path: str | Path) -> TorchTabularClassifier:
        blob = torch.load(Path(path), map_location="cpu")
        cfg = TrainConfig(**blob["config"])
        obj = cls(classes=list(blob["classes"]), config=cfg)
        obj.input_dim = blob["input_dim"]
        model = MLPClassifier(obj.input_dim, len(obj.classes), cfg.hidden_dims, cfg.dropout)
        model.load_state_dict(blob["state_dict"])
        model.eval()
        obj.model = model
        obj.history = blob.get("history", {})
        return obj

    # -- helpers -----------------------------------------------------
    def _encode(self, y: np.ndarray) -> np.ndarray:
        index = {c: i for i, c in enumerate(self.classes)}
        return np.array([index[str(v)] for v in y], dtype=np.int64)

    @staticmethod
    def _eval_accuracy(model: nn.Module, X: np.ndarray, y_idx: np.ndarray) -> float:
        if len(X) == 0:
            return 0.0
        model.eval()
        with torch.no_grad():
            pred = model(torch.from_numpy(np.asarray(X, dtype=np.float32))).argmax(1).numpy()
        return float((pred == y_idx).mean())

    def _require_model(self) -> None:
        if self.model is None:
            raise RuntimeError("Model is not trained/loaded.")
