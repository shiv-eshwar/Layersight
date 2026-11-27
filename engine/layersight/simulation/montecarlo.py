"""Vectorized Monte Carlo and the closed form that checks it."""

from __future__ import annotations

import math

import numpy as np

LAYERS = ("email_filter", "user", "application_control", "antivirus", "segmentation")


def closed_form(p_stop: list[float]) -> float:
    product = 1.0
    for probability in p_stop:
        product *= 1.0 - probability
    return product


def wilson(passed: int, runs: int, z: float = 1.96) -> tuple[float, float]:
    if runs <= 0:
        return (0.0, 0.0)
    proportion = passed / runs
    z2 = z * z
    denom = 1.0 + z2 / runs
    center = (proportion + z2 / (2.0 * runs)) / denom
    spread = proportion * (1.0 - proportion) / runs + z2 / (4.0 * runs * runs)
    margin = z * math.sqrt(spread) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def uniforms(seed: int, email_sha256: str, runs: int) -> np.ndarray:
    digest = email_sha256[:16] or "0"
    sequence = np.random.SeedSequence([seed, int(digest, 16)])
    return np.random.default_rng(sequence).random((runs, len(LAYERS)))


def run(p_stop: np.ndarray, draws: np.ndarray) -> np.ndarray:
    """Counts of the first layer that stops each run. The last bin passed every layer."""
    stopped = draws < p_stop
    first = np.where(stopped.any(axis=1), stopped.argmax(axis=1), p_stop.size)
    return np.bincount(first, minlength=int(p_stop.size) + 1)
