"""F133: generic resource-transition action semantics for the frozen F131 model.

The benchmark adds only authoritative mover-relative hand/resource deltas to the
frozen F131 action representation.  Resource classes are derived from compiled
rule structure and never expose type identifiers to the learner.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import FrozenBasis, _json_sha, _scalar_metrics
    from scripts.f131_shogi_action_conditioned_t1_factorization import (
        _action_ranking,
        _fit,
        _predict,
    )
    from scripts.f132_shogi_action_residual_causal_decomposition import (
        _build_surface,
        _family,
        _write_progress,
    )
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import FrozenBasis, _json_sha, _scalar_metrics
    from f131_shogi_action_conditioned_t1_factorization import _action_ranking, _fit, _predict
    from f132_shogi_action_residual_causal_decomposition import _build_surface, _family, _write_progress
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset

from generic_chess.core.actions import action_is_drop
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import ruleset_from_dict, ruleset_to_dict


FAMILY = "standard_shogi"
BASELINE = "a561777bb9d1b2b4a071a8449e1928fbe9f24cb5"
F131_TOP1 = 0.3937007874015748
F131_PAIRWISE = 0.6961452971418344
F131_NREGRET = 0.14638599860007367
F131_POOLED_RMSE = 2152.230646928496
F129_BASE_HOLDOUT_RMSE = 8476.16832054588
F129_STATIC_HOLDOUT_RMSE = 6088.17472319246
RESOURCE_SCHEMA = "RESOURCE_TRANSITION_V1"


def _stable_payload_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _matrix(value, board_size: int) -> tuple:
    if value is None:
        return ()
    result = []
    for row in value:
        row = tuple(row)
        if not row or all(isinstance(cell, (bool, np.bool_)) for cell in row):
            result.append(tuple(bool(cell) for cell in row))
            continue
        if all(isinstance(cell, tuple) and len(cell) == 2 and hasattr(cell[0], "file") and hasattr(cell[1], "file") for cell in row):
            result.append(tuple(sorted(((int(cell[0].file), int(cell[0].rank)), (int(cell[1].file), int(cell[1].rank))) for cell in row)))
            continue
        occupied = set()
        for cell in row:
            file = getattr(cell, "file", cell[0] if isinstance(cell, (tuple, list)) else None)
            rank = getattr(cell, "rank", cell[1] if isinstance(cell, (tuple, list)) else None)
            if file is not None and rank is not None:
                occupied.add(int(rank) * board_size + int(file))
        result.append(tuple(index in occupied for index in range(board_size * board_size)))
    return tuple(result)


def _mobility(value) -> tuple:
    if value is None:
        return ()
    return tuple(tuple((int(target.file), int(target.rank)) for target in destinations) for destinations in value)


def _type_refs_from_capture(compiled) -> tuple[set[str], bool]:
    explicit: set[str] = set()
    capture_any = False
    for pattern in compiled.ir.patterns:
        for effect in pattern.effects:
            if effect.kind != "remove" or effect.disposition != "capture_to_hand":
                continue
            ref = effect.piece_type_ref
            if ref is not None and getattr(ref, "kind", None) == "explicit":
                explicit.add(ref.type_id)
            else:
                guarded = [getattr(guard.type_ref, "type_id", None) for guard in pattern.guards if getattr(guard.type_ref, "kind", None) == "explicit"]
                if guarded:
                    explicit.update(type_id for type_id in guarded if type_id is not None)
                else:
                    capture_any = True
    return explicit, capture_any


def _resource_type_ids(compiled) -> tuple[str, ...]:
    metadata = compiled.support.type_metadata
    promoted = {target for value in metadata.values() for target in value.promotion_target_ids}
    base_types = {tid for tid, value in metadata.items() if not value.is_anchor and tid not in promoted}
    explicit, capture_any = _type_refs_from_capture(compiled)
    droppable = {tid for tid, masks in compiled.support.drop_allowed.items() if any(any(mask) for mask in masks)}
    capable = droppable | explicit
    if capture_any:
        capable |= base_types
    return tuple(sorted(base_types & capable))


def _geometry_signature(compiled, type_id: str) -> tuple:
    result = []
    for geometry in compiled.ir.geometry.values():
        source = geometry.atom_source
        if not source or source[0] != type_id:
            continue
        result.append((
            str(geometry.kind), bool(geometry.owner_relative),
            tuple(geometry.offset) if geometry.offset is not None else None,
            tuple(geometry.direction) if geometry.direction is not None else None,
            geometry.min_steps, geometry.max_steps, tuple(source[1:]),
        ))
    return tuple(sorted(result, key=repr))


def _resource_signature(compiled, type_id: str) -> dict:
    support = compiled.support
    metadata = support.type_metadata[type_id]
    payload = {
        "movement": _geometry_signature(compiled, type_id),
        "empty_board_mobility": tuple(_mobility(support.empty_mobility.get(type_id, ({}, {}))[owner]) for owner in (0, 1)),
        "drop_allowed": _matrix(support.drop_allowed.get(type_id, ((), ())), support.board_size),
        "promotion_allowed": _matrix(support.promotion_allowed.get(type_id, ((), ())), support.board_size),
        "promotion_forced": _matrix(support.promotion_forced.get(type_id, ((), ())), support.board_size),
        "is_promotable": bool(metadata.is_promotable),
        "is_anchor": bool(metadata.is_anchor),
    }
    return payload


def _resource_classes(compiled) -> dict:
    groups: dict[str, list[str]] = {}
    payloads: dict[str, dict] = {}
    for type_id in _resource_type_ids(compiled):
        payload = _resource_signature(compiled, type_id)
        digest = _stable_payload_hash(payload)
        groups.setdefault(digest, []).append(type_id)
        payloads[digest] = payload
    ordered = []
    type_to_class = {}
    for index, digest in enumerate(sorted(groups)):
        members = tuple(sorted(groups[digest]))
        class_id = f"resource_{index:02d}"
        ordered.append({"class_id": class_id, "signature_sha256": digest, "members": members, "payload": payloads[digest]})
        for member in members:
            type_to_class[member] = index
    return {"schema": RESOURCE_SCHEMA, "classes": ordered, "type_to_class": type_to_class}


def _resource_transition(root_position, child_position, resource_classes: dict, mover: int | None = None) -> np.ndarray:
    mover = root_position.side_to_move if mover is None else int(mover)
    opponent = 1 - mover
    values = []
    for item in resource_classes["classes"]:
        members = item["members"]
        root_mover = sum(root_position.hands[mover].count(type_id) for type_id in members)
        child_mover = sum(child_position.hands[mover].count(type_id) for type_id in members)
        root_opponent = sum(root_position.hands[opponent].count(type_id) for type_id in members)
        child_opponent = sum(child_position.hands[opponent].count(type_id) for type_id in members)
        values.append(float((child_mover - root_mover) - (child_opponent - root_opponent)))
    return np.asarray(values, dtype=np.float64)


def _rename_ruleset(ruleset):
    source = ruleset_to_dict(ruleset)
    type_ids = [item["type_id"] for item in source["piece_types"]]
    mapping = {old: f"opaque_{index:02d}" for index, old in enumerate(type_ids)}

    def remap(value):
        if isinstance(value, dict):
            return {mapping.get(key, key): remap(value_value) for key, value_value in value.items()}
        if isinstance(value, list):
            return [remap(item) for item in value]
        if isinstance(value, str):
            return mapping.get(value, value)
        return value

    remapped = remap(source)
    return ruleset_from_dict(remapped)


def _microtests() -> dict:
    reports = {}
    standard_rules = build_standard_shogi_ruleset()
    standard = compile_semantic_ruleset(standard_rules)
    renamed = compile_semantic_ruleset(_rename_ruleset(standard_rules))
    standard_classes = _resource_classes(standard)
    renamed_classes = _resource_classes(renamed)
    reports["standard_shogi"] = {
        "resource_class_count": len(standard_classes["classes"]),
        "signature_sequence": [item["signature_sha256"] for item in standard_classes["classes"]],
        "type_rename_signature_sequence_equal": [item["signature_sha256"] for item in standard_classes["classes"]] == [item["signature_sha256"] for item in renamed_classes["classes"]],
        "finite": all(np.all(np.isfinite(_resource_transition(initial_state(standard).position, initial_state(standard).position, standard_classes))) for _ in (0,)),
    }

    from generic_chess.rules.western_chess import build_western_chess_ruleset
    western = compile_semantic_ruleset(build_western_chess_ruleset())
    western_classes = _resource_classes(western)
    western_initial = initial_state(western).position
    reports["western_chess"] = {
        "resource_class_count": len(western_classes["classes"]),
        "ordinary_capture_resource_width_zero": len(western_classes["classes"]) == 0,
        "zero_transition": bool(np.allclose(_resource_transition(western_initial, western_initial, western_classes), 0.0)),
    }

    mixed_report = {"available": False}
    try:
        try:
            from tests.test_f24c_mixed_mechanic_certification import A0, A1, H0, _mixed_ruleset, _position
        except ModuleNotFoundError as error:
            if error.name != "tests":
                raise
            fixture_path = Path(__file__).resolve().parents[1] / "tests" / "test_f24c_mixed_mechanic_certification.py"
            spec = importlib.util.spec_from_file_location("f133_mixed_fixture", fixture_path)
            if spec is None or spec.loader is None:
                raise RuntimeError("F133 mixed fixture loader unavailable")
            fixture = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = fixture
            spec.loader.exec_module(fixture)
            A0, A1, H0 = fixture.A0, fixture.A1, fixture.H0
            _mixed_ruleset, _position = fixture._mixed_ruleset, fixture._position
        from generic_chess.core.pieces import Piece

        mixed = compile_semantic_ruleset(_mixed_ruleset())
        classes = _resource_classes(mixed)
        anchors = [(0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))]
        position = _position(mixed, [(1, 1, Piece(0, A0, A0)), (2, 1, Piece(1, A0, A0)), *anchors], hands=([(A0, 1)], ()))
        engine = semantic_engine_for(mixed)
        actions = engine.legal_actions(position)
        capture = next(action for action in actions if "capture_A0_A0" in action.pattern_id)
        drop = next(action for action in actions if action.source is None and action.actor_type == A0)
        promotion_position = _position(mixed, [(4, 4, Piece(0, A0, A0)), *anchors], hands=([(A0, 1)], ()))
        promotion_actions = engine.legal_actions(promotion_position)
        promotion = next(action for action in promotion_actions if action.promotion_target_id == A1)
        promoted_capture_position = _position(mixed, [(1, 1, Piece(0, A0, A0)), (2, 1, Piece(1, A0, A1, promoted=True)), *anchors], hands=([(A0, 1)], ()))
        promoted_capture = next(action for action in engine.legal_actions(promoted_capture_position) if "capture_A0_A0" in action.pattern_id)
        capture_delta = _resource_transition(position, engine.apply(position, capture), classes)
        drop_delta = _resource_transition(position, engine.apply(position, drop), classes)
        promotion_delta = _resource_transition(promotion_position, engine.apply(promotion_position, promotion), classes)
        promoted_capture_delta = _resource_transition(promoted_capture_position, engine.apply(promoted_capture_position, promoted_capture), classes)
        mixed_report = {
            "available": True,
            "resource_class_count": len(classes["classes"]),
            "capture_to_hand_positive": bool(np.max(capture_delta) == 1.0),
            "drop_from_hand_negative": bool(np.min(drop_delta) == -1.0),
            "promoted_capture_maps_to_base_resource": bool(np.max(promoted_capture_delta) == 1.0),
            "promotion_non_resource_changing": bool(np.allclose(promotion_delta, 0.0)),
            "finite": bool(np.all(np.isfinite(np.concatenate((capture_delta, drop_delta, promotion_delta, promoted_capture_delta))))),
        }
    except Exception as error:
        mixed_report = {"available": False, "error": type(error).__name__ + ": " + str(error)}
    reports["mixed_mechanics"] = mixed_report
    reports["pass"] = bool(
        reports["standard_shogi"]["resource_class_count"] > 0
        and reports["standard_shogi"]["type_rename_signature_sequence_equal"]
        and reports["standard_shogi"]["finite"]
        and reports["western_chess"]["ordinary_capture_resource_width_zero"]
        and reports["western_chess"]["zero_transition"]
        and mixed_report.get("available")
        and mixed_report.get("capture_to_hand_positive")
        and mixed_report.get("drop_from_hand_negative")
        and mixed_report.get("promoted_capture_maps_to_base_resource")
        and mixed_report.get("finite")
    )
    return reports


def _rows_with_features(rows: list[dict], feature_values: np.ndarray) -> list[dict]:
    result = []
    for index, row in enumerate(rows):
        copied = dict(row)
        copied["features"] = feature_values[index].tolist()
        result.append(copied)
    return result


def _predictions(fit: dict, rows: list[dict]) -> np.ndarray:
    return np.concatenate([_predict(fit["matched"], fit["pack"], split) for split in ("train", "dev", "holdout")])


def _root_groups(rows: list[dict], split: str) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        if row["split"] == split:
            groups.setdefault(row["root_identity"], []).append(index)
    return groups


def _t1_predictions(rows: list[dict], predictions: np.ndarray, split: str) -> tuple[np.ndarray, np.ndarray]:
    groups = _root_groups(rows, split)
    predicted = np.asarray([rows[group[0]]["v_star"] + max(float(predictions[index]) for index in group) for group in groups.values()], dtype=np.float64)
    teacher = np.asarray([max(float(rows[index]["q"]) for index in group) for group in groups.values()], dtype=np.float64)
    return teacher, predicted


def _action_and_t1_report(rows: list[dict], predictions: np.ndarray, holdout_t1_std: float) -> dict:
    action = _action_ranking(rows, predictions, "holdout", holdout_t1_std)
    teacher, predicted = _t1_predictions(rows, predictions, "holdout")
    scalar = _scalar_metrics(teacher, predicted, holdout_t1_std)
    scalar["normalized_mean_regret"] = action["mean_normalized_teacher_regret"]
    return {"action": action, "max_pooled_t1": scalar}


def _numerical_gate(fit: dict) -> dict:
    solver = fit["solver"]
    prediction = fit["prediction_difference_vs_matched"]["holdout"]["normalized_by_weighted_holdout_target_std"]
    values = {
        "finite_parameters": bool(np.all(np.isfinite(fit["matched"]))),
        "relative_linear_system_residual": solver["relative_linear_system_residual"],
        "objective_excess": fit["objective_excess"],
        "holdout_prediction_difference_normalized": prediction,
    }
    values["pass"] = bool(
        values["finite_parameters"]
        and values["relative_linear_system_residual"] <= 1e-10
        and abs(values["objective_excess"]) <= 1e-10
        and values["holdout_prediction_difference_normalized"] <= 1e-8
    )
    return values


def _margin_diagnosis(rows: list[dict], predictions: np.ndarray, contributions: dict[str, np.ndarray]) -> dict:
    contributions = {name: values for name, values in contributions.items() if len(values) == len(rows)}
    groups = _root_groups(rows, "holdout")
    wrong = []
    for identity, group in groups.items():
        teacher_index = max(group, key=lambda index: (rows[index]["q"], -index))
        predicted_index = max(group, key=lambda index: (predictions[index], -index))
        if teacher_index == predicted_index:
            continue
        margin = {name: float(values[teacher_index] - values[predicted_index]) for name, values in contributions.items()}
        wrong.append({"root_identity": identity, "margin": float(rows[teacher_index]["q"] - rows[predicted_index]["q"]), "contributions": margin})
    families = list(contributions)
    stats = {}
    for family in families:
        stats[family] = {
            "largest_positive_fraction": float(np.mean([max(item["contributions"], key=item["contributions"].get) == family for item in wrong])) if wrong else 0.0,
            "over_50_percent_positive_fraction": float(np.mean([item["contributions"][family] >= 0.5 * sum(max(0.0, value) for value in item["contributions"].values()) for item in wrong])) if wrong else 0.0,
            "mean_signed_margin_contribution": float(np.mean([item["contributions"][family] for item in wrong])) if wrong else 0.0,
            "mean_absolute_margin_contribution": float(np.mean([abs(item["contributions"][family]) for item in wrong])) if wrong else 0.0,
        }
    return {"wrong_top1_roots": len(wrong), "families": stats}


def _model_contributions(fit: dict, rows: list[dict], groups: dict[str, list[int]]) -> dict[str, np.ndarray]:
    pack = fit["pack"]
    x = np.asarray([row["features"] for row in rows], dtype=np.float64)
    normalized = (x - pack["feature_mean"]) / pack["feature_scale"]
    coefficients = np.zeros(len(pack["active"]), dtype=np.float64)
    coefficients[pack["active"]] = fit["matched"][:-1]
    per_feature = pack["target_std"] * normalized * coefficients[None, :]
    return {name: np.sum(per_feature[:, indices], axis=1) if indices else np.zeros(len(rows), dtype=np.float64) for name, indices in groups.items()}


def _run(output: Path) -> dict:
    started = time.time()
    microtests = _microtests()
    _write_progress(output, "genericity-microtests", microtests)
    if not microtests["pass"]:
        return {"schema": "F133_SHOGI_RESOURCE_TRANSITION_ACTION_SEMANTICS_V1", "classification": "F133_GENERICITY_MICROTEST_FAILURE", "microtests": microtests, "runtime_seconds": time.time() - started}

    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    base = FrozenBasis(FAMILY, compiled)
    rows, surface, shard_info = _build_surface(compiled, base, output)
    baseline_fit = _fit(rows, [row["target"] for row in rows])
    baseline_predictions = _predictions(baseline_fit, rows)
    holdout_teacher, _ = _t1_predictions(rows, baseline_predictions, "holdout")
    holdout_t1_std = float(np.std(holdout_teacher)) or 1.0
    baseline_report = _action_and_t1_report(rows, baseline_predictions, holdout_t1_std)
    reproduction = {
        "baseline": baseline_report,
        "pass": abs(baseline_report["action"]["top1_agreement"] - F131_TOP1) <= 1e-10
        and abs(baseline_report["action"]["pairwise_ordering_agreement"] - F131_PAIRWISE) <= 1e-10
        and abs(baseline_report["action"]["mean_normalized_teacher_regret"] - F131_NREGRET) <= 1e-10
        and abs(baseline_report["max_pooled_t1"]["rmse_oracle_units"] - F131_POOLED_RMSE) <= 1e-6,
    }
    _write_progress(output, "f131-reproduction", reproduction)
    if not reproduction["pass"]:
        return {"schema": "F133_SHOGI_RESOURCE_TRANSITION_ACTION_SEMANTICS_V1", "classification": "F133_FROZEN_BASELINE_REPRODUCTION_FAILURE", "microtests": microtests, "reproduction": reproduction, "runtime_seconds": time.time() - started}

    deltas = []
    contributions = {"material_board": [], "piece_square": [], "mobility": [], "king_safety": [], "hand_inventory": [], "promotion": [], "drop_opportunity": [], "other": []}
    resource_deltas = []
    max_recomposition_error = 0.0
    family_indices = {}
    for index, name in enumerate(base.names):
        family_indices.setdefault(_family(name), []).append(index)
    resource_classes = _resource_classes(compiled)
    for row in rows:
        root_phi = base.vector(row["root_state"])
        child = apply_action(row["root_state"], row["action_obj"], compiled)
        delta = -base.vector(child) - root_phi
        recomposed = float(delta @ np.asarray(base.weights, dtype=np.float64))
        max_recomposition_error = max(max_recomposition_error, abs(recomposed - row["target"]))
        deltas.append(delta)
        for family, indices in family_indices.items():
            contributions.setdefault(family, []).append(float(delta[indices] @ np.asarray([base.weights[index] for index in indices], dtype=np.float64)))
        resource_deltas.append(_resource_transition(row["root_state"].position, child.position, resource_classes))
    delta_matrix = np.asarray(deltas, dtype=np.float64)
    resource_matrix = np.asarray(resource_deltas, dtype=np.float64)
    hand_weight_by_type = {
        type_id: float(base.weights[base.names.index(f"hand_diff:{type_id}")])
        for type_id in base.hand_types
    }
    class_hand_weights = np.asarray([
        sum(hand_weight_by_type.get(type_id, 0.0) for type_id in item["members"])
        for item in resource_classes["classes"]
    ], dtype=np.float64)
    hand_values = resource_matrix @ class_hand_weights
    f132_exact = {"action_count": len(rows), "max_abs_error": float(max_recomposition_error), "pass": max_recomposition_error <= 1e-9, "named_hand_family_component_is_retained_for_audit": True}
    if not f132_exact["pass"]:
        return {"schema": "F133_SHOGI_RESOURCE_TRANSITION_ACTION_SEMANTICS_V1", "classification": "F132_ORACLE_ADVANTAGE_RECOMPOSITION_FAILURE", "microtests": microtests, "reproduction": reproduction, "f132_exact_decomposition": f132_exact, "runtime_seconds": time.time() - started}

    hand_control_rows = rows
    nonhand_labels = np.asarray([row["target"] for row in rows], dtype=np.float64) - hand_values
    hand_control_fit = _fit(hand_control_rows, nonhand_labels.tolist())
    hand_control_predictions = _predictions(hand_control_fit, rows) + hand_values
    hand_control_report = _action_and_t1_report(rows, hand_control_predictions, holdout_t1_std)

    resource_rows = _rows_with_features(rows, resource_matrix)
    resource_fit = _fit(resource_rows, hand_values.tolist())
    resource_predictions = _predictions(resource_fit, resource_rows)
    resource_metrics = {}
    holdout_resource_std = float(np.std(hand_values[[index for index, row in enumerate(rows) if row["split"] == "holdout"]])) or 1.0
    for split in ("train", "dev", "holdout"):
        indices = [index for index, row in enumerate(rows) if row["split"] == split]
        resource_metrics[split] = _scalar_metrics(hand_values[indices], resource_predictions[indices], holdout_resource_std)
    resource_identification = {"metrics": resource_metrics, "numerical_gate": _numerical_gate(resource_fit), "holdout_gate": bool(resource_metrics["holdout"]["normalized_rmse"] <= 0.05 and resource_metrics["holdout"]["r2"] >= 0.99 and resource_metrics["holdout"]["pearson"] >= 0.995)}
    _write_progress(output, "resource-identification", resource_identification)
    if not resource_identification["holdout_gate"]:
        return {"schema": "F133_SHOGI_RESOURCE_TRANSITION_ACTION_SEMANTICS_V1", "classification": "GENERIC_RESOURCE_CLASS_ENCODING_CANNOT_IDENTIFY_HAND_COMPONENT", "microtests": microtests, "reproduction": reproduction, "f132_exact_decomposition": f132_exact, "resource_classes": resource_classes, "resource_identification": resource_identification, "hand_exact_control": hand_control_report, "runtime_seconds": time.time() - started}

    candidate_features = np.column_stack([np.asarray([row["features"] for row in rows], dtype=np.float64), resource_matrix])
    candidate_rows = _rows_with_features(rows, candidate_features)
    candidate_fit = _fit(candidate_rows, [row["target"] for row in rows])
    candidate_predictions = _predictions(candidate_fit, candidate_rows)
    candidate_report = _action_and_t1_report(rows, candidate_predictions, holdout_t1_std)
    action_feature_width = len(rows[0]["features"])
    candidate_groups = {
        "frozen_f131_action": list(range(action_feature_width)),
        "hand_inventory": list(range(action_feature_width, candidate_features.shape[1])),
    }
    candidate_contributions = _model_contributions(candidate_fit, candidate_rows, candidate_groups)
    candidate_margin = _margin_diagnosis(rows, candidate_predictions, candidate_contributions)
    baseline_margin = _margin_diagnosis(rows, baseline_predictions, {family: np.asarray(values, dtype=np.float64) for family, values in contributions.items()})
    candidate_t1_rmse = candidate_report["max_pooled_t1"]["rmse_oracle_units"]
    candidate_action = candidate_report["action"]
    primary_pass = bool(candidate_action["top1_agreement"] >= 0.90 and candidate_action["pairwise_ordering_agreement"] >= 0.95 and candidate_action["mean_normalized_teacher_regret"] <= 0.05)
    useful = bool(candidate_t1_rmse < F131_POOLED_RMSE)
    hand_dominance = candidate_margin["families"].get("hand_inventory", {}).get("largest_positive_fraction", 0.0)
    improvement = candidate_action["top1_agreement"] - F131_TOP1
    regret_reduction = (F131_NREGRET - candidate_action["mean_normalized_teacher_regret"]) / F131_NREGRET
    if not resource_identification["numerical_gate"]["pass"]:
        classification = "F133_RESOURCE_ACTION_SOLVER_NUMERICAL_FAILURE"
    elif improvement < 0.05 and regret_reduction < 0.20:
        classification = "RESOURCE_TRANSITION_SEMANTICS_DO_NOT_EXPLAIN_F131_FAILURE"
    elif hand_dominance < 0.35 and not primary_pass:
        classification = "RESOURCE_TRANSITION_SEMANTICS_PARTIAL_REPAIR"
    elif primary_pass and not useful:
        classification = "RESOURCE_ACTION_POLICY_PASSES_T1_CALIBRATION_REMAINS"
    elif primary_pass and useful and hand_dominance < 0.35:
        classification = "GENERIC_RESOURCE_TRANSITION_ACTION_SEMANTICS_PASSES"
    else:
        classification = "RESOURCE_TRANSITION_SEMANTICS_PARTIAL_REPAIR"
    result = {
        "schema": "F133_SHOGI_RESOURCE_TRANSITION_ACTION_SEMANTICS_V1",
        "baseline": BASELINE,
        "resource_schema": RESOURCE_SCHEMA,
        "microtests": microtests,
        "reproduction": reproduction,
        "f132_exact_decomposition": f132_exact,
        "resource_classes": {"count": len(resource_classes["classes"]), "classes": [{key: item[key] for key in ("class_id", "signature_sha256", "members")} for item in resource_classes["classes"]]},
        "hand_component": {"class_weights": class_hand_weights.tolist(), "source": "authoritative_root_child_hand_delta_times_frozen_hand_weights"},
        "resource_identification": resource_identification,
        "hand_exact_control": hand_control_report,
        "f131_baseline": baseline_report,
        "f133_resource_action": {"feature_width": int(candidate_features.shape[1]), "numerical_gate": _numerical_gate(candidate_fit), "metrics": candidate_report, "primary_action_gate": primary_pass, "usefulness_gate": useful},
        "post_fit_hand_diagnosis": {"f131_baseline": baseline_margin, "f133_candidate": candidate_margin, "hand_inventory_largest_positive_fraction": hand_dominance},
        "classification": classification,
        "runtime_seconds": time.time() - started,
        "shards": shard_info,
        "surface": surface,
    }
    _write_progress(output, "final", result)
    return result


def run(output: Path | None = None) -> dict:
    return _run(output or Path(".generic_chess_flow/f133-shogi-result.json"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({"classification": result.get("classification"), "runtime_seconds": result.get("runtime_seconds")}, sort_keys=True))


if __name__ == "__main__":
    main()
