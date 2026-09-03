"""Learnable material weights and checkpoints (RuleSet-specific)."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from .features import (
    DYNAMIC_FEATURE_NAMES,
    SPATIAL_CELL_COUNT,
    non_anchor_type_ids,
)
from .serialization import stable_sha256

MATERIAL_SCALE = 1.0  # historical material-only scale; semantic v2 uses 256
SEMANTIC_NATIVE_SCALE = 256
SCHEMA_VERSION = 2


class LearningNumericalError(ValueError):
    """Raised when training produces numerically invalid weights."""


def _median_abs(values: list[float]) -> float:
    ordered = sorted(abs(v) for v in values)
    if not ordered:
        return 0.0
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


@dataclass(frozen=True, slots=True)
class LearnableMaterialCheckpoint:
    """Frozen evaluation checkpoint for one RuleSet."""

    schema_version: int = SCHEMA_VERSION
    ruleset_fingerprint: str = ""
    evaluation_profile_version: str = ""
    generation: int = 0
    parent_checkpoint_id: str | None = None
    created_at: str = ""
    training_config_hash: str = ""
    board_weights: dict[str, float] = field(default_factory=dict)
    hand_weights: dict[str, float] = field(default_factory=dict)
    material_scale: float = MATERIAL_SCALE
    value_scale: float = 1.0
    reference_median: float = 0.0
    w_max: float = 100_000.0
    games_seen: int = 0
    positions_seen: int = 0
    training_updates: int = 0
    training_seed: int | None = None
    promoted_to_champion: bool = False
    # Appended to preserve the positional field order of material-only v1.
    dynamic_weights: dict[str, float] = field(default_factory=dict)
    # Optional v3 additive representation.  Spatial tables include anchors;
    # each nine-cell row is a zero-sum location residual, so it cannot absorb
    # the constant material direction.
    spatial_occupancy_weights: dict[str, tuple[float, ...]] = field(default_factory=dict)
    localized_control_weights: tuple[float, ...] = ()

    # ------------------------------------------------------------------ ids

    @property
    def checkpoint_id(self) -> str:
        return stable_sha256(self._learning_state())

    def _learning_state(self) -> dict[str, Any]:
        state = {
            "schema_version": self.schema_version,
            "ruleset_fingerprint": self.ruleset_fingerprint,
            "evaluation_profile_version": self.evaluation_profile_version,
            "generation": self.generation,
            "parent_checkpoint_id": self.parent_checkpoint_id,
            "training_config_hash": self.training_config_hash,
            "board_weights": self.board_weights,
            "hand_weights": self.hand_weights,
            "material_scale": self.material_scale,
            "value_scale": self.value_scale,
            "reference_median": self.reference_median,
            "w_max": self.w_max,
            "games_seen": self.games_seen,
            "positions_seen": self.positions_seen,
            "training_updates": self.training_updates,
            "training_seed": self.training_seed,
            "promoted_to_champion": self.promoted_to_champion,
        }
        # Keep the serialized identity of historical material-only v1
        # checkpoints byte-for-byte stable.  v2 checkpoints opt in by
        # carrying a non-empty dynamic vector.
        if self.dynamic_weights:
            state["dynamic_weights"] = self.dynamic_weights
        if self.spatial_occupancy_weights:
            state["spatial_occupancy_weights"] = self.spatial_occupancy_weights
        if self.localized_control_weights:
            state["localized_control_weights"] = self.localized_control_weights
        return state

    @property
    def config_hash(self) -> str:
        """Distinct per checkpoint, so TT entries are never shared across
        evaluators (the experiment also creates a fresh engine per
        checkpoint)."""
        payload = {
                "checkpoint_id": self.checkpoint_id,
                "board_weights": self.board_weights,
                "hand_weights": self.hand_weights,
        }
        if self.dynamic_weights:
            payload["dynamic_weights"] = self.dynamic_weights
        if self.spatial_occupancy_weights:
            payload["spatial_occupancy_weights"] = self.spatial_occupancy_weights
        if self.localized_control_weights:
            payload["localized_control_weights"] = self.localized_control_weights
        return stable_sha256(payload)

    @property
    def evaluator_version(self) -> str:
        if self.spatial_occupancy_weights or self.localized_control_weights:
            return "learnable-generic-v3"
        return "learnable-generic-v2" if self.dynamic_weights else "learnable-material-v1"

    # ---------------------------------------------------------------- init

    @classmethod
    def from_profile(
        cls,
        compiled,
        profile,
        *,
        training_seed: int | None = None,
        generation: int = 0,
        parent_checkpoint_id: str | None = None,
        value_scale_factor: float = 4.0,
        w_max_factor: float = 10.0,
        dynamic_weights: dict[str, float] | None = None,
    ) -> "LearnableMaterialCheckpoint":
        type_ids = non_anchor_type_ids(compiled)
        board = {t: float(profile.board_value_by_type[t]) for t in type_ids}
        hand = {t: float(profile.hand_value_by_base_type[t]) for t in type_ids}
        median = _median_abs(list(board.values()))
        max_abs = max((abs(v) for v in board.values()), default=0.0)
        value_scale = max(median * value_scale_factor, max_abs)
        w_max = max(median * w_max_factor, 1.0)
        return cls(
            ruleset_fingerprint=compiled.ruleset_fingerprint,
            evaluation_profile_version=profile.evaluator_version,
            generation=generation,
            parent_checkpoint_id=parent_checkpoint_id,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            board_weights=board,
            hand_weights=hand,
            dynamic_weights=dict(dynamic_weights or {}),
            value_scale=value_scale,
            reference_median=median,
            w_max=w_max,
            training_seed=training_seed,
        )

    # -------------------------------------------------------------- native

    def quantized_board(self, type_ids: tuple[str, ...]) -> list[int]:
        return [
            int(round(self.board_weights.get(tid, 0.0) * self.material_scale))
            for tid in type_ids
        ]

    def quantized_hand(self, type_ids: tuple[str, ...]) -> list[int]:
        return [
            int(round(self.hand_weights.get(tid, 0.0) * self.material_scale))
            for tid in type_ids
        ]

    def quantized_dynamic(self) -> list[int]:
        return [int(round(self.dynamic_weights.get(name, 0.0))) for name in DYNAMIC_FEATURE_NAMES]

    @property
    def semantic_native_scale(self) -> int:
        """Fixed-point scale used by the versioned semantic evaluator."""
        return SEMANTIC_NATIVE_SCALE if self.dynamic_weights else int(self.material_scale)

    def semantic_quantized_board(self, type_ids: tuple[str, ...]) -> list[int]:
        scale = self.semantic_native_scale
        return [int(round(self.board_weights.get(tid, 0.0) * scale)) for tid in type_ids]

    def semantic_quantized_hand(self, type_ids: tuple[str, ...]) -> list[int]:
        scale = self.semantic_native_scale
        return [int(round(self.hand_weights.get(tid, 0.0) * scale)) for tid in type_ids]

    def semantic_quantized_dynamic(self) -> list[int] | None:
        if not self.dynamic_weights:
            return None
        scale = self.semantic_native_scale
        return [int(round(self.dynamic_weights.get(name, 0.0) * scale)) for name in DYNAMIC_FEATURE_NAMES]

    def semantic_quantized_spatial(self, type_ids: tuple[str, ...]) -> list[int] | None:
        if not self.spatial_occupancy_weights:
            return None
        scale = self.semantic_native_scale
        result: list[int] = []
        for owner in (0, 1):
            for type_id in type_ids:
                key = f"{owner}:{type_id}"
                row = tuple(self.spatial_occupancy_weights.get(key, ()))
                if len(row) != SPATIAL_CELL_COUNT:
                    raise LearningNumericalError(
                        f"spatial occupancy row for {key!r} must contain {SPATIAL_CELL_COUNT} values"
                    )
                quantized = [int(round(value * scale)) for value in row[:-1]]
                quantized.append(-sum(quantized))
                result.extend(quantized)
        return result

    def semantic_quantized_localized_control(self) -> list[int] | None:
        if not self.localized_control_weights:
            return None
        if len(self.localized_control_weights) != SPATIAL_CELL_COUNT:
            raise LearningNumericalError(
                f"localized control weights must contain {SPATIAL_CELL_COUNT} values"
            )
        scale = self.semantic_native_scale
        result = [int(round(value * scale)) for value in self.localized_control_weights[:-1]]
        result.append(-sum(result))
        return result

    def native_board_value(self, type_id: str) -> int:
        return int(round(self.board_weights.get(type_id, 0.0) * self.material_scale))

    def native_hand_value(self, type_id: str) -> int:
        return int(round(self.hand_weights.get(type_id, 0.0) * self.material_scale))

    # ----------------------------------------------------------- training

    def normalize_and_clip(self) -> None:
        """Rescale so the non-anchor board median stays fixed, then clip."""
        current_median = _median_abs(list(self.board_weights.values()))
        if current_median < 1e-9:
            raise LearningNumericalError(
                "non-anchor board weight median collapsed to ~0; "
                "refusing to normalize"
            )
        # The frozen reference median (initial non-anchor board median).
        target = (
            self.reference_median
            if self.reference_median > 0
            else self.value_scale / 4.0
        )
        factor = target / current_median
        for tid in list(self.board_weights):
            self.board_weights[tid] = max(
                -self.w_max, min(self.w_max, self.board_weights[tid] * factor)
            )
        for tid in list(self.hand_weights):
            self.hand_weights[tid] = max(
                -self.w_max, min(self.w_max, self.hand_weights[tid] * factor)
            )
        for name in list(self.dynamic_weights):
            self.dynamic_weights[name] = max(
                -self.w_max, min(self.w_max, self.dynamic_weights[name] * factor)
            )
        return factor

    def child_checkpoint(
        self,
        *,
        board_weights: dict[str, float],
        hand_weights: dict[str, float],
        games_seen_delta: int,
        positions_seen_delta: int,
        training_updates_delta: int,
        training_config_hash: str,
        training_seed: int | None,
        value_scale: float | None = None,
        dynamic_weights: dict[str, float] | None = None,
        spatial_occupancy_weights: dict[str, tuple[float, ...]] | None = None,
        localized_control_weights: tuple[float, ...] | None = None,
    ) -> "LearnableMaterialCheckpoint":
        """Create the next generation with a deterministic parent chain."""
        return LearnableMaterialCheckpoint(
            ruleset_fingerprint=self.ruleset_fingerprint,
            evaluation_profile_version=self.evaluation_profile_version,
            generation=self.generation + 1,
            parent_checkpoint_id=self.checkpoint_id,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            training_config_hash=training_config_hash,
            board_weights=dict(board_weights),
            hand_weights=dict(hand_weights),
            dynamic_weights=dict(
                self.dynamic_weights if dynamic_weights is None else dynamic_weights
            ),
            spatial_occupancy_weights=dict(
                self.spatial_occupancy_weights
                if spatial_occupancy_weights is None else spatial_occupancy_weights
            ),
            localized_control_weights=tuple(
                self.localized_control_weights
                if localized_control_weights is None else localized_control_weights
            ),
            material_scale=self.material_scale,
            value_scale=value_scale if value_scale is not None else self.value_scale,
            reference_median=self.reference_median,
            w_max=self.w_max,
            games_seen=self.games_seen + games_seen_delta,
            positions_seen=self.positions_seen + positions_seen_delta,
            training_updates=self.training_updates + training_updates_delta,
            training_seed=training_seed,
        )

    # -------------------------------------------------------- serialization

    def to_dict(self) -> dict[str, Any]:
        return dict(self._learning_state())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearnableMaterialCheckpoint":
        allowed = {
            "schema_version",
            "ruleset_fingerprint",
            "evaluation_profile_version",
            "generation",
            "parent_checkpoint_id",
            "created_at",
            "training_config_hash",
            "board_weights",
            "hand_weights",
            "dynamic_weights",
            "spatial_occupancy_weights",
            "localized_control_weights",
            "material_scale",
            "value_scale",
            "reference_median",
            "w_max",
            "games_seen",
            "positions_seen",
            "training_updates",
            "training_seed",
            "promoted_to_champion",
        }
        extra = set(data) - allowed
        if extra:
            raise ValueError(f"unknown checkpoint fields: {sorted(extra)}")
        if data.get("schema_version") == 1:
            raise ValueError(
                "checkpoint schema v1 is not supported for training: its "
                "training_config_hash used a stale pre-calibration payload "
                "and cannot be audited; regenerate from a v2 parent"
            )
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported checkpoint schema {data.get('schema_version')}"
            )
        payload = {k: data[k] for k in allowed if k in data}
        payload.setdefault("dynamic_weights", {})
        payload.setdefault("spatial_occupancy_weights", {})
        payload.setdefault("localized_control_weights", ())
        return cls(**payload)

    def validate_ruleset(self, compiled) -> None:
        if self.ruleset_fingerprint != compiled.ruleset_fingerprint:
            raise ValueError(
                "checkpoint ruleset fingerprint does not match the compiled "
                f"ruleset ({self.ruleset_fingerprint} vs "
                f"{compiled.ruleset_fingerprint})"
            )
        if self.spatial_occupancy_weights:
            metadata = getattr(getattr(compiled, "support", None), "type_metadata", None)
            if metadata is not None:
                type_ids = tuple(sorted(metadata))
            else:
                type_ids = tuple(sorted(pt.type_id for pt in compiled.piece_types))
            expected = {f"{owner}:{type_id}" for owner in (0, 1) for type_id in type_ids}
            if set(self.spatial_occupancy_weights) != expected:
                raise ValueError(
                    "spatial occupancy checkpoint must cover every owner/current type"
                )

    def ensure_within_limits(self) -> None:
        for tid, w in self.board_weights.items():
            if not math.isfinite(w):
                raise LearningNumericalError(f"non-finite board weight for {tid}")
            if abs(w) > self.w_max:
                raise LearningNumericalError(
                    f"board weight {tid} exceeds w_max ({w} > {self.w_max})"
                )
        for tid, w in self.hand_weights.items():
            if not math.isfinite(w):
                raise LearningNumericalError(f"non-finite hand weight for {tid}")
            if abs(w) > self.w_max:
                raise LearningNumericalError(
                    f"hand weight {tid} exceeds w_max ({w} > {self.w_max})"
                )
        for name, w in self.dynamic_weights.items():
            if name not in DYNAMIC_FEATURE_NAMES:
                raise LearningNumericalError(f"unknown dynamic weight {name}")
            if not math.isfinite(w):
                raise LearningNumericalError(f"non-finite dynamic weight for {name}")
            if abs(w) > self.w_max:
                raise LearningNumericalError(
                    f"dynamic weight {name} exceeds w_max ({w} > {self.w_max})"
                )
        for type_id, row in self.spatial_occupancy_weights.items():
            if len(row) != SPATIAL_CELL_COUNT:
                raise LearningNumericalError(
                    f"spatial occupancy row for {type_id!r} must contain {SPATIAL_CELL_COUNT} values"
                )
            if abs(sum(row)) > 1e-9:
                raise LearningNumericalError(
                    f"spatial occupancy row for {type_id!r} must have zero mean"
                )
            for index, w in enumerate(row):
                if not math.isfinite(w):
                    raise LearningNumericalError(
                        f"non-finite spatial occupancy weight for {type_id}[{index}]"
                    )
                if abs(w) > self.w_max:
                    raise LearningNumericalError(
                        f"spatial occupancy weight {type_id}[{index}] exceeds w_max"
                    )
        if self.localized_control_weights:
            if len(self.localized_control_weights) != SPATIAL_CELL_COUNT:
                raise LearningNumericalError(
                    f"localized control weights must contain {SPATIAL_CELL_COUNT} values"
                )
            if abs(sum(self.localized_control_weights)) > 1e-9:
                raise LearningNumericalError(
                    "localized control weights must have zero mean"
                )
            for index, w in enumerate(self.localized_control_weights):
                if not math.isfinite(w):
                    raise LearningNumericalError(
                        f"non-finite localized control weight at {index}"
                    )
                if abs(w) > self.w_max:
                    raise LearningNumericalError(
                        f"localized control weight {index} exceeds w_max"
                    )
