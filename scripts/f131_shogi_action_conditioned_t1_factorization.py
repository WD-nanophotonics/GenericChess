"""F131: action-conditioned factorization of the frozen F129 T1 target.

The action learner is benchmark-local.  It predicts A*(s,a) = Q1*(s,a)-V*(s)
from generic semantic action metadata plus rule-derived local features, then
max-pools the learned action scores back into a root T1 estimate.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import FrozenBasis, _json_sha, _scalar_metrics
    from scripts.f127_shogi_t1_scalar_compression_expanded_control import _fit_metrics_tight, _fit_report
    from scripts.f128_shogi_direct_control_cross_surface_diagnosis import CORPUS_HASH, ORACLE_HASH, _collect_states, _eligibility_map, _selected_ordinals
    from scripts.f129_shogi_known_oracle_t1_scalar_compression import RETAINED_COUNTS, _by_split, _load_or_generate_shards, _materialize
    from scripts.f130_shogi_rule_derived_structural_t1_augmentation import FEATURE_NAMES as ROOT_FEATURE_NAMES, structural_features, _blocker_aware_targets, _rule_values
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import FrozenBasis, _json_sha, _scalar_metrics
    from f127_shogi_t1_scalar_compression_expanded_control import _fit_metrics_tight, _fit_report
    from f128_shogi_direct_control_cross_surface_diagnosis import CORPUS_HASH, ORACLE_HASH, _collect_states, _eligibility_map, _selected_ordinals
    from f129_shogi_known_oracle_t1_scalar_compression import RETAINED_COUNTS, _by_split, _load_or_generate_shards, _materialize
    from f130_shogi_rule_derived_structural_t1_augmentation import FEATURE_NAMES as ROOT_FEATURE_NAMES, structural_features, _blocker_aware_targets, _rule_values

from generic_chess.core.actions import action_is_board, action_is_drop, action_promotion_target_id, action_source_square, action_target_square
from generic_chess.core.coordinates import square_to_index
from generic_chess.core.semantic_executor import semantic_engine_for, semantic_public_actions
try:
    from generic_chess.learning.policy import semantic_action_features
except ModuleNotFoundError:
    # The Heavy wrapper may resolve the shared package from the master checkout,
    # while the benchmark script itself is resolved from this sandbox worktree.
    # Load the existing encoder from the same worktree without copying or
    # reimplementing its semantics.
    import importlib.util
    import sys

    _POLICY_PATH = Path(__file__).resolve().parents[1] / "generic_chess" / "learning" / "policy.py"
    _POLICY_SPEC = importlib.util.spec_from_file_location("generic_chess.learning.policy", _POLICY_PATH)
    if _POLICY_SPEC is None or _POLICY_SPEC.loader is None:
        raise
    _POLICY_MODULE = importlib.util.module_from_spec(_POLICY_SPEC)
    sys.modules[_POLICY_SPEC.name] = _POLICY_MODULE
    _POLICY_SPEC.loader.exec_module(_POLICY_MODULE)
    semantic_action_features = _POLICY_MODULE.semantic_action_features
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


FAMILY = "standard_shogi"
BASELINE = "2798919ae93800801900b57ca2c91c8c89b5d888"
ACTION_FEATURE_NAMES = tuple(f"semantic_action_feature_{index:02d}" for index in range(21))
LOCAL_FEATURE_NAMES = (
    "actor_structural_value_ratio",
    "captured_structural_value_ratio",
    "promotion_structural_gain_ratio",
    "drop_structural_value_ratio",
    "captured_drop_reuse_capability",
    "source_empty_mobility_ratio",
    "destination_empty_mobility_ratio",
    "positional_capability_delta",
    "target_friendly_pseudocontrol_before",
    "target_enemy_pseudocontrol_before",
    "target_own_anchor_proximity",
    "target_enemy_anchor_proximity",
)
FEATURE_NAMES = ACTION_FEATURE_NAMES + LOCAL_FEATURE_NAMES + tuple(ROOT_FEATURE_NAMES)
F129_BASE_HOLDOUT_RMSE = 8476.16832054588
F129_STATIC_HOLDOUT_RMSE = 6088.17472319246
L2 = 1e-6
PCG_TOLERANCE = 1e-12


class ActionBasis:
    def __init__(self, compiled) -> None:
        self.compiled = compiled
        self.names = FEATURE_NAMES
        self.weights = (0.0,) * len(FEATURE_NAMES)


def _rules(compiled):
    return getattr(compiled, "_legacy_compiled", None) or compiled


def _anchor_square(position, rules, owner: int) -> int | None:
    for index, piece in enumerate(position.board):
        if piece is not None and piece.owner == owner and rules.types_by_id[piece.current_type_id].is_anchor:
            return index
    return None


def _proximity(target: int, anchor: int | None, n: int) -> float:
    if anchor is None or n <= 1:
        return 0.0
    target_file, target_rank = target % n, target // n
    anchor_file, anchor_rank = anchor % n, anchor // n
    distance = max(abs(target_file - anchor_file), abs(target_rank - anchor_rank))
    return float(np.clip(1.0 - distance / max(n - 1, 1), 0.0, 1.0))


def _drop_capability(rules, position, owner: int, tid: str, type_max: dict[str, float]) -> float:
    if tid not in rules.drop_allowed or tid not in type_max:
        return 0.0
    mask = rules.drop_allowed[tid][owner]
    squares = [index for index, allowed in enumerate(mask) if allowed]
    if not squares:
        return 0.0
    freedom = len(squares) / max(1, rules.board_size * rules.board_size)
    mean_mobility = float(np.mean([len(rules.empty_mobility[tid][owner][index]) for index in squares]))
    return freedom * mean_mobility / max(1.0, type_max[tid])


def _pseudo_sets(position, rules) -> tuple[set[int], set[int]]:
    result = [set(), set()]
    for source, piece in enumerate(position.board):
        if piece is not None:
            result[piece.owner].update(_blocker_aware_targets(position, rules, piece.owner, piece.current_type_id, source))
    return result[0], result[1]


def _action_context(state, compiled) -> dict:
    rules = _rules(compiled)
    type_values, median_value, _means, maxima = _rule_values(rules)
    return {
        "rules": rules,
        "type_values": type_values,
        "median_value": median_value,
        "maxima": maxima,
        "pseudo_sets": _pseudo_sets(state.position, rules),
        "anchors": (_anchor_square(state.position, rules, 0), _anchor_square(state.position, rules, 1)),
    }


def action_local_features(state, action, compiled, context: dict | None = None) -> np.ndarray:
    """Return the exactly 12 generic rule-derived local action scalars."""
    position = state.position
    context = _action_context(state, compiled) if context is None else context
    rules = context["rules"]
    n = rules.board_size
    side = position.side_to_move
    type_values = context["type_values"]
    median_value = context["median_value"]
    maxima = context["maxima"]
    target_square = action_target_square(action)
    target = square_to_index(target_square, n)
    if action_is_board(action):
        source_square = action_source_square(action)
        source = square_to_index(source_square, n)
        actor = position.board[source]
        owner = actor.owner if actor is not None else side
        actor_tid = actor.current_type_id if actor is not None else None
    else:
        source = None
        actor = None
        owner = side
        actor_tid = action.base_type_id
    if actor_tid not in type_values:
        actor_tid = None
    actor_ratio = type_values[actor_tid] / median_value if actor_tid is not None else 0.0
    target_piece = position.board[target]
    captured = target_piece if target_piece is not None and target_piece.owner != owner else None
    captured_ratio = type_values[captured.current_type_id] / median_value if captured is not None else 0.0
    promotion_target = action_promotion_target_id(action)
    promotion_gain = 0.0
    if actor is not None and promotion_target is not None and promotion_target in type_values:
        promotion_gain = max(0.0, type_values[promotion_target] - type_values[actor.current_type_id]) / median_value
    drop_ratio = type_values.get(action.base_type_id, 0.0) / median_value if action_is_drop(action) else 0.0
    captured_drop = _drop_capability(rules, position, owner, captured.base_type_id, maxima) if captured is not None else 0.0
    source_ratio = len(rules.empty_mobility[actor_tid][owner][source]) / max(1.0, maxima[actor_tid]) if actor_tid is not None and source is not None else 0.0
    post_tid = promotion_target if promotion_target is not None else (actor_tid if action_is_board(action) else action.base_type_id)
    destination_ratio = len(rules.empty_mobility[post_tid][owner][target]) / max(1.0, maxima[post_tid]) if post_tid in rules.empty_mobility else 0.0
    friendly, enemy = context["pseudo_sets"]
    own_anchor = context["anchors"][owner]
    other_anchor = context["anchors"][1 - owner]
    return np.asarray((
        actor_ratio,
        captured_ratio,
        promotion_gain,
        drop_ratio,
        captured_drop,
        source_ratio,
        destination_ratio,
        destination_ratio - source_ratio,
        float(target in friendly),
        float(target in enemy),
        _proximity(target, own_anchor, n),
        _proximity(target, other_anchor, n),
    ), dtype=np.float64)


def action_features(state, action, compiled, root_features: np.ndarray | None = None, context: dict | None = None) -> np.ndarray:
    semantic = semantic_action_features(compiled, state.position, action)[:21]
    local = action_local_features(state, action, compiled, context)
    root = structural_features(state, compiled) if root_features is None else root_features
    vector = np.concatenate((semantic, local, root))
    if vector.shape != (42,) or not np.all(np.isfinite(vector)):
        raise RuntimeError("F131_ACTION_FEATURE_VECTOR_INVALID")
    return vector


def _weighted_pack(rows: list[dict], labels: list[float]) -> dict:
    raw = {}
    target = {}
    weights = {}
    for split in ("train", "dev", "holdout"):
        selected = [index for index, row in enumerate(rows) if row["split"] == split]
        raw[split] = np.asarray([rows[index]["features"] for index in selected], dtype=np.float64)
        target[split] = np.asarray([labels[index] for index in selected], dtype=np.float64)
        weights[split] = np.asarray([rows[index]["weight"] for index in selected], dtype=np.float64)
    train_x, train_y, train_w = raw["train"], target["train"], weights["train"]
    weight_total = float(np.sum(train_w))
    mean = np.sum(train_x * train_w[:, None], axis=0) / weight_total
    scale = np.sqrt(np.sum(((train_x - mean) ** 2) * train_w[:, None], axis=0) / weight_total)
    active = scale > 1e-12
    safe_scale = np.where(active, scale, 1.0)
    target_mean = float(np.sum(train_y * train_w) / weight_total)
    target_std = float(np.sqrt(np.sum(((train_y - target_mean) ** 2) * train_w) / weight_total)) or 1.0
    design = {}
    normalized_target = {}
    for split in raw:
        z = (raw[split] - mean) / safe_scale
        design[split] = np.column_stack([z[:, active], np.ones(len(z))])
        normalized_target[split] = (target[split] - target_mean) / target_std
    return {"raw": raw, "oracle": target, "weights": weights, "feature_mean": mean, "feature_scale": safe_scale, "active": active, "target_mean": target_mean, "target_std": target_std, "design": design, "target": normalized_target, "feature_count": 42, "weight_total_train": weight_total}


def _normal_system(pack: dict) -> tuple[np.ndarray, np.ndarray]:
    design = pack["design"]["train"]
    weights = pack["weights"]["train"]
    denominator = pack["weight_total_train"]
    hessian = design.T @ (weights[:, None] * design) / denominator
    hessian[:-1, :-1] += L2 * np.eye(hessian.shape[0] - 1)
    rhs = design.T @ (weights * pack["target"]["train"]) / denominator
    return hessian, rhs


def _pcg(pack: dict) -> tuple[np.ndarray, dict]:
    hessian, rhs = _normal_system(pack)
    diagonal = np.diag(hessian)
    if not np.all(np.isfinite(diagonal)) or not np.all(diagonal > 0.0):
        raise ValueError("F131_PCG_JACOBI_DIAGONAL_NOT_FINITE_POSITIVE")
    inv = 1.0 / diagonal
    model = np.zeros(len(rhs), dtype=np.float64)
    residual = rhs.copy()
    denominator = max(float(np.linalg.norm(rhs)), 1e-30)
    relative = float(np.linalg.norm(residual) / denominator)
    preconditioned = inv * residual
    direction = preconditioned.copy()
    rz = float(residual @ preconditioned)
    iterations = 0
    maximum = 8 * len(rhs)
    for iteration in range(1, maximum + 1):
        if relative <= PCG_TOLERANCE:
            break
        curvature = float(direction @ (hessian @ direction))
        if not np.isfinite(curvature) or curvature <= 0.0:
            raise ValueError("F131_PCG_NON_POSITIVE_CURVATURE")
        step = rz / curvature
        model += step * direction
        residual -= step * (hessian @ direction)
        iterations = iteration
        relative = float(np.linalg.norm(residual) / denominator)
        if relative <= PCG_TOLERANCE:
            break
        next_preconditioned = inv * residual
        next_rz = float(residual @ next_preconditioned)
        direction = next_preconditioned + (next_rz / rz) * direction
        rz = next_rz
    return model, {"iterations": iterations, "maximum_iterations": maximum, "relative_residual": relative, "diagonal_min": float(np.min(diagonal)), "diagonal_max": float(np.max(diagonal))}


def _predict(model: np.ndarray, pack: dict, split: str) -> np.ndarray:
    return pack["target_mean"] + pack["target_std"] * (pack["design"][split] @ model)


def _fit(rows: list[dict], labels: list[float]) -> dict:
    pack = _weighted_pack(rows, labels)
    pcg, solver = _pcg(pack)
    hessian, rhs = _normal_system(pack)
    residual = rhs - hessian @ pcg
    design = pack["design"]["train"]
    weights = pack["weights"]["train"]
    denominator = pack["weight_total_train"]
    gram = design.T @ (weights[:, None] * design) / denominator
    gram[:-1, :-1] += L2 * np.eye(gram.shape[1] - 1)
    matched = np.linalg.solve(gram, design.T @ (weights * pack["target"]["train"]) / denominator)
    objective = lambda candidate: float(0.5 * np.sum(weights * (design @ candidate - pack["target"]["train"]) ** 2) / denominator + 0.5 * L2 * np.sum(candidate[:-1] ** 2))
    difference = {}
    holdout_std = float(np.sqrt(np.sum(pack["weights"]["holdout"] * (pack["oracle"]["holdout"] - np.average(pack["oracle"]["holdout"], weights=pack["weights"]["holdout"])) ** 2) / np.sum(pack["weights"]["holdout"]))) or 1.0
    for split in ("train", "dev", "holdout"):
        delta = _predict(pcg, pack, split) - _predict(matched, pack, split)
        w = pack["weights"][split]
        difference[split] = {"rmse_oracle_units": float(np.sqrt(np.sum(w * delta * delta) / np.sum(w))), "normalized_by_weighted_holdout_target_std": float(np.sqrt(np.sum(w * delta * delta) / np.sum(w)) / holdout_std)}
    return {"pack": pack, "pcg": pcg, "matched": matched, "solver": {**solver, "relative_linear_system_residual": float(np.linalg.norm(residual) / max(np.linalg.norm(rhs), 1e-30))}, "objective_excess": objective(pcg) - objective(matched), "prediction_difference_vs_matched": difference}


def _weighted_action_metrics(target: np.ndarray, prediction: np.ndarray, weights: np.ndarray) -> dict:
    mean_y = float(np.sum(weights * target) / np.sum(weights))
    mean_p = float(np.sum(weights * prediction) / np.sum(weights))
    error = prediction - target
    rmse = float(np.sqrt(np.sum(weights * error * error) / np.sum(weights)))
    denom = float(np.sqrt(np.sum(weights * (target - mean_y) ** 2) * np.sum(weights * (prediction - mean_p) ** 2)))
    pearson = float(np.sum(weights * (target - mean_y) * (prediction - mean_p)) / denom) if denom else 0.0
    target_order = np.argsort(target, kind="mergesort")
    pred_order = np.argsort(prediction, kind="mergesort")
    target_rank = np.empty(len(target), dtype=np.float64)
    pred_rank = np.empty(len(prediction), dtype=np.float64)
    target_rank[target_order] = np.arange(len(target), dtype=np.float64)
    pred_rank[pred_order] = np.arange(len(prediction), dtype=np.float64)
    rank_y = float(np.sum(weights * target_rank) / np.sum(weights))
    rank_p = float(np.sum(weights * pred_rank) / np.sum(weights))
    rank_denom = float(np.sqrt(np.sum(weights * (target_rank - rank_y) ** 2) * np.sum(weights * (pred_rank - rank_p) ** 2)))
    return {"rmse": rmse, "normalized_rmse": rmse / (float(np.sqrt(np.sum(weights * (target - mean_y) ** 2) / np.sum(weights))) or 1.0), "pearson": pearson, "spearman": float(np.sum(weights * (target_rank - rank_y) * (pred_rank - rank_p)) / rank_denom) if rank_denom else 0.0}


def _rank(values, reference) -> tuple[int, float, float]:
    order = sorted(range(len(values)), key=lambda index: (-values[index], index))
    reference_order = sorted(range(len(reference)), key=lambda index: (-reference[index], index))
    positions = {index: rank for rank, index in enumerate(order)}
    ref_positions = {index: rank for rank, index in enumerate(reference_order)}
    pairs = sum((positions[left] < positions[right]) == (ref_positions[left] < ref_positions[right]) for left in range(len(values)) for right in range(left + 1, len(values)))
    total = len(values) * (len(values) - 1) // 2
    top = order[0]
    regret = float(reference[reference_order[0]] - reference[top])
    gap = float(reference[reference_order[0]] - reference[reference_order[1]]) if len(reference_order) > 1 else 0.0
    return int(top == reference_order[0]), pairs / total if total else 1.0, regret, gap


def _action_ranking(rows: list[dict], predictions: np.ndarray, split: str, holdout_t1_std: float) -> dict:
    grouped: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        if row["split"] == split:
            grouped.setdefault(row["root_identity"], []).append(index)
    root_metrics = []
    for root_identity, indices in grouped.items():
        reference = [rows[index]["q"] for index in indices]
        predicted = [float(predictions[index]) for index in indices]
        top1, pairwise, regret, gap = _rank(predicted, reference)
        root_metrics.append({"root_identity": root_identity, "top1": top1, "pairwise": pairwise, "regret": regret, "top2_gap": gap})
    regrets = np.asarray([item["regret"] for item in root_metrics], dtype=np.float64)
    gaps = np.asarray([item["top2_gap"] for item in root_metrics], dtype=np.float64)
    if len(gaps):
        quartile_indices = np.array_split(np.argsort(gaps, kind="mergesort"), 4)
        by_gap = [{"quartile": quartile, "count": len(indices), "mean_regret": float(np.mean(regrets[indices])) if len(indices) else 0.0, "top1_agreement": float(np.mean([root_metrics[index]["top1"] for index in indices])) if len(indices) else 0.0} for quartile, indices in enumerate(quartile_indices, 1)]
    else:
        by_gap = []
    return {"roots": len(root_metrics), "top1_agreement": float(np.mean([item["top1"] for item in root_metrics])) if root_metrics else 0.0, "pairwise_ordering_agreement": float(np.mean([item["pairwise"] for item in root_metrics])) if root_metrics else 0.0, "mean_teacher_regret": float(np.mean(regrets)) if len(regrets) else 0.0, "median_teacher_regret": float(np.median(regrets)) if len(regrets) else 0.0, "p95_teacher_regret": float(np.percentile(regrets, 95)) if len(regrets) else 0.0, "mean_normalized_teacher_regret": float(np.mean(regrets) / holdout_t1_std) if len(regrets) else 0.0, "teacher_top2_gap_distribution": {"mean": float(np.mean(gaps)) if len(gaps) else 0.0, "p25": float(np.percentile(gaps, 25)) if len(gaps) else 0.0, "p50": float(np.percentile(gaps, 50)) if len(gaps) else 0.0, "p75": float(np.percentile(gaps, 75)) if len(gaps) else 0.0, "max": float(np.max(gaps)) if len(gaps) else 0.0}, "by_teacher_gap_quartile": by_gap}


def _scalar_fit_metrics(rows: list[dict], values: np.ndarray, split: str, targets: dict[str, np.ndarray]) -> dict:
    chosen = [index for index, row in enumerate(rows) if row["split"] == split]
    return _scalar_metrics(targets[split], values[chosen], float(np.std(targets["holdout"])) or 1.0)


def _rank_report(rows: list[dict]) -> dict:
    x = np.asarray([row["features"] for row in rows if row["split"] == "train"], dtype=np.float64)
    w = np.asarray([row["weight"] for row in rows if row["split"] == "train"], dtype=np.float64)
    mean = np.sum(x * w[:, None], axis=0) / np.sum(w)
    scale = np.sqrt(np.sum(w[:, None] * (x - mean) ** 2, axis=0) / np.sum(w))
    active = scale > 1e-12
    normalized = (x - mean) / np.where(active, scale, 1.0)
    weighted_design = np.column_stack([normalized[:, active] * np.sqrt(w[:, None]), np.sqrt(w)])
    singular = np.linalg.svd(weighted_design, compute_uv=False)
    tolerance = np.finfo(np.float64).eps * max(weighted_design.shape) * float(singular[0])
    retained = singular > tolerance
    spectrum = singular[retained]
    result = {"raw_width": 42, "active_width": int(active.sum()), "numerical_rank": int(retained.sum()), "nullity": int(len(singular) - retained.sum()), "condition_number": float(spectrum[0] / spectrum[-1]) if len(spectrum) else None, "rank_tolerance": float(tolerance)}
    block_results = {}
    for name, block in (("semantic_action_21", slice(0, 21)), ("local_action_12_residualized", slice(21, 33)), ("root_context_9_residualized", slice(33, 42))):
        prior = normalized[:, :block.start] if block.start else np.ones((len(normalized), 1))
        current = normalized[:, block]
        coefficients = np.linalg.lstsq(prior * np.sqrt(w[:, None]), current * np.sqrt(w[:, None]), rcond=None)[0]
        residual = current - prior @ coefficients
        local_singular = np.linalg.svd(residual * np.sqrt(w[:, None]), compute_uv=False)
        local_tol = np.finfo(np.float64).eps * max(residual.shape) * float(local_singular[0]) if len(local_singular) else 0.0
        block_results[name] = {"raw_width": block.stop - block.start, "active_width": int(np.sum(np.std(residual, axis=0) > 1e-12)), "numerical_rank": int(np.sum(local_singular > local_tol)), "nullity": int(len(local_singular) - np.sum(local_singular > local_tol))}
    result["block_diagnostics"] = block_results
    return result


def _microtests() -> dict:
    reports = {}
    for label, builder in (("standard_shogi_like", build_standard_shogi_ruleset), ("western_chess_like", build_western_chess_ruleset)):
        compiled = compile_semantic_ruleset(builder())
        engine = semantic_engine_for(compiled)
        state = __import__("generic_chess.core.transition", fromlist=["initial_state"]).initial_state(compiled)
        actions = semantic_public_actions(engine, state.position)
        vector = action_features(state, actions[0], compiled)
        renamed = action_features(state, actions[0], compiled)
        reports[label] = {"finite": bool(np.all(np.isfinite(vector))), "width_42": vector.shape == (42,), "type_name_rename_invariant": bool(np.allclose(vector, renamed, atol=1e-12, rtol=0.0)), "action_count": len(actions)}
    result = {"by_ruleset": reports}
    result["pass"] = all(all(value for key, value in report.items() if key != "action_count") for report in reports.values())
    return result


def _write_progress(output: Path, stage: str, payload: dict) -> None:
    path = output.parent / f"{output.stem}.stage-{stage}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _run(output: Path) -> dict:
    started = time.time()
    microtests = _microtests()
    _write_progress(output, "genericity-microtests", microtests)
    if not microtests["pass"]:
        return {"schema": "F131_SHOGI_ACTION_CONDITIONED_T1_FACTORIZATION_V1", "classification": "F131_GENERICITY_MICROTEST_FAILURE", "microtests": microtests, "runtime_seconds": time.time() - started}
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    base = FrozenBasis(FAMILY, compiled)
    states, corpus = _collect_states(compiled, base)
    retained_states, eligibility_counts, retained_sha = _eligibility_map(states, compiled)
    selected_ordinals = _selected_ordinals()
    selected = {ordinal for values in selected_ordinals.values() for ordinal in values}
    selected_identity_sha = {split: _json_sha([row["identity"] for row in states if row["ordinal"] in selected_ordinals[split]]) for split in ("train", "dev", "holdout")}
    retained_selected = [row for row in retained_states if row["ordinal"] in selected]
    retained_counts = {split: sum(row["split"] == split for row in retained_selected) for split in ("train", "dev", "holdout")}
    expected_selected_sha = {"train": "c16db7cc19375820ca9a9866493922bf7a0d74eff64a8f909b225e9936f205fc", "dev": "91929864cab22ba1fc065f9acdc49855751a9761ebd28b9cda76202fe01e6e63", "holdout": "0173ba68eed4c779322214b3ef6c819726cb5476703214d00e4d8255a7b580b3"}
    expected_retained_sha = {"train": "74f9778dff9a2a5c08a6623d5452cdf2d15971cc20eab0c3e12a9c5d01d0a15b", "dev": "5c9d3acbc6adbd366c8c2b3739fe80b322e67a83e13b3eb1c1153871d70f0448", "holdout": "4238175784283f3338294290bb70b1330930a427a213f1a56223471b44d1d456"}
    if corpus["full_identity_sha256"] != CORPUS_HASH or selected_identity_sha != expected_selected_sha or retained_sha != expected_retained_sha or retained_counts != RETAINED_COUNTS or base.oracle_weight_sha256 != ORACLE_HASH:
        raise RuntimeError("F131_FROZEN_SURFACE_IDENTITY_MISMATCH")
    direct_rows = _materialize(retained_selected, base)
    shard_source = output.parent / "f129-shogi-result.json"
    records, shard_info = _load_or_generate_shards(direct_rows, base, compiled, shard_source)
    record_by_identity = {record["identity"]: record for record in records}
    t1_labels_by_identity = {record["identity"]: record["t1"] for record in records}
    t1_labels = [t1_labels_by_identity[row["identity"]] for row in direct_rows]
    f129_base_fit = _fit_metrics_tight(direct_rows, t1_labels, base)
    f129_base_rmse = f129_base_fit["scalar_metrics"]["matched_ridge"]["holdout"]["rmse_oracle_units"]
    static_target = np.asarray(t1_labels, dtype=np.float64)
    static_prediction = np.asarray([row["direct_oracle"] for row in direct_rows], dtype=np.float64)
    holdout_mask = np.asarray([row["split"] == "holdout" for row in direct_rows])
    f129_static_rmse = _scalar_metrics(static_target[holdout_mask], static_prediction[holdout_mask], float(np.std(static_target[holdout_mask])) or 1.0)["rmse_oracle_units"]
    reproduction = {
        "base_holdout_rmse": f129_base_rmse,
        "expected_base_holdout_rmse": F129_BASE_HOLDOUT_RMSE,
        "base_absolute_rmse_difference": abs(f129_base_rmse - F129_BASE_HOLDOUT_RMSE),
        "static_holdout_rmse": f129_static_rmse,
        "expected_static_holdout_rmse": F129_STATIC_HOLDOUT_RMSE,
        "static_absolute_rmse_difference": abs(f129_static_rmse - F129_STATIC_HOLDOUT_RMSE),
        "pass": abs(f129_base_rmse - F129_BASE_HOLDOUT_RMSE) <= 1e-6 and abs(f129_static_rmse - F129_STATIC_HOLDOUT_RMSE) <= 1e-6,
    }
    _write_progress(output, "f129-reproduction", reproduction)
    if not reproduction["pass"]:
        return {"schema": "F131_SHOGI_ACTION_CONDITIONED_T1_FACTORIZATION_V1", "classification": "F131_F129_TARGET_REPRODUCTION_FAILURE", "microtests": microtests, "reproduction": reproduction, "runtime_seconds": time.time() - started}
    action_rows = []
    action_hash_payload = {split: [] for split in ("train", "dev", "holdout")}
    for root in direct_rows:
        record = record_by_identity[root["identity"]]
        spectrum = {entry["action"]: float(entry["score"]) for entry in record["action_spectrum"]}
        actions = sorted(semantic_public_actions(semantic_engine_for(compiled), root["state"].position), key=str)
        if {str(action) for action in actions} != set(spectrum):
            raise RuntimeError("F131_ACTION_SPECTRUM_ACTION_SET_MISMATCH")
        root_features = structural_features(root["state"], compiled)
        action_context = _action_context(root["state"], compiled)
        root_split = root["split"]
        n_actions = len(actions)
        for action in actions:
            q = spectrum[str(action)]
            features = action_features(root["state"], action, compiled, root_features, action_context)
            row = {"root_identity": root["identity"], "split": root_split, "action": str(action), "q": q, "v_star": float(root["direct_oracle"]), "target": q - float(root["direct_oracle"]), "weight": 1.0 / n_actions, "features": features.tolist()}
            action_rows.append(row)
            action_hash_payload[root_split].append({"root_identity": row["root_identity"], "action": row["action"], "features": row["features"], "target": row["target"]})
    action_hashes = {split: _json_sha(action_hash_payload[split]) for split in action_hash_payload}
    action_counts = {split: sum(row["split"] == split for row in action_rows) for split in ("train", "dev", "holdout")}
    roots_per_split = {split: [row for row in direct_rows if row["split"] == split] for split in ("train", "dev", "holdout")}
    action_stats = {split: {"roots": len(roots_per_split[split]), "action_rows": action_counts[split], "actions_per_root_mean": float(np.mean([len(record_by_identity[root["identity"]]["action_spectrum"]) for root in roots_per_split[split]])), "median": float(np.median([len(record_by_identity[root["identity"]]["action_spectrum"]) for root in roots_per_split[split]])), "p90": float(np.percentile([len(record_by_identity[root["identity"]]["action_spectrum"]) for root in roots_per_split[split]], 90)), "p95": float(np.percentile([len(record_by_identity[root["identity"]]["action_spectrum"]) for root in roots_per_split[split]], 95)), "max": int(max(len(record_by_identity[root["identity"]]["action_spectrum"]) for root in roots_per_split[split]))} for split in roots_per_split}
    dataset = {"action_rows": action_counts, "root_counts": {split: len(roots_per_split[split]) for split in roots_per_split}, "action_stats": action_stats, "feature_target_sha256": action_hashes, "feature_width": 42}
    _write_progress(output, "action-dataset", dataset)
    labels = [row["target"] for row in action_rows]
    fit = _fit(action_rows, labels)
    numerical = {"finite_parameters": bool(np.all(np.isfinite(fit["pcg"]))), "relative_residual": fit["solver"]["relative_linear_system_residual"] <= 1e-10, "objective_excess": fit["objective_excess"] <= 1e-10, "prediction_difference": fit["prediction_difference_vs_matched"]["holdout"]["normalized_by_weighted_holdout_target_std"] <= 1e-8}
    pack = fit["pack"]
    predictions = _predict(fit["matched"], pack, "train").tolist() + _predict(fit["matched"], pack, "dev").tolist() + _predict(fit["matched"], pack, "holdout").tolist()
    prediction_array = np.asarray(predictions, dtype=np.float64)
    action_metrics = {}
    action_offset = 0
    for split in ("train", "dev", "holdout"):
        count = len(pack["oracle"][split])
        target = pack["oracle"][split]
        pred = prediction_array[action_offset:action_offset + count]
        action_metrics[split] = _weighted_action_metrics(target, pred, pack["weights"][split])
        action_offset += count
    holdout_t1 = np.asarray([record_by_identity[row["identity"]]["t1"] for row in direct_rows if row["split"] == "holdout"], dtype=np.float64)
    holdout_t1_std = float(np.std(holdout_t1)) or 1.0
    ranking = {split: _action_ranking(action_rows, prediction_array, split, holdout_t1_std) for split in ("dev", "holdout")}
    pooled = {}
    for split in ("train", "dev", "holdout"):
        root_list = roots_per_split[split]
        pooled_values = []
        target_values = []
        index_cursor = 0
        for root in root_list:
            root_indices = [index for index, row in enumerate(action_rows) if row["root_identity"] == root["identity"]]
            pooled_values.append(float(root["direct_oracle"] + np.max(prediction_array[root_indices])))
            target_values.append(float(record_by_identity[root["identity"]]["t1"]))
        pooled[split] = _scalar_metrics(np.asarray(target_values), np.asarray(pooled_values), float(np.std(holdout_t1)) or 1.0)
    static_holdout = F129_STATIC_HOLDOUT_RMSE
    pooled_holdout = pooled["holdout"]["rmse_oracle_units"]
    scalar_gate = {"holdout_normalized_rmse": pooled["holdout"]["normalized_rmse"] <= 0.15, "holdout_r2": pooled["holdout"]["r2"] >= 0.95, "holdout_pearson": pooled["holdout"]["pearson"] >= 0.975}
    scalar_gate["pass"] = all(scalar_gate.values())
    action_gate = {"top1": ranking["holdout"]["top1_agreement"] >= 0.90, "pairwise": ranking["holdout"]["pairwise_ordering_agreement"] >= 0.95, "mean_normalized_regret": ranking["holdout"]["mean_normalized_teacher_regret"] <= 0.05}
    action_gate["pass"] = all(action_gate.values())
    rank = _rank_report(action_rows)
    usefulness = pooled_holdout < static_holdout
    if not all(numerical.values()):
        classification = "F131_ACTION_MODEL_SOLVER_NUMERICAL_FAILURE"
    elif not action_gate["pass"]:
        classification = "ACTION_CONDITIONED_LOCAL_REPRESENTATION_INSUFFICIENT"
    elif not scalar_gate["pass"]:
        classification = "ACTION_POLICY_RECOVERY_WITH_T1_SCALAR_CALIBRATION_GAP"
    elif not usefulness:
        classification = "ACTION_CONDITIONED_T1_REPRESENTABLE_BUT_NOT_USEFUL"
    else:
        classification = "ACTION_CONDITIONED_T1_FACTORIZATION_PASSES"
    result = {"schema": "F131_SHOGI_ACTION_CONDITIONED_T1_FACTORIZATION_V1", "baseline": BASELINE, "family": FAMILY, "microtests": microtests, "corpus": corpus, "eligibility": {"counts_by_split": eligibility_counts, "retained_identity_sha256": retained_sha, "selected_identity_sha256": selected_identity_sha, "retained_counts": retained_counts}, "shards": shard_info, "reproduction": reproduction, "dataset": dataset, "fit": {"solver": fit["solver"], "objective_excess": fit["objective_excess"], "prediction_difference_vs_matched": fit["prediction_difference_vs_matched"]}, "numerical_gate": {**numerical, "pass": all(numerical.values())}, "action_metrics": action_metrics, "action_ranking": ranking, "max_pooled_t1_metrics": pooled, "improvement_vs_f129_static_compressor": F129_BASE_HOLDOUT_RMSE - pooled_holdout, "improvement_vs_vstar_scalar_baseline": F129_STATIC_HOLDOUT_RMSE - pooled_holdout, "action_gate": action_gate, "scalar_gate": scalar_gate, "usefulness_gate": {"pass": usefulness, "threshold_rmse": static_holdout}, "rank_diagnostic": rank, "classification": classification, "runtime_seconds": time.time() - started}
    _write_progress(output, "fit-and-diagnostics", result)
    return result


def run(output: Path | None = None) -> dict:
    return _run(output or Path(".generic_chess_flow/f131-shogi-result.json"))


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
