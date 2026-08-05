"""Evaluation hyperparameters (generic; no chess-specific knowledge)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib

from ...rules.schema import canonical_json


MATE_SCORE = 1_000_000_000
MATE_THRESHOLD = 900_000_000
MAX_STATIC_EVAL = 10_000_000


@dataclass(frozen=True, slots=True)
class EvaluationConfig:
    """Universal evaluation weights and analysis parameters.

    These are generic hyper-parameters derived from the rules themselves;
    they encode no knowledge about any specific traditional game.
    """

    density_points: tuple[float, ...] = (0.0, 0.125, 0.25, 0.375, 0.5)
    density_weights: tuple[float, ...] = (0.25, 0.2, 0.2, 0.18, 0.17)
    coverage_weight: float = 0.10
    reachability_weight: float = 0.05
    path_efficiency_weight: float = 0.05
    hand_weight: float = 0.9
    dynamic_mobility_weight: int = 2
    anchor_escape_weight: int = 5
    promotion_potential_weight: int = 3
    normal_piece_median_value: int = 1000
    mc_samples: int = 64
    evaluator_version: str = "generic-v1"


def config_hash(config: EvaluationConfig) -> str:
    raw = canonical_json(asdict(config))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
