"""F74 parent-retained, output-layer-only correction probe.

The script is intentionally experiment-local.  It reads only the persisted
F62 fit roots and the already selected F62 development roots, freezes the
Gen1 representation, fits one deterministic output-weight direction, applies
the pre-registered fit-only trust region, and probes the existing product
search binding.
"""

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
from generic_chess.native.semantic import evaluate as native_evaluate  # noqa: E402
from generic_chess.native.semantic import dynamic_features as native_dynamic_features  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_r2_fresh_strength as f61r2  # noqa: E402


WORK_ORDER = "GENERICCHESS-F74-PARENT-RETAINED-OUTPUT-DELTA-PROBE"
PARENT_SHA = "ecf4e6e0acca399dba8f4cea0607d5cfe9cef89c"
LABEL = "B_CANONICAL_STANDARD_SHOGI"
GEN1_ID = "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
GEN1_CANDIDATE = "F60_D0_PAIRWISE_SEED_59012"
F62_STAGE_SHA = "e7a93423d6058c68fe7ccbc61302584ca1e8869aa828586254f72f4dfdac2c70"
F62_RECORDS_SHA = "b7a6dc134bf1232fa90d9734ad070c184ecd09f691bc92958686093181d3ff61"
F62_OUT = ROOT / ".generic_chess_flow" / "f62-learned-champion-repeatability"
MODEL_PARAMS = ROOT / "docs" / "architecture" / "GENERICCHESS_F61_MODEL_PARAMS.json"
OUT = ROOT / ".generic_chess_flow" / "f74-parent-retained-output-delta-probe"
RESULT_PATH = OUT / "f74_results.json"
FIT_ROOT_COUNT = 48
DEVELOPMENT_ROOT_COUNT = 20
FIT_ROOT_INDICES = tuple(
    index for index in range(96) if index % 32 < 16
)
DEVELOPMENT_ROOT_INDICES = tuple(
    index for index in range(96) if 16 <= index % 32 < 24
)
NODES = 2_048
MAX_DEPTH = 12
TT_MEGABYTES = 8
FIT_ITERATIONS = 80
FIT_TOLERANCE = 1e-11


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _action_key(payload: dict | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _load_gen1(compiled):
    data = json.loads(MODEL_PARAMS.read_text(encoding="utf-8"))
    row = next(
        item for item in data["corrected_candidates"]
        if item["candidate_id"] == GEN1_CANDIDATE
    )
    gen1 = f61r2._candidate_checkpoint(f59._parent(LABEL), row)
    if (
        row["corrected_checkpoint_id"] != GEN1_ID
        or row["checkpoint_id"] != GEN1_ID
        or gen1.checkpoint_id != GEN1_ID
    ):
        raise RuntimeError("F74 Gen1 durable champion identity mismatch")
    gen1.validate_ruleset(compiled)
    return gen1


def _load_fit_roots() -> list[dict]:
    roots = []
    for index in FIT_ROOT_INDICES:
        path = F62_OUT / "progress" / "spectrum" / f"root-{index:03d}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        record = payload["identity"]["record"]
        if record.get("source_split") != "fit":
            raise RuntimeError("F74 fit corpus crossed a split boundary")
        metadata = payload["root_metadata"]
        roots.append({
            "root_index": index,
            "record": record,
            "metadata": metadata,
            "source_identity_sha256": payload["identity_sha256"],
        })
    if len(roots) != FIT_ROOT_COUNT:
        raise RuntimeError("F74 fit corpus size differs from the frozen F62 contract")
    return roots


def _trusted_fit_roots(roots: list[dict]) -> list[dict]:
    trusted = []
    for root in roots:
        metadata = root["metadata"]
        deep = metadata["root_80k"]["action_key"]
        if (
            metadata["root_40k"]["action_key"] == deep
            and metadata["spectrum_top_10k_action_key"]
            == metadata["spectrum_top_20k_action_key"]
            and metadata["spectrum_top_10k_action_key"] == deep
            and not metadata["root_80k_mate_band"]
            and not metadata["retained_q20_any_mate_band"]
        ):
            trusted.append(root)
    return trusted


def _load_development_roots() -> list[dict]:
    roots = []
    for index in DEVELOPMENT_ROOT_INDICES:
        path = F62_OUT / "progress" / "spectrum" / f"root-{index:03d}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        record = payload["identity"]["record"]
        if record.get("source_split") != "development":
            raise RuntimeError("F74 development corpus crossed a split boundary")
        metadata = payload["root_metadata"]
        if metadata["root_40k"]["action_key"] != metadata["root_80k"]["action_key"]:
            continue
        roots.append({
            "root_index": index,
            "record": record,
            "metadata": metadata,
            "source_identity_sha256": payload["identity_sha256"],
        })
    if len(roots) != DEVELOPMENT_ROOT_COUNT:
        raise RuntimeError("F74 development root count differs from the frozen contract")
    return roots


def _hidden_activations(model: CompactNonlinearResidual, features: np.ndarray) -> np.ndarray:
    values = np.asarray(features, dtype=np.float64)
    normalized = (
        values - np.asarray(model.input_mean, dtype=np.float64)
    ) / np.asarray(model.input_scale, dtype=np.float64)
    return np.tanh(
        normalized @ np.asarray(model.hidden_weights, dtype=np.float64).T
        + np.asarray(model.hidden_bias, dtype=np.float64)
    )


def _root_rows(root: dict, model: CompactNonlinearResidual) -> dict:
    action_rows = root["metadata"]["action_rows"]
    features = np.asarray([row["features"] for row in action_rows], dtype=np.float64)
    hidden = _hidden_activations(model, features)
    base = np.asarray([row["base_q"] for row in action_rows], dtype=np.float64)
    residual = model.predict(features)
    total = base + residual
    keys = [row["action_key"] for row in action_rows]
    consensus_key = root["metadata"]["root_80k"]["action_key"]
    try:
        consensus_index = keys.index(consensus_key)
    except ValueError as exc:
        raise RuntimeError("F74 consensus action is absent from retained fit rows") from exc
    return {
        "root_index": root["root_index"],
        "keys": keys,
        "features": features,
        "hidden": hidden,
        "base": base,
        "parent_residual": residual,
        "parent_total": total,
        "consensus_index": consensus_index,
        "metadata": root["metadata"],
    }


def _pairwise_rows(root_rows: list[dict]) -> list[list[tuple[np.ndarray, float]]]:
    result = []
    for root in root_rows:
        target = root["consensus_index"]
        pairs = []
        for index in range(len(root["keys"])):
            if index == target:
                continue
            direction = root["hidden"][target] - root["hidden"][index]
            parent_margin = (
                root["parent_total"][target] - root["parent_total"][index]
            ) / 1.0
            pairs.append((direction, float(parent_margin)))
        if not pairs:
            raise RuntimeError("F74 trusted root has no retained alternative action")
        result.append(pairs)
    return result


def _stable_softplus(values: np.ndarray) -> np.ndarray:
    return np.logaddexp(0.0, np.asarray(values, dtype=np.float64))


def _pairwise_objective(
    delta: np.ndarray,
    pairwise: list[list[tuple[np.ndarray, float]]],
    target_scale: float,
    regularization: float,
) -> float:
    losses = []
    for root in pairwise:
        margins = np.asarray(
            [margin / target_scale + direction @ delta for direction, margin in root],
            dtype=np.float64,
        )
        losses.append(float(np.mean(_stable_softplus(-margins))))
    return float(np.mean(losses) + 0.5 * regularization * (delta @ delta))


def _fit_direction(
    pairwise: list[list[tuple[np.ndarray, float]]],
    *,
    width: int,
    target_scale: float,
    regularization: float,
) -> tuple[np.ndarray, dict]:
    """Fit one deterministic convex output-layer direction with Newton steps."""
    delta = np.zeros(width, dtype=np.float64)
    initial = _pairwise_objective(delta, pairwise, target_scale, regularization)
    objective = initial
    accepted_steps = 0
    for iteration in range(1, FIT_ITERATIONS + 1):
        gradient = regularization * delta
        hessian = regularization * np.eye(width, dtype=np.float64)
        root_weight = 1.0 / len(pairwise)
        for root in pairwise:
            pair_weight = root_weight / len(root)
            for direction, margin in root:
                normalized = margin / target_scale + direction @ delta
                probability = 1.0 / (1.0 + math.exp(float(np.clip(normalized, -60.0, 60.0))))
                gradient -= pair_weight * probability * direction
                hessian += pair_weight * probability * (1.0 - probability) * np.outer(
                    direction, direction
                )
        step = np.linalg.solve(hessian, gradient)
        if float(np.linalg.norm(step)) <= FIT_TOLERANCE:
            break
        trial_scale = 1.0
        improved = False
        for _ in range(32):
            candidate = delta - trial_scale * step
            candidate_objective = _pairwise_objective(
                candidate, pairwise, target_scale, regularization
            )
            if candidate_objective < objective - 1e-14:
                delta = candidate
                objective = candidate_objective
                accepted_steps += 1
                improved = True
                break
            trial_scale *= 0.5
        if not improved:
            break
    return delta, {
        "initial_objective": initial,
        "fitted_objective": objective,
        "iterations": iteration,
        "accepted_steps": accepted_steps,
        "delta_norm": float(np.linalg.norm(delta)),
    }


def _parent_scores(root: dict) -> np.ndarray:
    return np.asarray(root["parent_total"], dtype=np.float64)


def _top_index(scores: np.ndarray, keys: list[str]) -> int:
    return min(range(len(scores)), key=lambda index: (-float(scores[index]), keys[index]))


def _high_confidence_boundary(
    roots: list[dict], delta: np.ndarray, target_scale: float
) -> tuple[float, dict]:
    margins = []
    for root in roots:
        scores = _parent_scores(root)
        order = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), root["keys"][i]))
        margins.append(float(scores[order[0]] - scores[order[1]]))
    threshold = float(np.percentile(np.asarray(margins), 75.0))
    high = [root for root, margin in zip(roots, margins) if margin >= threshold]
    boundaries = []
    for root in high:
        scores = _parent_scores(root)
        top = _top_index(scores, root["keys"])
        for index in range(len(scores)):
            if index == top:
                continue
            margin = (scores[top] - scores[index]) / target_scale
            slope = float((root["hidden"][top] - root["hidden"][index]) @ delta)
            if slope < 0.0 and margin > 0.0:
                boundaries.append({
                    "root_index": root["root_index"],
                    "top_action_key": root["keys"][top],
                    "alternative_action_key": root["keys"][index],
                    "alpha": -margin / slope,
                })
    boundary = min((item["alpha"] for item in boundaries), default=float("inf"))
    return boundary, {
        "threshold": threshold,
        "count": len(high),
        "finite_boundary_count": len(boundaries),
        "first_boundary": min(boundaries, key=lambda item: item["alpha"])
        if boundaries else None,
    }


def _residual_cap(
    roots: list[dict], delta: np.ndarray, target_scale: float
) -> tuple[float, dict]:
    parent_max = max(
        float(np.max(np.abs(root["parent_residual"]))) for root in roots
    )
    cap = 2.0 * parent_max
    boundaries = []
    for root in roots:
        change = target_scale * (root["hidden"] @ delta)
        for index, slope in enumerate(change):
            slope = float(slope)
            if slope > 0.0:
                boundary = (cap - float(root["parent_residual"][index])) / slope
            elif slope < 0.0:
                boundary = (cap + float(root["parent_residual"][index])) / -slope
            else:
                continue
            if boundary > 0.0:
                boundaries.append({
                    "root_index": root["root_index"],
                    "action_key": root["keys"][index],
                    "alpha": boundary,
                })
    value = min((item["alpha"] for item in boundaries), default=float("inf"))
    return value, {
        "parent_max_abs": parent_max,
        "allowed_max_abs": cap,
        "finite_boundary_count": len(boundaries),
        "first_boundary": min(boundaries, key=lambda item: item["alpha"])
        if boundaries else None,
    }


def _make_candidate(gen1, model: CompactNonlinearResidual, alpha: float, delta: np.ndarray):
    fitted_weights = np.asarray(model.output_weights, dtype=np.float64) + delta
    candidate_model = replace(
        model,
        output_weights=tuple((np.asarray(model.output_weights) + alpha * delta).tolist()),
        output_bias=model.output_bias,
    )
    training_identity = {
        "work_order": WORK_ORDER,
        "parent_checkpoint_id": gen1.checkpoint_id,
        "fit_method": "deterministic_regularized_pairwise_output_delta",
        "fit_regularization": model.regularization,
        "raw_delta": delta.tolist(),
        "alpha": alpha,
        "fitted_direction_norm": float(np.linalg.norm(delta)),
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
        "training_identity": training_identity,
        "model_sha256": stable_sha256(candidate_model.to_dict()),
        "raw_output_weight_norm": float(np.linalg.norm(fitted_weights - np.asarray(model.output_weights))),
    }


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
    if candidate.compact_nonlinear.get("output_bias") != gen1.compact_nonlinear.get("output_bias"):
        failures.append("checkpoint output bias changed")
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
            # Gen1 is rooted in successor_root_q.  Native evaluates the
            # successor from the opponent's leaf perspective, so this
            # residual contribution has one fixed negative sign.
            expected = -(
                int(round(python_candidate * candidate.semantic_native_scale))
                - int(round(python_parent * gen1.semantic_native_scale))
            )
            actual = int(candidate_score - parent_score)
            if actual != expected:
                failures.append(f"root-{root['root_index']}: Native/Python residual mismatch")
            rows.append({
                "root_index": root["root_index"],
                "action_key": action_row["action_key"],
                "actual_native_delta": actual,
                "expected_native_delta": expected,
                "python_parent_residual": python_parent,
                "python_candidate_residual": python_candidate,
                "dynamic_dimension": len(dynamic),
            })
    return {"rows": rows, "all_exact": not failures, "failures": failures}


def _engine_payload(result) -> dict:
    return {
        "action_key": None if result.action is None else _action_key(f59.action_to_dict(result.action)),
        "score": int(result.score),
        "completed_depth": int(result.completed_depth),
        "nodes": int(result.nodes),
        "beta_cutoffs": int(result.beta_cutoffs),
        "tt_probes": int(result.tt_probes),
        "tt_hits": int(result.tt_hits),
        "tt_cutoffs": int(result.tt_cutoffs),
        "termination_mode": str(result.termination_reason),
    }


def _search_arm(compiled, native, checkpoint, root: dict) -> dict:
    session = f59._session(compiled, root["record"])
    result = SemanticSearchEngine(
        compiled, native, checkpoint=checkpoint, tt_megabytes=TT_MEGABYTES
    ).search(
        session,
        SearchLimits(max_depth=MAX_DEPTH, max_nodes=NODES, quiescence_max_depth=0),
        root_window_pruning=True,
    )
    return _engine_payload(result)


def _deployment_row(compiled, native, gen1, candidate, candidate_model, root):
    parent = _search_arm(compiled, native, gen1, root)
    parent_repeat = _search_arm(compiled, native, gen1, root)
    child = _search_arm(compiled, native, candidate, root)
    child_repeat = _search_arm(compiled, native, candidate, root)
    deep = root["metadata"]["root_80k"]["action_key"]
    parent_static = _root_rows(root, CompactNonlinearResidual.from_dict(gen1.compact_nonlinear))
    child_static = _root_rows(root, candidate_model)
    parent_static_key = parent_static["keys"][_top_index(parent_static["parent_total"], parent_static["keys"])]
    child_static_key = child_static["keys"][_top_index(child_static["parent_total"], child_static["keys"])]
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
    child_residual = child_static["parent_residual"]
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
        "parent_static_top_action_key": parent_static_key,
        "candidate_static_top_action_key": child_static_key,
        "candidate_residual_delta_scale": float(np.max(np.abs(child_residual - parent_static["parent_residual"]))),
    }


def _provenance() -> dict:
    return {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in (
            "scripts/f74_parent_retained_output_delta_probe.py",
            "scripts/f59_action_spectrum_diagnosis.py",
            "scripts/f61_r2_fresh_strength.py",
            "scripts/f71_causal_root_hint_probe.py",
            "generic_chess/native/semantic_engine.py",
            "generic_chess/native/semantic.py",
            "docs/architecture/GENERICCHESS_F61_MODEL_PARAMS.json",
        )
    }


def run() -> dict:
    if not native_available():
        raise RuntimeError("F74 requires the native extension")
    compiled, native, _profile = f59._ruleset(LABEL)
    gen1 = _load_gen1(compiled)
    parent_model = CompactNonlinearResidual.from_dict(gen1.compact_nonlinear)
    fit_roots = _load_fit_roots()
    trusted_roots = _trusted_fit_roots(fit_roots)
    development_roots = _load_development_roots()
    if not trusted_roots:
        raise RuntimeError("F74 found no trusted fit roots")
    fit_data = [_root_rows(root, parent_model) for root in trusted_roots]
    pairwise = _pairwise_rows(fit_data)
    delta, fit_summary = _fit_direction(
        pairwise,
        width=parent_model.width,
        target_scale=parent_model.target_scale,
        regularization=parent_model.regularization,
    )
    high_boundary, high_summary = _high_confidence_boundary(
        fit_data, delta, parent_model.target_scale
    )
    residual_boundary, residual_summary = _residual_cap(
        fit_data, delta, parent_model.target_scale
    )
    alpha_star = min(1.0, 0.5 * high_boundary, residual_boundary)
    candidate_model, candidate, candidate_summary = _make_candidate(
        gen1, parent_model, alpha_star, delta
    )
    final_fit_data = [
        _root_rows(root, candidate_model) for root in trusted_roots
    ]
    final_objective = _pairwise_objective(
        alpha_star * delta, pairwise,
        parent_model.target_scale, parent_model.regularization,
    )
    representation_failures = _representation_guard(
        compiled, gen1, candidate, parent_model, candidate_model
    )
    parity = _native_parity(
        compiled, native, gen1, candidate, candidate_model, trusted_roots
    )
    contract_failures = list(representation_failures) + list(parity["failures"])
    if not alpha_star > 0.0:
        contract_failures.append("trust-region alpha is not positive")
    if not final_objective < fit_summary["initial_objective"]:
        contract_failures.append("final fit pairwise objective did not improve")
    deployment = [
        _deployment_row(compiled, native, gen1, candidate, candidate_model, root)
        for root in development_roots
    ]
    contract_failures.extend(
        f"root-{row['root_index']}: repeated fresh arm differed"
        for row in deployment if not row["deterministic"]
    )
    changed = [row for row in deployment if row["decision_changed"]]
    toward = sum(row["direction"] == "toward-deep" for row in deployment)
    away = sum(row["direction"] == "away-from-deep" for row in deployment)
    lateral = sum(row["direction"] == "lateral" for row in deployment)
    if contract_failures:
        classification = "HARNESS_MISMATCH"
    elif not final_objective < fit_summary["initial_objective"]:
        classification = "PARENT_RETAINED_OUTPUT_DELTA_UNSAFE"
    elif len(changed) >= 1:
        classification = "PARENT_RETAINED_OUTPUT_DELTA_DEPLOYMENT_VISIBLE"
    else:
        classification = "PARENT_RETAINED_OUTPUT_DELTA_NOT_DEPLOYMENT_VISIBLE"
    result = {
        "schema": "generic-chess-f74-parent-retained-output-delta-probe-v1",
        "work_order": WORK_ORDER,
        "baseline_sha": PARENT_SHA,
        "classification": classification,
        "gen1_checkpoint_id": gen1.checkpoint_id,
        "candidate_checkpoint_id": candidate.checkpoint_id,
        "trusted_fit_root_count": len(trusted_roots),
        "fit_root_count": len(fit_roots),
        "fit_data_identity": {"stage_sha256": F62_STAGE_SHA, "records_sha256": F62_RECORDS_SHA},
        "fit": {
            "objective": "per_root_pairwise_logistic",
            "regularization": parent_model.regularization,
            "target_scale": parent_model.target_scale,
            "action_row_count": sum(len(root["keys"]) for root in fit_data),
            "pair_count": sum(len(root) for root in pairwise),
            "summary": fit_summary,
            "objective_before": fit_summary["initial_objective"],
            "objective_after_alpha_star": final_objective,
        },
        "correction": {
            "raw_delta": delta.tolist(),
            "raw_delta_norm": float(np.linalg.norm(delta)),
            "raw_delta_max_abs": float(np.max(np.abs(delta))),
            "alpha_high_confidence_boundary": high_boundary,
            "alpha_residual_cap": residual_boundary,
            "alpha_star": alpha_star,
            "high_confidence": high_summary,
            "residual_cap": residual_summary,
            "candidate": candidate_summary,
        },
        "residuals": {
            "fit_parent_max_abs": residual_summary["parent_max_abs"],
            "fit_candidate_max_abs": max(
                float(np.max(np.abs(root["parent_residual"]))) for root in final_fit_data
            ),
            "fit_allowed_max_abs": residual_summary["allowed_max_abs"],
        },
        "native_python_parity": parity,
        "development": {
            "root_count": len(deployment),
            "nodes": NODES,
            "max_depth": MAX_DEPTH,
            "tt_megabytes": TT_MEGABYTES,
            "root_window_pruning": True,
            "fresh_engine_per_arm": True,
            "decision_changes": len(changed),
            "toward_deep": toward,
            "away_from_deep": away,
            "lateral": lateral,
            "parent_deep_agreement": sum(row["parent_deep_agreement"] for row in deployment),
            "child_deep_agreement": sum(row["child_deep_agreement"] for row in deployment),
            "completed_depth_distribution_parent": {
                str(depth): sum(row["parent"]["completed_depth"] == depth for row in deployment)
                for depth in sorted({row["parent"]["completed_depth"] for row in deployment})
            },
            "completed_depth_distribution_child": {
                str(depth): sum(row["child"]["completed_depth"] == depth for row in deployment)
                for depth in sorted({row["child"]["completed_depth"] for row in deployment})
            },
            "rows": deployment,
        },
        "contract_failures": contract_failures,
        "code_provenance": _provenance(),
    }
    _atomic_json(RESULT_PATH, result)
    return result


def main() -> None:
    result = run()
    print(json.dumps({
        "classification": result["classification"],
        "trusted_fit_root_count": result["trusted_fit_root_count"],
        "alpha_star": result["correction"]["alpha_star"],
        "fit_objective_before": result["fit"]["objective_before"],
        "fit_objective_after_alpha_star": result["fit"]["objective_after_alpha_star"],
        "decision_changes": result["development"]["decision_changes"],
        "toward_deep": result["development"]["toward_deep"],
        "away_from_deep": result["development"]["away_from_deep"],
        "lateral": result["development"]["lateral"],
        "contract_failures": result["contract_failures"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
