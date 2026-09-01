"""Shared ML result types."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Prediction:
    label: str
    confidence: float
    score: float | None = None
    model_name: str = "unknown"
    model_version: str = "0"
    latency_ms: float | None = None
