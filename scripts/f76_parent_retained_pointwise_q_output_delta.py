"""F76 pointwise-Q, output-layer-only correction for the retained Gen1 model."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.core.actions import action_from_dict  # noqa: E402
from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.native import native_available  # noqa: E402
from generic_chess.native.adapter import pack_semantic_search_position  # noqa: E402
from generic_chess.native.semantic import dynamic_features as native_dynamic_features  # noqa: E402
from generic_chess.native.semantic import evaluate as native_evaluate  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_r2_fresh_strength as f61r2  # noqa: E402
from scripts import f74_parent_retained_output_delta_probe as f74  # noqa: E402


WORK_ORDER = "GENERICCHESS-F76-PARENT-RETAINED-POINTWISE-Q-OUTPUT-DELTA"
PARENT_SHA = "e680f6ab09b15cc13520d8655b7100a1540b8134"
LABEL = "B_CANONICAL_STANDARD_SHOGI"
GEN1_ID = "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
F75_CHILD_ID = "bafabe1a6eeedf30b0ebe34109e5c4efdad87fc434edf8e75e9030e958bca0bb"
F75_DESCRIPTOR = ROOT / "artifacts" / "f75_parent_retained_arena" / "candidate.json"
F62_STAGE_SHA = "e7a93423d6058c68fe7ccbc61302584ca1e8869aa828586254f72f4dfdac2c70"
F62_RECORDS_SHA = "b7a6dc134bf1232fa90d9734ad070c184ecd09f691bc92958686093181d3ff61"
ARTIFACTS = ROOT / "artifacts" / "f76_parent_retained_pointwise_q"
CANDIDATE_PATH = ARTIFACTS / "candidate.json"
OUT = ROOT / ".generic_chess_flow" / "f76-parent-retained-pointwise-q"
RESULT_PATH = OUT / "f76_results.json"
FIT_ROOT_COUNT = 48
DEVELOPMENT_ROOT_COUNT = 20
REGULARIZATION = 1e-3
NODES = 2_048
MAX_DEPTH = 12
TT_MEGABYTES = 8


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _action_key(payload: dict | None) -> str | None:
    return None if payload is None else json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _load_gen1(compiled):
    data = json.loads((ROOT / "docs" / "architecture" / "GENERICCHESS_F61_MODEL_PARAMS.json").read_text(encoding="utf-8"))
    row = next(item for item in data["corrected_candidates"] if item["candidate_id"] == "F60_D0_PAIRWISE_SEED_59012")
    gen1 = f61r2._candidate_checkpoint(f59._parent(LABEL), row)
    if gen1.checkpoint_id != GEN1_ID:
        raise RuntimeError("F76 Gen1 identity mismatch")
    gen1.validate_ruleset(compiled)
    return gen1


def _fit_roots() -> list[dict]:
    roots = f74._load_fit_roots()
    if len(roots) != FIT_ROOT_COUNT:
        raise RuntimeError("F76 fit split count mismatch")
    return roots


def _development_roots() -> list[dict]:
    roots = f74._load_development_roots()
    if len(roots) != DEVELOPMENT_ROOT_COUNT:
        raise RuntimeError("F76 stable development root count mismatch")
    return roots


def _root_rows(root: dict, model: CompactNonlinearResidual) -> dict:
    rows = f74._root_rows(root, model)
    q20k = np.asarray([float(item["q_20k"]) for item in root["metadata"]["action_rows"]], dtype=np.float64)
    rows["q20k"] = q20k
    rows["target_residual"] = q20k - rows["base"]
    return rows


def _load_f75_delta() -> np.ndarray:
    payload = json.loads(F75_DESCRIPTOR.read_text(encoding="utf-8"))
    if payload.get("child_checkpoint_id") != F75_CHILD_ID:
        raise RuntimeError("F76 F75 descriptor child identity mismatch")
    delta = np.asarray(payload["raw_delta"], dtype=np.float64)
    if delta.shape != (32,):
        raise RuntimeError("F76 F75 raw delta width mismatch")
    return delta


def _pointwise_rows(roots: list[dict], model: CompactNonlinearResidual) -> list[list[dict]]:
    result = []
    for root in roots:
        static = _root_rows(root, model)
        actions = []
        for index, key in enumerate(static["keys"]):
            actions.append({
                "action_key": key,
                "hidden": static["hidden"][index],
                "target_residual": float(static["target_residual"][index]),
                "parent_residual": float(static["parent_residual"][index]),
                "parent_total": float(static["parent_total"][index]),
            })
        if not actions:
            raise RuntimeError(f"F76 root-{root['root_index']} has no action rows")
        result.append(actions)
    return result


def _pointwise_objective(delta: np.ndarray, rows: list[list[dict]], scale: float, regularization: float) -> float:
    total = 0.0
    root_weight = 1.0 / len(rows)
    for root in rows:
        action_weight = root_weight / len(root)
        for item in root:
            target = (item["target_residual"] - item["parent_residual"]) / scale
            error = float(item["hidden"] @ delta) - target
            total += action_weight * error * error
    return float(total + regularization * (delta @ delta))


def _fit_pointwise_delta(rows: list[list[dict]], width: int, scale: float, regularization: float) -> tuple[np.ndarray, dict]:
    matrix = regularization * np.eye(width, dtype=np.float64)
    vector = np.zeros(width, dtype=np.float64)
    root_weight = 1.0 / len(rows)
    for root in rows:
        action_weight = root_weight / len(root)
        for item in root:
            target = (item["target_residual"] - item["parent_residual"]) / scale
            hidden = np.asarray(item["hidden"], dtype=np.float64)
            matrix += action_weight * np.outer(hidden, hidden)
            vector += action_weight * hidden * target
    delta = np.linalg.solve(matrix, vector)
    initial = _pointwise_objective(np.zeros(width, dtype=np.float64), rows, scale, regularization)
    fitted = _pointwise_objective(delta, rows, scale, regularization)
    return delta, {
        "objective_before": initial,
        "objective_after": fitted,
        "delta_norm": float(np.linalg.norm(delta)),
        "action_row_count": sum(len(root) for root in rows),
        "root_count": len(rows),
        "regularization": regularization,
        "closed_form": True,
    }


def _top_index(scores: np.ndarray, keys: list[str]) -> int:
    return min(range(len(scores)), key=lambda index: (-float(scores[index]), keys[index]))


def _high_confidence_boundary(rows: list[dict], delta: np.ndarray, scale: float) -> tuple[float, dict]:
    margins = []
    for root in rows:
        order = sorted(range(len(root["parent_total"])), key=lambda index: (-float(root["parent_total"][index]), root["keys"][index]))
        margins.append(float(root["parent_total"][order[0]] - root["parent_total"][order[1]]))
    threshold = float(np.percentile(np.asarray(margins, dtype=np.float64), 75.0))
    selected = [root for root, margin in zip(rows, margins) if margin >= threshold]
    boundaries = []
    for root in selected:
        top = _top_index(root["parent_total"], root["keys"])
        for index in range(len(root["keys"])):
            if index == top:
                continue
            margin = (root["parent_total"][top] - root["parent_total"][index]) / scale
            slope = float((root["hidden"][top] - root["hidden"][index]) @ delta)
            if slope < 0.0 and margin > 0.0:
                boundaries.append({"root_index": root["root_index"], "alpha": -margin / slope})
    boundary = min((item["alpha"] for item in boundaries), default=float("inf"))
    return boundary, {
        "upper_quartile_threshold": threshold,
        "selected_root_count": len(selected),
        "finite_boundary_count": len(boundaries),
        "first_boundary": min(boundaries, key=lambda item: item["alpha"]) if boundaries else None,
    }


def _residual_boundary(rows: list[dict], delta: np.ndarray, scale: float) -> tuple[float, dict]:
    parent_max = max(float(np.max(np.abs(root["parent_residual"]))) for root in rows)
    allowed = 2.0 * parent_max
    boundaries = []
    for root in rows:
        change = scale * (root["hidden"] @ delta)
        for index, slope in enumerate(change):
            slope = float(slope)
            if slope > 0.0:
                value = (allowed - float(root["parent_residual"][index])) / slope
            elif slope < 0.0:
                value = (allowed + float(root["parent_residual"][index])) / -slope
            else:
                continue
            if value > 0.0:
                boundaries.append({"root_index": root["root_index"], "alpha": value})
    boundary = min((item["alpha"] for item in boundaries), default=float("inf"))
    return boundary, {
        "parent_max_abs": parent_max,
        "allowed_max_abs": allowed,
        "finite_boundary_count": len(boundaries),
        "first_boundary": min(boundaries, key=lambda item: item["alpha"]) if boundaries else None,
    }


def _make_candidate(gen1, parent_model, delta: np.ndarray, alpha: float):
    candidate_model = replace(
        parent_model,
        output_weights=tuple((np.asarray(parent_model.output_weights) + alpha * delta).tolist()),
        output_bias=parent_model.output_bias,
    )
    training_identity = {
        "work_order": WORK_ORDER,
        "parent_checkpoint_id": gen1.checkpoint_id,
        "fit_method": "deterministic_ridge_pointwise_q_output_delta",
        "fit_regularization": parent_model.regularization,
        "raw_delta": delta.tolist(),
        "alpha": alpha,
    }
    candidate = gen1.child_checkpoint(
        board_weights=gen1.board_weights,
        hand_weights=gen1.hand_weights,
        dynamic_weights=gen1.dynamic_weights,
        compact_nonlinear=candidate_model.to_dict(),
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=stable_sha256(training_identity),
        training_seed=None,
    )
    return candidate_model, candidate, {
        "training_config_hash": stable_sha256(training_identity),
        "model_sha256": stable_sha256(candidate_model.to_dict()),
        "output_weights": list(candidate_model.output_weights),
    }


def _write_or_verify_descriptor(gen1, candidate, candidate_model, delta, alpha, fit_summary, cosine):
    payload = {
        "schema": "generic-chess-f76-pointwise-q-candidate-v1",
        "source_commit": PARENT_SHA,
        "parent_checkpoint_id": gen1.checkpoint_id,
        "child_checkpoint_id": candidate.checkpoint_id,
        "alpha": alpha,
        "raw_delta": delta.tolist(),
        "final_output_weights": list(candidate_model.output_weights),
        "training_config_hash": stable_sha256({
            "work_order": WORK_ORDER,
            "parent_checkpoint_id": gen1.checkpoint_id,
            "fit_method": "deterministic_ridge_pointwise_q_output_delta",
            "fit_regularization": gen1.compact_nonlinear["regularization"],
            "raw_delta": delta.tolist(),
            "alpha": alpha,
        }),
        "candidate_model_sha256": stable_sha256(candidate_model.to_dict()),
        "fit_objective_before": fit_summary["objective_before"],
        "fit_objective_after": fit_summary["objective_after"],
        "f74_delta_cosine": cosine,
    }
    if CANDIDATE_PATH.is_file():
        existing = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
        if existing != payload:
            raise RuntimeError("F76 durable candidate descriptor identity mismatch")
    else:
        _atomic_json(CANDIDATE_PATH, payload)
    return payload


def _representation_guard(compiled, gen1, candidate, parent_model, candidate_model):
    failures = []
    if candidate.ruleset_fingerprint != gen1.ruleset_fingerprint:
        failures.append("ruleset binding changed")
    for field in (
        "input_mean", "input_scale", "target_scale", "hidden_weights",
        "hidden_bias", "output_bias", "width", "hand_type_indices", "perspective",
    ):
        if getattr(parent_model, field) != getattr(candidate_model, field):
            failures.append(f"frozen model field changed: {field}")
    if parent_model.output_weights == candidate_model.output_weights:
        failures.append("output correction is zero")
    candidate.validate_ruleset(compiled)
    return failures


def _native_parity(compiled, native, gen1, candidate, candidate_model, roots):
    failures = []
    rows = []
    for root in roots[:4]:
        session = f59._session(compiled, root["record"])
        for action_row in root["metadata"]["action_rows"][:2]:
            action = action_from_dict(action_row["action"])
            if action not in session.legal_actions():
                failures.append(f"root-{root['root_index']}: cached action is not legal")
                continue
            child_session = f59._session(compiled, root["record"])
            child_session.submit(action)
            packed = pack_semantic_search_position(compiled, native, child_session)
            dynamic = native_dynamic_features(native, packed)
            features = np.asarray([action_row["features"]], dtype=np.float64)
            python_parent = float(CompactNonlinearResidual.from_dict(gen1.compact_nonlinear).predict(features)[0])
            python_candidate = float(candidate_model.predict(features)[0])
            type_ids = tuple(native.type_ids)
            parent_score = native_evaluate(
                native, packed,
                board_values=gen1.semantic_quantized_board(type_ids),
                hand_values=gen1.semantic_quantized_hand(type_ids),
                dynamic_values=gen1.semantic_quantized_dynamic(),
                compact_values=gen1.compact_nonlinear,
                evaluator_scale=gen1.semantic_native_scale,
            )
            candidate_score = native_evaluate(
                native, packed,
                board_values=candidate.semantic_quantized_board(type_ids),
                hand_values=candidate.semantic_quantized_hand(type_ids),
                dynamic_values=candidate.semantic_quantized_dynamic(),
                compact_values=candidate.compact_nonlinear,
                evaluator_scale=candidate.semantic_native_scale,
            )
            expected = -(int(round(python_candidate * candidate.semantic_native_scale)) - int(round(python_parent * gen1.semantic_native_scale)))
            actual = int(candidate_score - parent_score)
            if actual != expected:
                failures.append(f"root-{root['root_index']}: Native/Python residual mismatch")
            rows.append({
                "root_index": root["root_index"],
                "action_key": action_row["action_key"],
                "actual_native_delta": actual,
                "expected_native_delta": expected,
                "dynamic_dimension": len(dynamic),
            })
    return {"rows": rows, "all_exact": not failures, "failures": failures}


def _search_arm(compiled, native, checkpoint, root):
    session = f59._session(compiled, root["record"])
    result = SemanticSearchEngine(compiled, native, checkpoint=checkpoint, tt_megabytes=TT_MEGABYTES).search(
        session,
        SearchLimits(max_depth=MAX_DEPTH, max_nodes=NODES, quiescence_max_depth=0),
        root_window_pruning=True,
    )
    return {
        "action_key": None if result.action is None else _action_key(f59.action_to_dict(result.action)),
        "score": int(result.score),
        "completed_depth": int(result.completed_depth),
        "nodes": int(result.nodes),
        "beta_cutoffs": int(result.beta_cutoffs),
        "tt_probes": int(result.tt_probes),
        "tt_hits": int(result.tt_hits),
        "tt_cutoffs": int(result.tt_cutoffs),
        "termination_reason": str(result.termination_reason),
        "root_window_pruning": bool(getattr(result, "root_window_pruning", False)),
    }


def _development_row(compiled, native, gen1, candidate, root):
    parent = _search_arm(compiled, native, gen1, root)
    parent_repeat = _search_arm(compiled, native, gen1, root)
    child = _search_arm(compiled, native, candidate, root)
    child_repeat = _search_arm(compiled, native, candidate, root)
    deep = root["metadata"]["root_80k"]["action_key"]
    changed = parent["action_key"] != child["action_key"]
    parent_deep = parent["action_key"] == deep
    child_deep = child["action_key"] == deep
    if changed and child_deep and not parent_deep:
        direction = "toward-deep"
    elif changed and parent_deep and not child_deep:
        direction = "away-from-deep"
    elif changed:
        direction = "lateral"
    else:
        direction = None
    return {
        "root_index": root["root_index"],
        "cached_deep_consensus_action_key": deep,
        "parent": parent,
        "parent_repeat": parent_repeat,
        "child": child,
        "child_repeat": child_repeat,
        "deterministic": parent == parent_repeat and child == child_repeat,
        "decision_changed": changed,
        "direction": direction,
        "parent_deep_agreement": parent_deep,
        "child_deep_agreement": child_deep,
    }


def _development_summary(rows):
    changed = [row for row in rows if row["decision_changed"]]
    searches = [
        search for row in rows for search in (row["parent"], row["parent_repeat"], row["child"], row["child_repeat"])
    ]
    return {
        "root_count": len(rows),
        "decision_changes": len(changed),
        "toward_deep": sum(row["direction"] == "toward-deep" for row in rows),
        "away_from_deep": sum(row["direction"] == "away-from-deep" for row in rows),
        "lateral": sum(row["direction"] == "lateral" for row in rows),
        "parent_deep_agreement": sum(row["parent_deep_agreement"] for row in rows),
        "child_deep_agreement": sum(row["child_deep_agreement"] for row in rows),
        "deterministic": all(row["deterministic"] for row in rows),
        "root_window_pruning_all_true": all(search["root_window_pruning"] for search in searches),
        "search_telemetry": {
            "searches": len(searches),
            "beta_cutoffs": sum(search["beta_cutoffs"] for search in searches),
            "tt_probes": sum(search["tt_probes"] for search in searches),
            "tt_hits": sum(search["tt_hits"] for search in searches),
            "tt_cutoffs": sum(search["tt_cutoffs"] for search in searches),
            "completed_depths": {
                str(depth): sum(search["completed_depth"] == depth for search in searches)
                for depth in sorted({search["completed_depth"] for search in searches})
            },
        },
        "rows": rows,
    }


def _provenance() -> dict:
    return {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in (
            "scripts/f76_parent_retained_pointwise_q_output_delta.py",
            "scripts/f74_parent_retained_output_delta_probe.py",
            "scripts/f59_action_spectrum_diagnosis.py",
            "scripts/f61_r2_fresh_strength.py",
            "generic_chess/native/semantic_engine.py",
            "generic_chess/native/semantic.py",
            "docs/architecture/GENERICCHESS_F61_MODEL_PARAMS.json",
        )
    }


def run() -> dict:
    if not native_available():
        raise RuntimeError("F76 requires the native extension")
    compiled, native, _profile = f59._ruleset(LABEL)
    gen1 = _load_gen1(compiled)
    parent_model = CompactNonlinearResidual.from_dict(gen1.compact_nonlinear)
    if parent_model.regularization != REGULARIZATION:
        raise RuntimeError("F76 regularization differs from Gen1")
    fit_roots = _fit_roots()
    fit_data = [_root_rows(root, parent_model) for root in fit_roots]
    pointwise = _pointwise_rows(fit_roots, parent_model)
    delta, fit_summary = _fit_pointwise_delta(pointwise, parent_model.width, parent_model.target_scale, REGULARIZATION)
    f74_delta = _load_f75_delta()
    cosine = float(delta @ f74_delta / (np.linalg.norm(delta) * np.linalg.norm(f74_delta)))
    high_boundary, high_summary = _high_confidence_boundary(fit_data, delta, parent_model.target_scale)
    residual_boundary, residual_summary = _residual_boundary(fit_data, delta, parent_model.target_scale)
    alpha_star = float(min(1.0, 0.5 * high_boundary, residual_boundary))
    candidate_model, candidate, candidate_summary = _make_candidate(gen1, parent_model, delta, alpha_star)
    descriptor = _write_or_verify_descriptor(gen1, candidate, candidate_model, delta, alpha_star, fit_summary, cosine)
    representation_failures = _representation_guard(compiled, gen1, candidate, parent_model, candidate_model)
    parity = _native_parity(compiled, native, gen1, candidate, candidate_model, fit_roots)
    final_fit_data = [_root_rows(root, candidate_model) for root in fit_roots]
    final_objective = _pointwise_objective(alpha_star * delta, pointwise, parent_model.target_scale, REGULARIZATION)
    parent_max = residual_summary["parent_max_abs"]
    candidate_max = max(float(np.max(np.abs(root["parent_residual"]))) for root in final_fit_data)
    high_roots = [root for root, margin in zip(fit_data, [
        max(root["parent_total"]) - sorted(root["parent_total"])[-2] for root in fit_data
    ]) if margin >= high_summary["upper_quartile_threshold"]]
    retention_failures = []
    for parent_root in high_roots:
        candidate_root = next(root for root in final_fit_data if root["root_index"] == parent_root["root_index"])
        parent_top = _top_index(parent_root["parent_total"], parent_root["keys"])
        candidate_top = _top_index(candidate_root["parent_total"], candidate_root["keys"])
        if parent_root["keys"][parent_top] != candidate_root["keys"][candidate_top]:
            retention_failures.append(f"root-{parent_root['root_index']}: high-confidence top action changed")
    contract_failures = list(representation_failures) + list(parity["failures"]) + retention_failures
    if not alpha_star > 0.0:
        contract_failures.append("trust-region alpha is not positive")
    if candidate_max > 2.0 * parent_max:
        contract_failures.append("fit residual cap exceeded")
    if not final_objective < fit_summary["objective_before"]:
        contract_failures.append("weighted pointwise-Q objective did not improve")
    development = None
    if contract_failures:
        classification = "HARNESS_MISMATCH"
    elif cosine >= 0.995:
        classification = "POINTWISE_OUTPUT_DELTA_REDUNDANT_WITH_F74"
    else:
        development_rows = [_development_row(compiled, native, gen1, candidate, root) for root in _development_roots()]
        development = _development_summary(development_rows)
        contract_failures.extend(
            f"root-{row['root_index']}: repeated fresh arm differed"
            for row in development_rows if not row["deterministic"]
        )
        if not development["root_window_pruning_all_true"]:
            contract_failures.append("development root pruning telemetry was not true")
        if contract_failures:
            classification = "HARNESS_MISMATCH"
        elif development["decision_changes"] >= 1:
            classification = "POINTWISE_OUTPUT_DELTA_DEPLOYMENT_VISIBLE"
        else:
            classification = "POINTWISE_OUTPUT_DELTA_NOT_DEPLOYMENT_VISIBLE"
    result = {
        "schema": "generic-chess-f76-parent-retained-pointwise-q-output-delta-v1",
        "work_order": WORK_ORDER,
        "baseline_sha": PARENT_SHA,
        "classification": classification,
        "gen1_checkpoint_id": gen1.checkpoint_id,
        "candidate_checkpoint_id": candidate.checkpoint_id,
        "fit_data_identity": {"stage_sha256": F62_STAGE_SHA, "records_sha256": F62_RECORDS_SHA},
        "fit_root_count": len(fit_roots),
        "fit": {
            "objective": "weighted_pointwise_q",
            "regularization": REGULARIZATION,
            "target_scale": parent_model.target_scale,
            "summary": fit_summary,
            "objective_before": fit_summary["objective_before"],
            "objective_after_raw_delta": fit_summary["objective_after"],
            "objective_after_alpha_star": final_objective,
        },
        "correction": {
            "raw_delta": delta.tolist(),
            "raw_delta_norm": float(np.linalg.norm(delta)),
            "f74_delta_cosine": cosine,
            "alpha_high_confidence_boundary": high_boundary,
            "alpha_residual_cap_boundary": residual_boundary,
            "alpha_star": alpha_star,
            "high_confidence": high_summary,
            "residual_cap": residual_summary,
            "candidate": candidate_summary,
            "descriptor_path": str(CANDIDATE_PATH.relative_to(ROOT)),
        },
        "retention": {
            "fit_root_count_checked": len(fit_roots),
            "upper_quartile_roots_checked": len(high_roots),
            "high_confidence_top_action_retained": not retention_failures,
            "parent_max_abs_residual": parent_max,
            "candidate_max_abs_residual": candidate_max,
            "allowed_max_abs_residual": 2.0 * parent_max,
        },
        "native_python_parity": parity,
        "development": development,
        "contract_failures": contract_failures,
        "code_provenance": _provenance(),
    }
    _atomic_json(RESULT_PATH, result)
    return result


def main() -> None:
    result = run()
    print(json.dumps({
        "classification": result["classification"],
        "candidate_checkpoint_id": result["candidate_checkpoint_id"],
        "fit_root_count": result["fit_root_count"],
        "raw_delta_norm": result["correction"]["raw_delta_norm"],
        "f74_delta_cosine": result["correction"]["f74_delta_cosine"],
        "alpha_star": result["correction"]["alpha_star"],
        "objective_before": result["fit"]["objective_before"],
        "objective_after_alpha_star": result["fit"]["objective_after_alpha_star"],
        "decision_changes": None if result["development"] is None else result["development"]["decision_changes"],
        "contract_failures": result["contract_failures"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
