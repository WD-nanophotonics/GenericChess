"""F130: generic rule-derived structural augmentation for the frozen F129 surface.

This is benchmark-local code.  The feature extractor deliberately consumes
only compiled rules and a position; it does not enumerate legal actions or
successor states and does not call a search/evaluator path.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import (
        FrozenBasis,
        _json_sha,
        _scalar_metrics,
    )
    from scripts.f125_known_oracle_one_ply_search_compression import _prepare_filtered
    from scripts.f127_shogi_t1_scalar_compression_expanded_control import (
        _fit_metrics_tight,
        _fit_report,
        _numerical_gate,
        _search_representation_gate,
    )
    from scripts.f128_shogi_direct_control_cross_surface_diagnosis import (
        CORPUS_HASH,
        F127_COUNTS,
        ORACLE_HASH,
        _collect_states,
        _eligibility_map,
        _selected_ordinals,
    )
    from scripts.f129_shogi_known_oracle_t1_scalar_compression import (
        RETAINED_COUNTS,
        _by_split,
        _load_or_generate_shards,
        _materialize,
    )
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import FrozenBasis, _json_sha, _scalar_metrics
    from f125_known_oracle_one_ply_search_compression import _prepare_filtered
    from f127_shogi_t1_scalar_compression_expanded_control import _fit_metrics_tight, _fit_report, _numerical_gate, _search_representation_gate
    from f128_shogi_direct_control_cross_surface_diagnosis import CORPUS_HASH, F127_COUNTS, ORACLE_HASH, _collect_states, _eligibility_map, _selected_ordinals
    from f129_shogi_known_oracle_t1_scalar_compression import RETAINED_COUNTS, _by_split, _load_or_generate_shards, _materialize

from generic_chess.core.coordinates import index_to_square, square_to_index
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands, Position
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


FAMILY = "standard_shogi"
BASELINE = "64d26b26d7694c513508ff8bdb7f2f00135ee6e2"
F129_BASE_HOLDOUT_RMSE = 8476.16832054588
F129_STATIC_HOLDOUT_RMSE = 6088.17472319246
F127_DIRECT_HOLDOUT_NRMSE = 0.05158006312777384
F129_REPRO_TOLERANCE = 1e-6
FEATURE_NAMES = (
    "realized_activity_balance",
    "blocked_capacity_balance",
    "empty_board_positional_capability_balance",
    "promotion_structural_capability_balance",
    "drop_structural_capability_balance",
    "anchor_structural_space_balance",
    "anchor_ring_control_balance",
    "attacked_structural_value_balance",
    "hanging_structural_value_balance",
)


class AugmentedBasis:
    """Feature-name carrier for the unchanged FrozenBasis normalization path."""

    def __init__(self, base: FrozenBasis) -> None:
        self.base = base
        self.compiled = base.compiled
        self.names = tuple(base.names) + FEATURE_NAMES
        self.weights = tuple(base.weights) + (0.0,) * len(FEATURE_NAMES)


def _rule_values(compiled) -> tuple[dict[str, float], float, dict[str, float], dict[str, float]]:
    """Derive stable structural values from movement capability, not piece IDs."""
    n = compiled.board_size
    values: dict[str, float] = {}
    means: dict[str, float] = {}
    maxima: dict[str, float] = {}
    for piece_type in compiled.piece_types:
        tid = piece_type.type_id
        counts = [
            len(compiled.empty_mobility[tid][owner][square])
            for owner in (0, 1)
            for square in range(n * n)
        ]
        values[tid] = 1.0 + float(np.mean(counts)) if counts else 1.0
        means[tid] = float(np.mean(counts)) if counts else 0.0
        maxima[tid] = float(max(counts)) if counts else 0.0
    ordinary = [values[pt.type_id] for pt in compiled.piece_types if not pt.is_anchor]
    ordered = sorted(ordinary)
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else ((ordered[middle - 1] + ordered[middle]) / 2.0 if ordered else 1.0)
    return values, max(1.0, median), means, maxima


def _blocker_aware_targets(position: Position, compiled, owner: int, tid: str, source: int) -> frozenset[int]:
    """Return F37-style pseudo-targets: rays stop at the first occupied square."""
    targets: set[int] = set()
    atoms = compiled.types_by_id[tid].movement_atoms
    leap_row = compiled.leap_targets[tid][owner][source]
    ray_row = compiled.ray_paths[tid][owner][source]
    n = compiled.board_size
    for atom, leap_targets, ray_path in zip(atoms, leap_row, ray_row):
        if isinstance(atom, LeapAtom):
            targets.update(square_to_index(square, n) for square in leap_targets)
            continue
        for square in ray_path:
            target = square_to_index(square, n)
            targets.add(target)
            if position.board[target] is not None:
                break
    return frozenset(targets)


def _side_delta(values: tuple[float, float], side: int) -> float:
    return float(values[side] - values[1 - side])


def structural_features(state, compiled) -> np.ndarray:
    """Return exactly the nine generic side-to-move-relative F130 features."""
    position = state.position
    side = position.side_to_move
    rules = getattr(compiled, "_legacy_compiled", None) or compiled
    n = rules.board_size
    type_values, median_value, type_means, type_maxima = _rule_values(rules)
    metadata = rules.types_by_id

    activity = [0.0, 0.0]
    blocked = [0.0, 0.0]
    positional = [0.0, 0.0]
    promotion = [0.0, 0.0]
    drop = [0.0, 0.0]
    attacked = [0.0, 0.0]
    hanging = [0.0, 0.0]
    pseudo_by_owner: list[set[int]] = [set(), set()]
    piece_records: list[tuple[int, int, str, int, frozenset[int]]] = []

    for source, piece in enumerate(position.board):
        if piece is None:
            continue
        tid = piece.current_type_id
        pseudo = _blocker_aware_targets(position, rules, piece.owner, tid, source)
        pseudo_by_owner[piece.owner].update(pseudo)
        piece_records.append((source, piece.owner, tid, piece.base_type_id, pseudo))
        meta = metadata[tid]
        if not meta.is_anchor:
            structural_ratio = type_values[tid] / median_value
            empty_count = len(rules.empty_mobility[tid][piece.owner][source])
            realized_ratio = len(pseudo) / max(1, empty_count)
            activity[piece.owner] += structural_ratio * realized_ratio
            if empty_count:
                blocked[piece.owner] += structural_ratio * (1.0 - realized_ratio)
            positional[piece.owner] += type_values[tid] * (
                empty_count - type_means[tid]
            ) / max(1.0, type_maxima[tid])
            if not piece.promoted and meta.is_promotable:
                allowed = rules.promotion_allowed.get(piece.base_type_id, ((), ()))
                source_opportunities = sum(1 for origin, _ in allowed[piece.owner] if origin == index_to_square(source, n))
                opportunity_ratio = source_opportunities / max(1, empty_count)
                targets = [type_values[target] for target in meta.promotion_target_ids if target in type_values]
                gain = max(0.0, (max(targets) if targets else type_values[tid]) - type_values[tid])
                promotion[piece.owner] += gain * opportunity_ratio

    for owner, hand in enumerate(position.hands):
        for tid, count in hand.items():
            if tid not in rules.drop_allowed or tid not in type_values or count <= 0:
                continue
            mask = rules.drop_allowed[tid][owner]
            legal_squares = [index for index, allowed in enumerate(mask) if allowed and position.board[index] is None]
            drop_freedom = len(legal_squares) / max(1, n * n)
            mean_mobility = (
                float(np.mean([len(rules.empty_mobility[tid][owner][index]) for index in legal_squares]))
                if legal_squares else 0.0
            )
            drop[owner] += drop_freedom * mean_mobility * (type_values[tid] / median_value) * count

    anchor_space = [0.0, 0.0]
    ring_control = [0.0, 0.0]
    anchors: list[int | None] = [None, None]
    for source, piece in enumerate(position.board):
        if piece is None or not metadata[piece.current_type_id].is_anchor:
            continue
        anchors[piece.owner] = source
        ring = {
            square_to_index(square, n)
            for square in rules.empty_mobility[piece.current_type_id][piece.owner][source]
        }
        empty_fraction = sum(position.board[index] is None for index in ring) / max(1, len(ring))
        anchor_space[piece.owner] = float(empty_fraction)
        friendly = len(pseudo_by_owner[piece.owner] & ring)
        enemy = len(pseudo_by_owner[1 - piece.owner] & ring)
        ring_control[piece.owner] = float(friendly - enemy)

    for source, owner, tid, _base_tid, pseudo in piece_records:
        if metadata[tid].is_anchor:
            continue
        value = type_values[tid] / median_value
        if source in pseudo_by_owner[1 - owner]:
            attacked[owner] += value
            if not (pseudo_by_owner[owner] and source in pseudo_by_owner[owner]):
                hanging[owner] += value

    attacked_balance = attacked[1 - side] - attacked[side]
    hanging_balance = hanging[1 - side] - hanging[side]
    return np.asarray((
        _side_delta(tuple(activity), side),
        _side_delta(tuple(blocked), side),
        _side_delta(tuple(positional), side),
        _side_delta(tuple(promotion), side),
        _side_delta(tuple(drop), side),
        _side_delta(tuple(anchor_space), side),
        _side_delta(tuple(ring_control), side),
        attacked_balance,
        hanging_balance,
    ), dtype=np.float64)


def _write_progress(output: Path, stage: str, payload: dict) -> None:
    path = output.parent / f"{output.stem}.stage-{stage}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _augment(rows: list[dict], compiled, base: FrozenBasis) -> list[dict]:
    output = []
    for row in rows:
        extra = structural_features(row["state"], compiled)
        if not np.all(np.isfinite(extra)):
            raise RuntimeError("F130_NONFINITE_STRUCTURAL_FEATURE")
        output.append({**row, "features": list(row["features"]) + extra.tolist(), "structural_features": extra.tolist()})
    return output


def _rank_report(rows: list[dict], basis) -> dict:
    raw = np.asarray([row["features"] for row in rows if row["split"] == "train"], dtype=np.float64)
    scale = raw.std(axis=0)
    active = scale > 1e-12
    design = np.column_stack([((raw - raw.mean(axis=0)) / np.where(active, scale, 1.0))[:, active], np.ones(len(raw))])
    singular = np.linalg.svd(design, compute_uv=False)
    tolerance = np.finfo(np.float64).eps * max(design.shape) * float(singular[0])
    retained = singular > tolerance
    spectrum = singular[retained]
    return {
        "raw_feature_count": len(basis.names),
        "active_feature_count": int(active.sum()),
        "numerical_rank": int(retained.sum()),
        "nullity": int(len(singular) - retained.sum()),
        "condition_number_on_retained_spectrum": float(spectrum[0] / spectrum[-1]) if len(spectrum) else None,
        "rank_tolerance": float(tolerance),
    }


def _feature_diagnostic(fit: dict, rows: list[dict]) -> dict:
    pack = fit["pack"]
    model = fit["matched"]
    base_count = len(rows[0]["features"]) - len(FEATURE_NAMES)
    raw = np.asarray([row["features"] for row in rows], dtype=np.float64)
    train = raw[[row["split"] == "train" for row in rows]]
    holdout = raw[[row["split"] == "holdout" for row in rows]]
    names = FEATURE_NAMES
    rows_out = []
    for offset, name in enumerate(names):
        index = base_count + offset
        active_indices = np.flatnonzero(pack["active"])
        parameter_index = int(np.searchsorted(active_indices, index)) if pack["active"][index] else None
        normalized_coefficient = float(model[parameter_index]) if parameter_index is not None and parameter_index < len(model) - 1 else 0.0
        raw_coefficient = float(pack["target_std"] * normalized_coefficient / pack["feature_scale"][index])
        train_std = float(np.std(train[:, index]))
        holdout_std = float(np.std(holdout[:, index]))
        rows_out.append({
            "feature": name,
            "normalized_coefficient": normalized_coefficient,
            "raw_target_coefficient": raw_coefficient,
            "train_standard_deviation": train_std,
            "holdout_standard_deviation": holdout_std,
            "absolute_coefficient_times_holdout_standard_deviation": abs(raw_coefficient) * holdout_std,
        })
    corr = np.corrcoef(train[:, -len(names):].T) if len(train) > 1 else np.eye(len(names))
    return {"fitted_features": rows_out, "pairwise_correlation": corr.tolist()}


def _static_metrics(rows: list[dict], records_by_split: dict[str, list[dict]]) -> dict:
    result = {}
    for split in ("train", "dev", "holdout"):
        target = np.asarray([record["t1"] for record in records_by_split[split]], dtype=np.float64)
        direct = np.asarray([row["direct_oracle"] for row in rows if row["split"] == split], dtype=np.float64)
        result[split] = _scalar_metrics(target, direct, float(np.std(target)) or 1.0)
    return result


def _microtests() -> dict:
    reports = {}
    for label, builder in (("shogi_like", build_standard_shogi_ruleset), ("western_like", build_western_chess_ruleset)):
        compiled = compile_semantic_ruleset(builder())
        rules = getattr(compiled, "_legacy_compiled", None) or compiled
        state = initial_state(compiled)
        values = structural_features(state, compiled)
        renamed_types = tuple(
            type(piece_type)(piece_type.type_id, f"renamed-{index}", piece_type.movement_atoms, piece_type.is_anchor, piece_type.is_promotable, piece_type.promotion_target_ids)
            for index, piece_type in enumerate(rules.piece_types)
        )
        renamed = rules.__class__(
            rules.ruleset_fingerprint, rules.board_size, renamed_types,
            {piece_type.type_id: piece_type for piece_type in renamed_types}, rules.initial_position, rules.initial_entity_count,
            rules.leap_targets, rules.ray_paths, rules.empty_mobility, rules.empty_forward_mobility,
            rules.drop_allowed, rules.promotion_allowed, rules.promotion_forced,
            rules.repetition_limit, rules.max_ply, rules.stalemate_result, rules.repetition_policy,
            rules.automatic_adjudications, rules.declarations,
        )
        renamed_values = structural_features(state, renamed)
        mirror_board = tuple(
            None if piece is None else Piece(piece.owner ^ 1, piece.base_type_id, piece.current_type_id, piece.promoted)
            for piece in reversed(state.position.board)
        )
        mirror_position = Position(mirror_board, (state.position.hands[1], state.position.hands[0]), state.position.side_to_move ^ 1, state.position.ruleset_fingerprint, state.position.aux_state)
        mirror_state = state.__class__(mirror_position, state.ply_count, state.repetition_counts, state.terminal_status, state.history)
        mirror_values = structural_features(mirror_state, compiled)
        empty_position = Position((None,) * (rules.board_size * rules.board_size), (Hands.empty(), Hands.empty()), 0, rules.ruleset_fingerprint)
        empty_state = state.__class__(empty_position, 0, (), state.terminal_status, ())
        empty_values = structural_features(empty_state, compiled)
        reports[label] = {
            "finite": bool(np.all(np.isfinite(values))),
            "exactly_nine": len(values) == 9,
            "type_name_rename_invariant": bool(np.allclose(values, renamed_values, atol=1e-12, rtol=0.0)),
            "owner_board_mirror_negates": bool(np.allclose(values, -mirror_values, atol=1e-12, rtol=0.0)),
            "anchor_absence_zero": bool(np.allclose(empty_values, 0.0, atol=1e-12, rtol=0.0)),
        }
    result = {"by_ruleset": reports}
    result["pass"] = all(all(flags.values()) for flags in reports.values())
    return result


def _run(output: Path) -> dict:
    started = time.time()
    microtests = _microtests()
    _write_progress(output, "genericity-microtests", microtests)
    if not microtests["pass"]:
        return {"schema": "F130_SHOGI_RULE_DERIVED_STRUCTURAL_T1_AUGMENTATION_V1", "classification": "F130_GENERICITY_MICROTEST_FAILURE", "microtests": microtests, "runtime_seconds": time.time() - started}

    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    base = FrozenBasis(FAMILY, compiled)
    states, corpus = _collect_states(compiled, base)
    retained_states, eligibility_counts, retained_sha = _eligibility_map(states, compiled)
    selected_ordinals = _selected_ordinals()
    selected = {ordinal for values in selected_ordinals.values() for ordinal in values}
    selected_identity_sha = {split: _json_sha([row["identity"] for row in states if row["ordinal"] in selected_ordinals[split]]) for split in ("train", "dev", "holdout")}
    retained_selected = [row for row in retained_states if row["ordinal"] in selected]
    retained_selected_counts = {split: sum(row["split"] == split for row in retained_selected) for split in ("train", "dev", "holdout")}
    expected_selected_sha = {
        "train": "c16db7cc19375820ca9a9866493922bf7a0d74eff64a8f909b225e9936f205fc",
        "dev": "91929864cab22ba1fc065f9acdc49855751a9761ebd28b9cda76202fe01e6e63",
        "holdout": "0173ba68eed4c779322214b3ef6c819726cb5476703214d00e4d8255a7b580b3",
    }
    expected_retained_sha = {
        "train": "74f9778dff9a2a5c08a6623d5452cdf2d15971cc20eab0c3e12a9c5d01d0a15b",
        "dev": "5c9d3acbc6adbd366c8c2b3739fe80b322e67a83e13b3eb1c1153871d70f0448",
        "holdout": "4238175784283f3338294290bb70b1330930a427a213f1a56223471b44d1d456",
    }
    if corpus["full_identity_sha256"] != CORPUS_HASH or selected_identity_sha != expected_selected_sha or retained_sha != expected_retained_sha or retained_selected_counts != RETAINED_COUNTS or base.oracle_weight_sha256 != ORACLE_HASH:
        raise RuntimeError("F130_FROZEN_SURFACE_IDENTITY_MISMATCH")
    direct_rows = _materialize(retained_selected, base)
    direct_fit_base = _fit_metrics_tight(direct_rows, [row["direct_oracle"] for row in direct_rows], base)
    direct_aug_rows = _augment(direct_rows, compiled, base)
    aug_basis = AugmentedBasis(base)
    direct_fit_aug = _fit_metrics_tight(direct_aug_rows, [row["direct_oracle"] for row in direct_aug_rows], aug_basis)
    direct_report = {
        "f129_base": _fit_report(direct_fit_base, "oracle"),
        "f130_augmented": _fit_report(direct_fit_aug, "oracle"),
        "f127_reference_holdout_normalized_rmse": F127_DIRECT_HOLDOUT_NRMSE,
        "change_augmented_minus_base_holdout_normalized_rmse": direct_fit_aug["scalar_metrics"]["matched_ridge"]["holdout"]["normalized_rmse"] - direct_fit_base["scalar_metrics"]["matched_ridge"]["holdout"]["normalized_rmse"],
    }
    _write_progress(output, "direct-control", direct_report)

    f129_shard_source = output.parent / "f129-shogi-result.json"
    records, shard_info = _load_or_generate_shards(direct_rows, base, compiled, f129_shard_source)
    records_by_split = _by_split(records, direct_rows)
    labels = {record["identity"]: record["t1"] for record in records}
    t1_labels = [labels[row["identity"]] for row in direct_rows]
    static = _static_metrics(direct_rows, records_by_split)
    base_t1_fit = _fit_metrics_tight(direct_rows, t1_labels, base)
    base_t1_report = _fit_report(base_t1_fit, "teacher")
    base_holdout = base_t1_report["scalar_metrics"]["matched_ridge"]["holdout"]["rmse_oracle_units"]
    static_holdout = static["holdout"]["rmse_oracle_units"]
    reproduction = {
        "base_holdout_rmse": base_holdout,
        "expected_f129_base_holdout_rmse": F129_BASE_HOLDOUT_RMSE,
        "base_absolute_rmse_difference": abs(base_holdout - F129_BASE_HOLDOUT_RMSE),
        "static_holdout_rmse": static_holdout,
        "expected_f129_static_holdout_rmse": F129_STATIC_HOLDOUT_RMSE,
        "static_absolute_rmse_difference": abs(static_holdout - F129_STATIC_HOLDOUT_RMSE),
        "pass": abs(base_holdout - F129_BASE_HOLDOUT_RMSE) <= F129_REPRO_TOLERANCE and abs(static_holdout - F129_STATIC_HOLDOUT_RMSE) <= F129_REPRO_TOLERANCE,
    }
    _write_progress(output, "f129-reproduction", reproduction)
    if not reproduction["pass"]:
        return {"schema": "F130_SHOGI_RULE_DERIVED_STRUCTURAL_T1_AUGMENTATION_V1", "classification": "F130_F129_TARGET_REPRODUCTION_FAILURE", "microtests": microtests, "reproduction": reproduction, "runtime_seconds": time.time() - started}

    augmented_fit = _fit_metrics_tight(direct_aug_rows, t1_labels, aug_basis)
    augmented_report = _fit_report(augmented_fit, "teacher")
    augmented_metrics = augmented_report["scalar_metrics"]["matched_ridge"]
    numerical = _numerical_gate(augmented_fit)
    representation = _search_representation_gate(augmented_metrics)
    usefulness = augmented_metrics["holdout"]["rmse_oracle_units"] < F129_STATIC_HOLDOUT_RMSE
    metrics = {
        "F129_base_compressed": base_t1_report["scalar_metrics"]["matched_ridge"],
        "F129_static_oracle": static,
        "F130_augmented": augmented_metrics,
        "improvement_vs_f129_holdout_rmse": F129_BASE_HOLDOUT_RMSE - augmented_metrics["holdout"]["rmse_oracle_units"],
        "improvement_vs_static_holdout_rmse": F129_STATIC_HOLDOUT_RMSE - augmented_metrics["holdout"]["rmse_oracle_units"],
    }
    rank_a = _rank_report(direct_rows, base)
    rank_b = _rank_report(direct_aug_rows, aug_basis)
    rank = {"A_BASE_HANDCRAFTED": rank_a, "B_BASE_PLUS_RULE_DERIVED_STRUCTURAL_V1": rank_b, "rank_increment": rank_b["numerical_rank"] - rank_a["numerical_rank"]}
    _write_progress(output, "rank-diagnostic", rank)
    contribution = _feature_diagnostic(augmented_fit, direct_aug_rows)
    _write_progress(output, "search-fit", {"fit": augmented_report, "numerical_gate": {**numerical, "pass": all(numerical.values())}, "representation_gate": representation, "usefulness_gate": usefulness, "metrics": metrics, "rank": rank, "feature_contribution": contribution})

    if not all(numerical.values()):
        classification = "F130_STRUCTURAL_T1_SOLVER_NUMERICAL_FAILURE"
    elif not representation["pass"] and augmented_metrics["holdout"]["rmse_oracle_units"] >= F129_BASE_HOLDOUT_RMSE:
        classification = "RULE_DERIVED_STRUCTURAL_AUGMENTATION_DOES_NOT_CAPTURE_T1"
    elif not representation["pass"]:
        classification = "RULE_DERIVED_STRUCTURAL_AUGMENTATION_PARTIAL"
    elif not usefulness:
        classification = "T1_SCALAR_REPRESENTABLE_BUT_COMPRESSION_NOT_USEFUL"
    else:
        classification = "RULE_DERIVED_STRUCTURAL_AUGMENTATION_PASSES_T1_COMPRESSION"
    return {
        "schema": "F130_SHOGI_RULE_DERIVED_STRUCTURAL_T1_AUGMENTATION_V1",
        "baseline": BASELINE,
        "family": FAMILY,
        "microtests": microtests,
        "corpus": corpus,
        "eligibility": {"counts_by_split": eligibility_counts, "retained_identity_sha256": retained_sha, "selected_identity_sha256": selected_identity_sha, "retained_selected_counts": retained_selected_counts},
        "shards": shard_info,
        "f129_reproduction": reproduction,
        "direct_control_diagnostic": direct_report,
        "rank_diagnostic": rank,
        "feature_contribution_diagnostic": contribution,
        "fit": augmented_report,
        "numerical_gate": {**numerical, "pass": all(numerical.values())},
        "representation_gate": representation,
        "usefulness_gate": {"holdout_rmse_less_than_f129_static_baseline": usefulness, "threshold_rmse": F129_STATIC_HOLDOUT_RMSE},
        "metrics": metrics,
        "classification": classification,
        "runtime_seconds": time.time() - started,
    }


def run(output: Path | None = None) -> dict:
    return _run(output or Path(".generic_chess_flow/f130-shogi-result.json"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"classification": result["classification"], "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))


if __name__ == "__main__":
    main()
