"""Inference latency measurement helpers."""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import numpy as np


def measure_latency(
    fn: Callable[[Any], Any], inputs: list[Any], *, warmup: int = 3, repeats: int = 1
) -> dict:
    """Call ``fn`` once per input (optionally repeated) and summarise wall-clock latency."""
    for sample in inputs[:warmup]:
        fn(sample)

    timings_ms: list[float] = []
    for _ in range(max(repeats, 1)):
        for sample in inputs:
            start = time.perf_counter()
            fn(sample)
            timings_ms.append((time.perf_counter() - start) * 1000.0)

    arr = np.array(timings_ms) if timings_ms else np.array([0.0])
    return {
        "n_calls": int(len(timings_ms)),
        "mean_ms": round(float(arr.mean()), 3),
        "p50_ms": round(float(np.percentile(arr, 50)), 3),
        "p95_ms": round(float(np.percentile(arr, 95)), 3),
        "max_ms": round(float(arr.max()), 3),
    }
