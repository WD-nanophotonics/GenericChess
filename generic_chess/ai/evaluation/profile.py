"""RuleSet-level evaluation profile (built once per RuleSet)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

from ...core.pieces import PieceType
from ...rules.compiled import CompiledRuleSet
from .analyzer import MovementCapabilityProfile, build_movement_capability
from .config import EvaluationConfig, MAX_STATIC_EVAL, config_hash

if TYPE_CHECKING:
    from .cache import MovementCapabilityCache


@dataclass(frozen=True, slots=True)
class PieceValueProfile:
    type_id: str
    movement_signature: str
    raw_capability_score: float
    normalized_board_value: int
    normalized_hand_value: int
    promotion_option_value: int
    drop_freedom_ratio: float
    drop_mobility: float
    is_anchor: bool
    is_promotable: bool


@dataclass(frozen=True, slots=True)
class RuleSetEvaluationProfile:
    ruleset_fingerprint: str
    schema_version: int
    evaluator_version: str
    config_hash: str
    piece_profiles: Mapping[str, PieceValueProfile]
    median_non_anchor_value: int
    board_value_by_type: Mapping[str, int]
    hand_value_by_base_type: Mapping[str, int]
    promotion_gain_by_type: Mapping[str, int]


def _raw_capability_score(capability: MovementCapabilityProfile, config: EvaluationConfig) -> float:
    mobility_score = sum(
        w * m for w, m in zip(config.density_weights, capability.expected_mobility)
    )
    path_eff = (
        1.0 / (1.0 + capability.average_shortest_path)
        if capability.average_shortest_path is not None
        else 0.0
    )
    return (
        mobility_score
        + config.coverage_weight * capability.coverage_ratio
        + config.reachability_weight * capability.reachable_pair_ratio
        + config.path_efficiency_weight * path_eff
    )


def _drop_profile(
    compiled: CompiledRuleSet,
    type_id: str,
    n: int,
) -> tuple[float, float]:
    if type_id not in compiled.drop_allowed:
        return 0.0, 0.0
    mask = compiled.drop_allowed[type_id][0]
    total = n * n
    allowed = [idx for idx, ok in enumerate(mask) if ok]
    freedom = len(allowed) / total if total else 0.0
    mobility = sum(len(compiled.empty_mobility[type_id][0][idx]) for idx in allowed)
    avg = mobility / len(allowed) if allowed else 0.0
    return freedom, avg


def build_ruleset_profile(
    compiled: CompiledRuleSet,
    config: EvaluationConfig,
    capability_cache: "MovementCapabilityCache | None" = None,
) -> RuleSetEvaluationProfile:
    n = compiled.board_size
    raw: dict[str, float] = {}
    capabilities: dict[str, MovementCapabilityProfile] = {}
    drop: dict[str, tuple[float, float]] = {}
    ordinary: list[PieceType] = []

    for pt in compiled.piece_types:
        if capability_cache is not None:
            capability, _ = capability_cache.get_or_build(n, pt.movement_atoms, config)
        else:
            capability = build_movement_capability(n, pt.movement_atoms, config)
        capabilities[pt.type_id] = capability
        raw[pt.type_id] = _raw_capability_score(capability, config)
        drop[pt.type_id] = _drop_profile(compiled, pt.type_id, n)
        if not pt.is_anchor:
            ordinary.append(pt)

    median_raw = _median([raw[pt.type_id] for pt in ordinary]) if ordinary else 0.0
    scale = config.normal_piece_median_value

    def normalized_board(type_id: str, is_anchor: bool) -> int:
        if is_anchor:
            return 0
        if median_raw <= 0.0:
            return 1
        value = int(round(scale * raw[type_id] / median_raw))
        return max(1, min(value, MAX_STATIC_EVAL))

    board_value: dict[str, int] = {}
    hand_value: dict[str, int] = {}
    promotion_gain: dict[str, int] = {}

    # Pass 1: every board/hand value must be complete before promotion gains
    # are computed so results never depend on piece_types declaration order.
    for pt in compiled.piece_types:
        bv = normalized_board(pt.type_id, pt.is_anchor)
        board_value[pt.type_id] = bv
        hv = int(round(bv * config.hand_weight)) if not pt.is_anchor else 0
        hand_value[pt.type_id] = min(hv, MAX_STATIC_EVAL)

    # Pass 2: promotion gains (from the complete table) and profiles.
    profiles: dict[str, PieceValueProfile] = {}
    for pt in compiled.piece_types:
        bv = board_value[pt.type_id]
        if pt.is_promotable:
            targets = [board_value[t] for t in pt.promotion_target_ids if t in board_value]
            promotion_gain[pt.type_id] = max(
                0, (max(targets) if targets else 0) - bv
            )
        else:
            promotion_gain[pt.type_id] = 0
        freedom, drop_mob = drop[pt.type_id]
        profiles[pt.type_id] = PieceValueProfile(
            type_id=pt.type_id,
            movement_signature=capabilities[pt.type_id].movement_signature,
            raw_capability_score=raw[pt.type_id],
            normalized_board_value=bv,
            normalized_hand_value=hand_value[pt.type_id],
            promotion_option_value=promotion_gain[pt.type_id],
            drop_freedom_ratio=freedom,
            drop_mobility=drop_mob,
            is_anchor=pt.is_anchor,
            is_promotable=pt.is_promotable,
        )

    median_value = _median([board_value[pt.type_id] for pt in ordinary]) if ordinary else 0
    return RuleSetEvaluationProfile(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        schema_version=1,
        evaluator_version=config.evaluator_version,
        config_hash=config_hash(config),
        piece_profiles=profiles,
        median_non_anchor_value=median_value,
        board_value_by_type=board_value,
        hand_value_by_base_type=hand_value,
        promotion_gain_by_type=promotion_gain,
    )


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0
