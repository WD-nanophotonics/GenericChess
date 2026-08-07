"""Pair-level arena statistics (bootstrap CI on paired scores)."""

from __future__ import annotations

import random


def bootstrap_pair_mean_ci(
    pair_scores,
    *,
    confidence: float = 0.95,
    resamples: int = 10_000,
    seed: int = 271828,
):
    """Bootstrap confidence interval for the mean of paired scores.

    Sampling unit is a pair (never an individual game).  Returns
    ``(low, high)`` percentiles (default 2.5 / 97.5).  Deterministic for a
    fixed ``seed``.
    """
    if not pair_scores:
        raise ValueError("pair_scores must be non-empty")
    if not (0.0 < confidence < 1.0):
        raise ValueError("confidence must be in (0, 1)")
    alpha = (1.0 - confidence) / 2.0
    rng = random.Random(seed)
    n = len(pair_scores)
    means = []
    for _ in range(resamples):
        total = 0.0
        for _ in range(n):
            total += pair_scores[rng.randrange(n)]
        means.append(total / n)
    means.sort()
    lo = means[int(alpha * resamples)]
    hi = means[min(resamples - 1, int((1.0 - alpha) * resamples))]
    return lo, hi
