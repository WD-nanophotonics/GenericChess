"""Zero-search decomposition of the published F109 Semantic Policy-v0.

This audit consumes only the persisted F109 bundles.  It never invokes a
teacher search, self-play, Arena, or policy training variant.  The only rule
runtime work is deterministic legal-action reconstruction from each persisted
history for collision witnesses.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.learning.policy import (
    SemanticPolicyExample,
    SemanticPolicyV0,
    fit_semantic_policy_v0,
    policy_target_from_q,
    semantic_action_features,
)
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.mirror import pack_semantic_action
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


WORK_ORDER_ID = "GENERICCHESS_F110_POLICY_V0_FAILURE_DECOMPOSITION"
CHECKPOINT_IDS = {
    "western_chess": "55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e",
    "standard_shogi": "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4",
}
MODEL_SHA = {
    "western_chess": "f1e516f1d8278a3048f121df7df3191572c7073d42bb6ee31eefb78423ccdc06",
    "standard_shogi": "6a4c47e7d45c5363b908f909640bdd31e4d41d700cd6cb6d1e4c8598fbefa8d8",
}
FIT_SEEDS = {"western_chess": 1090111, "standard_shogi": 1090211}
TYPE_COORDS = (21, 22, 23)


def _load_bundle(path: Path, name: str) -> tuple[dict[str, Any], SemanticPolicyV0]:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    policy = SemanticPolicyV0.from_dict(bundle["policy_artifact"])
    if bundle["frozen_checkpoint_id"] != CHECKPOINT_IDS[name]:
        raise AssertionError(f"{name}: frozen checkpoint identity mismatch")
    if policy.model_sha256 != MODEL_SHA[name] or policy.computed_model_sha256 != MODEL_SHA[name]:
        raise AssertionError(f"{name}: frozen policy SHA mismatch")
    return bundle, policy


def _examples(bundle: dict[str, Any]) -> list[tuple[str, SemanticPolicyExample, dict[str, Any]]]:
    result = []
    for row in bundle["rows"]:
        example = SemanticPolicyExample(
            state=tuple(row["state_features"]),
            actions=tuple(tuple(values) for values in row["action_features"]),
            target=tuple(row["target"]),
            root_identity=row["root_identity"],
        )
        result.append((row["split"], example, row))
    return result


def _probabilities(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits)
    weights = np.exp(shifted)
    return weights / np.sum(weights)


def _pairwise(q: np.ndarray, logits: np.ndarray) -> float:
    total = correct = 0
    for left in range(len(q)):
        for right in range(left + 1, len(q)):
            if q[left] == q[right]:
                continue
            total += 1
            correct += int((q[left] - q[right]) * (logits[left] - logits[right]) > 0)
    return correct / total if total else 1.0


def _root_metrics(policy: SemanticPolicyV0, selected: list[tuple[str, SemanticPolicyExample, dict[str, Any]]]) -> dict[str, Any]:
    values = defaultdict(list)
    for _split, example, row in selected:
        logits = policy.logits(example.state, example.actions)
        probs = _probabilities(logits)
        target = np.asarray(example.target, dtype=np.float64)
        q = np.asarray(row["q_values"], dtype=np.float64)
        values["target_entropy"].append(float(-np.sum(target * np.log(np.maximum(target, 1e-300)))))
        values["policy_entropy"].append(float(-np.sum(probs * np.log(np.maximum(probs, 1e-300)))))
        values["cross_entropy"].append(float(-np.sum(target * np.log(np.maximum(probs, 1e-300)))))
        values["kl_target_policy"].append(float(np.sum(target * np.log(np.maximum(target, 1e-300) / np.maximum(probs, 1e-300)))))
        values["top1_q1k_agreement"].append(float(np.argmax(probs) == np.argmax(q)))
        values["complete_pairwise_ranking_accuracy"].append(_pairwise(q, logits))
        values["q1k_regret_policy_top"].append(float(np.max(q) - q[int(np.argmax(probs))]))
        values["logit_std"].append(float(np.std(logits)))
        values["maximum_policy_probability"].append(float(np.max(probs)))
    return {
        "roots": len(selected),
        **{key: (float(np.mean(item)) if item else None) for key, item in values.items()},
    }


def _split_metrics(policy: SemanticPolicyV0, examples: list[tuple[str, SemanticPolicyExample, dict[str, Any]]]) -> dict[str, Any]:
    return {split: _root_metrics(policy, [item for item in examples if item[0] == split]) for split in ("train", "dev", "holdout")}


def _init_params(state_width: int, seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    scale = np.sqrt(2.0 / (state_width + 16))
    return [
        rng.normal(0.0, scale, size=(16, state_width)),
        np.zeros(16, dtype=np.float64),
        rng.normal(0.0, 1.0 / np.sqrt(24.0), size=(16, 24)),
        np.zeros(24, dtype=np.float64),
    ]


def _params_model(params: list[np.ndarray], template: SemanticPolicyV0) -> SemanticPolicyV0:
    return SemanticPolicyV0(
        ruleset_fingerprint=template.ruleset_fingerprint,
        state_schema_id=template.state_schema_id, action_schema_id=template.action_schema_id,
        state_width=template.state_width, action_width=template.action_width, hidden_width=16,
        state_weights=tuple(tuple(float(v) for v in row) for row in params[0]),
        state_bias=tuple(float(v) for v in params[1]),
        action_embedding=tuple(tuple(float(v) for v in row) for row in params[2]),
        action_bias=tuple(float(v) for v in params[3]),
        corpus_config=template.corpus_config, training_config=template.training_config,
        hand_type_indices=template.hand_type_indices,
    )


def _loss_metrics(params: list[np.ndarray], examples: list[tuple[str, SemanticPolicyExample, dict[str, Any]]]) -> dict[str, float]:
    ce = []
    kl = []
    top = []
    for _split, example, row in examples:
        state, phi, target = example.arrays()
        hidden = np.tanh(params[0] @ state + params[1])
        logits = phi @ (params[2].T @ hidden + params[3])
        probs = _probabilities(logits)
        q = np.asarray(row["q_values"], dtype=np.float64)
        ce.append(-np.sum(target * np.log(np.maximum(probs, 1e-300))))
        kl.append(np.sum(target * np.log(np.maximum(target, 1e-300) / np.maximum(probs, 1e-300))))
        top.append(float(np.argmax(probs) == np.argmax(q)))
    return {"cross_entropy": float(np.mean(ce)), "kl": float(np.mean(kl)), "top1": float(np.mean(top))}


def _gradients(params: list[np.ndarray], examples: list[tuple[str, SemanticPolicyExample, dict[str, Any]]], regularization: float) -> list[np.ndarray]:
    gradients = [np.zeros_like(param) for param in params]
    for _split, example, _row in examples:
        state, phi, target = example.arrays()
        hidden = np.tanh(params[0] @ state + params[1])
        action_vector = params[2].T @ hidden + params[3]
        logits = phi @ action_vector
        probabilities = _probabilities(logits)
        dlogits = (probabilities - target) / len(examples)
        d_action = phi.T @ dlogits
        gradients[2] += np.outer(hidden, d_action)
        gradients[3] += d_action
        d_hidden = params[2] @ d_action
        d_state = d_hidden * (1.0 - hidden * hidden)
        gradients[0] += np.outer(d_state, state)
        gradients[1] += d_state
    for param, gradient in zip(params, gradients):
        gradient += regularization * param
    return gradients


def _replay_fit(policy: SemanticPolicyV0, train: list[tuple[str, SemanticPolicyExample, dict[str, Any]]], seed: int) -> dict[str, Any]:
    params = _init_params(policy.state_width, seed)
    moments = [(np.zeros_like(param), np.zeros_like(param)) for param in params]
    checkpoints = {0, 1, 10, 50, 100, 200, 400}
    trace = {}
    for step in range(0, 401):
        gradients = _gradients(params, train, 1e-4)
        if step in checkpoints:
            model = _params_model(params, policy)
            trace[str(step)] = {
                **_loss_metrics(params, train),
                "mean_max_logit": float(np.mean([np.max(np.abs(model.logits(e.state, e.actions))) for _, e, _ in train])),
                "mean_abs_hidden": float(np.mean([np.mean(np.abs(model.hidden(e.state))) for _, e, _ in train])),
                "hidden_abs_gt_095_fraction": float(np.mean([np.mean(np.abs(model.hidden(e.state)) > 0.95) for _, e, _ in train])),
                "parameter_l2": [float(np.linalg.norm(param)) for param in params],
                "gradient_l2": [float(np.linalg.norm(gradient)) for gradient in gradients],
            }
        if step == 400:
            break
        for index, (param, gradient) in enumerate(zip(params, gradients)):
            first, second = moments[index]
            first[...] = 0.9 * first + 0.1 * gradient
            second[...] = 0.999 * second + 0.001 * gradient * gradient
            first_hat = first / (1.0 - 0.9 ** (step + 1))
            second_hat = second / (1.0 - 0.999 ** (step + 1))
            param[...] -= 0.005 * first_hat / (np.sqrt(second_hat) + 1e-8)
    replayed = _params_model(params, policy)
    return {"trace": trace, "replayed_model_sha256": replayed.computed_model_sha256, "published_model_sha256": policy.model_sha256,
            "identity": replayed.computed_model_sha256 == policy.model_sha256}


def _target_scale_audit(examples: list[tuple[str, SemanticPolicyExample, dict[str, Any]]]) -> dict[str, Any]:
    rows = []
    for split, _example, row in examples:
        q = np.asarray(row["q_values"], dtype=np.float64)
        median = float(np.median(q))
        iqr = float(np.percentile(q, 75.0) - np.percentile(q, 25.0))
        current = policy_target_from_q(q)
        specified = policy_target_from_q(q, epsilon=1.0)
        rows.append({"split": split, "iqr": iqr, "median": median,
                     "current_entropy": float(-np.sum(current * np.log(np.maximum(current, 1e-300)))),
                     "specified_entropy": float(-np.sum(specified * np.log(np.maximum(specified, 1e-300)))),
                     "current_max_probability": float(np.max(current)),
                     "specified_max_probability": float(np.max(specified)),
                     "target_kl_current_vs_specified": float(np.sum(current * np.log(np.maximum(current, 1e-300) / np.maximum(specified, 1e-300)))),
                     "teacher_top_changes": bool(np.argmax(current) != np.argmax(specified))})
    return {"roots": len(rows), "zero_iqr_count": sum(row["iqr"] == 0.0 for row in rows),
            "iqr_lt_1_count": sum(row["iqr"] < 1.0 for row in rows),
            "by_split": {split: [row for row in rows if row["split"] == split] for split in ("train", "dev", "holdout")},
            "mean_current_entropy": float(np.mean([row["current_entropy"] for row in rows])),
            "mean_specified_entropy": float(np.mean([row["specified_entropy"] for row in rows])),
            "mean_target_kl_current_vs_specified": float(np.mean([row["target_kl_current_vs_specified"] for row in rows])),
            "teacher_top_changes": sum(row["teacher_top_changes"] for row in rows)}


def _collision_audit(examples: list[tuple[str, SemanticPolicyExample, dict[str, Any]]]) -> dict[str, Any]:
    root_rows = []
    witnesses = []
    unequal_collision_roots = 0
    collision_groups = 0
    collision_actions = 0
    for split, example, row in examples:
        groups = defaultdict(list)
        phi = np.asarray(example.actions, dtype=np.float64)
        target = np.asarray(example.target, dtype=np.float64)
        q = np.asarray(row["q_values"], dtype=np.float64)
        for index, vector in enumerate(phi):
            groups[tuple(float(value) for value in vector)].append(index)
        collided = [members for members in groups.values() if len(members) > 1]
        collision_groups += len(collided)
        collision_actions += sum(len(members) for members in collided)
        unequal = any(len({float(q[index]) for index in members}) > 1 for members in collided)
        unequal_collision_roots += int(unequal)
        group_probs = np.zeros(len(phi), dtype=np.float64)
        for members in groups.values():
            mass = float(np.sum(target[members]))
            group_probs[members] = mass / len(members)
        collision_ce = float(-np.sum(target * np.log(np.maximum(group_probs, 1e-300))))
        collision_kl = float(np.sum(target * np.log(np.maximum(target, 1e-300) / np.maximum(group_probs, 1e-300))))
        root_rows.append({"root_identity": row["root_identity"], "split": split, "actions": len(phi),
                          "unique_feature_vectors": len(groups), "collision_group_count": len(collided),
                          "largest_collision_group": max((len(members) for members in collided), default=1),
                          "fraction_actions_in_collisions": sum(len(members) for members in collided) / len(phi),
                          "collision_contains_unequal_q": unequal, "collision_only_min_ce": collision_ce,
                          "collision_only_min_kl": collision_kl})
        if unequal and len(witnesses) < 12:
            for members in collided:
                if len({float(q[index]) for index in members}) > 1:
                    witnesses.append({"root_identity": row["root_identity"], "split": split,
                                      "members": members, "feature_vector": phi[members[0]].tolist(),
                                      "q_values": [float(q[index]) for index in members],
                                      "target_probabilities": [float(target[index]) for index in members]})
                    break
    return {"roots": root_rows, "representative_witnesses": witnesses,
            "collision_group_count": collision_groups, "collision_action_count": collision_actions,
            "roots_with_unequal_q_collision": unequal_collision_roots,
            "max_collision_only_ce": max((row["collision_only_min_ce"] for row in root_rows), default=0.0)}


def _linear_oracle(phi: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, int]:
    weights = np.zeros(phi.shape[1], dtype=np.float64)
    ridge = 1e-8
    for iteration in range(50):
        probs = _probabilities(phi @ weights)
        gradient = phi.T @ (probs - target) + ridge * weights
        covariance = np.diag(probs) - np.outer(probs, probs)
        hessian = phi.T @ covariance @ phi + ridge * np.eye(phi.shape[1])
        try:
            direction = np.linalg.solve(hessian, -gradient)
        except np.linalg.LinAlgError:
            direction = np.linalg.lstsq(hessian, -gradient, rcond=None)[0]
        base = float(-np.sum(target * np.log(np.maximum(probs, 1e-300))) + 0.5 * ridge * np.dot(weights, weights))
        step = 1.0
        while step > 1e-8:
            candidate = weights + step * direction
            candidate_probs = _probabilities(phi @ candidate)
            value = float(-np.sum(target * np.log(np.maximum(candidate_probs, 1e-300))) + 0.5 * ridge * np.dot(candidate, candidate))
            if value <= base:
                weights = candidate
                break
            step *= 0.5
        if np.linalg.norm(gradient) < 1e-8:
            return weights, iteration + 1
    return weights, 50


def _oracle_audit(examples: list[tuple[str, SemanticPolicyExample, dict[str, Any]]]) -> dict[str, Any]:
    root_rows = []
    oracle_weights = []
    for split, example, row in examples:
        _, phi, target = example.arrays()
        q = np.asarray(row["q_values"], dtype=np.float64)
        weights, iterations = _linear_oracle(phi, target)
        logits = phi @ weights
        probs = _probabilities(logits)
        root_rows.append({"root_identity": row["root_identity"], "split": split, "iterations": iterations,
                          "ce": float(-np.sum(target * np.log(np.maximum(probs, 1e-300)))),
                          "kl": float(np.sum(target * np.log(np.maximum(target, 1e-300) / np.maximum(probs, 1e-300)))),
                          "top1_q1k_agreement": float(np.argmax(probs) == np.argmax(q)),
                          "q1k_regret": float(np.max(q) - q[int(np.argmax(probs))]),
                          "pairwise_accuracy": _pairwise(q, logits)})
        oracle_weights.append(weights)
    by_split = {}
    for split in ("train", "dev", "holdout"):
        selected = [row for row in root_rows if row["split"] == split]
        by_split[split] = {key: float(np.mean([row[key] for row in selected])) for key in ("ce", "kl", "top1_q1k_agreement", "q1k_regret", "pairwise_accuracy")} if selected else None
    matrix = np.asarray(oracle_weights, dtype=np.float64)
    centered = matrix - np.mean(matrix, axis=0, keepdims=True)
    singular = np.linalg.svd(centered, compute_uv=False) if len(matrix) else np.zeros(0)
    variance = float(np.sum(singular * singular))
    return {"by_split": by_split, "roots": root_rows, "weights": matrix.tolist(),
            "centered_weight_singular_values": singular.tolist(),
            "centered_weight_variance_fraction_rank_16": float(np.sum(singular[:16] ** 2) / variance) if variance else 1.0}


def _reconstruct_actions(name: str, examples: list[tuple[str, SemanticPolicyExample, dict[str, Any]]]):
    builder = build_western_chess_ruleset if name == "western_chess" else build_standard_shogi_ruleset
    compiled = compile_semantic_ruleset(builder())
    native_rules = compile_native_semantic_rules(compiled)
    reconstructed = {}
    for _split, _example, row in examples:
        session = GameSession(compiled)
        for item in row["history"]:
            session.submit(action_from_dict(item))
        actions = tuple(sorted(session.legal_actions(), key=lambda action: int(pack_semantic_action(native_rules, session.state.position, action))))
        encoded = np.asarray([semantic_action_features(compiled, session.state.position, action) for action in actions], dtype=np.float64)
        stored = np.asarray(_example.actions, dtype=np.float64)
        reconstructed[row["root_identity"]] = {
            "actions": [action_to_dict(action) for action in actions],
            "feature_matrix_match": bool(encoded.shape == stored.shape and np.array_equal(encoded, stored)),
        }
    return reconstructed


def _type_audit(examples, reconstructed) -> dict[str, Any]:
    frequencies = Counter()
    top_frequencies = Counter()
    near_matches = []
    for _split, example, row in examples:
        reconstructed_row = reconstructed.get(row["root_identity"], {"actions": [], "feature_matrix_match": False})
        actions = reconstructed_row["actions"]
        q = np.asarray(row["q_values"], dtype=np.float64)
        top = int(np.argmax(q))
        for index, action in enumerate(actions):
            actor = action.get("actor_type_id") or action.get("base_type_id") or "unknown"
            kind = "drop" if action.get("kind") == "semantic_drop" else "board"
            frequencies[f"{kind}:actor:{actor}"] += 1
            if action.get("promotion_target_id"):
                frequencies[f"promotion:{action['promotion_target_id']}"] += 1
            if kind == "drop":
                frequencies[f"drop:{action.get('base_type_id', 'unknown')}"] += 1
            if index == top:
                top_frequencies[str(actor)] += 1
        phi = np.asarray(example.actions, dtype=np.float64)
        for left in range(len(phi)):
            for right in range(left + 1, len(phi)):
                if np.array_equal(np.delete(phi[left], TYPE_COORDS), np.delete(phi[right], TYPE_COORDS)) and not np.array_equal(phi[left, TYPE_COORDS], phi[right, TYPE_COORDS]):
                    if len(near_matches) < 20:
                        near_matches.append({"root_identity": row["root_identity"], "left": left, "right": right,
                                             "left_type_coordinates": phi[left, TYPE_COORDS].tolist(), "right_type_coordinates": phi[right, TYPE_COORDS].tolist(),
                                             "left_q": float(q[left]), "right_q": float(q[right]),
                                             "left_action": actions[left] if left < len(actions) else None,
                                             "right_action": actions[right] if right < len(actions) else None})
                    break
    return {"frequency_by_type": dict(frequencies), "teacher_top_action_frequency_by_actor_type": dict(top_frequencies),
            "near_matched_type_coordinate_witnesses": near_matches,
            "non_monotonic_type_witness_count": len(near_matches)}


def _hidden_audit(policy: SemanticPolicyV0, examples, oracle: dict[str, Any]) -> dict[str, Any]:
    hidden = np.asarray([policy.hidden(example.state) for _split, example, _row in examples], dtype=np.float64)
    singular = np.linalg.svd(hidden - np.mean(hidden, axis=0, keepdims=True), compute_uv=False)
    distances = []
    duplicate_different = []
    for left in range(len(hidden)):
        for right in range(left + 1, len(hidden)):
            distance = float(np.linalg.norm(hidden[left] - hidden[right]))
            distances.append(distance)
            if distance < 1e-8:
                target_left = np.asarray(examples[left][1].target)
                target_right = np.asarray(examples[right][1].target)
                if np.linalg.norm(target_left - target_right, ord=1) > 0.1:
                    duplicate_different.append({"left": examples[left][2]["root_identity"], "right": examples[right][2]["root_identity"], "target_l1": float(np.linalg.norm(target_left - target_right, ord=1))})
    return {"hidden_dimension": int(hidden.shape[1]), "train_hidden_numerical_rank": int(np.linalg.matrix_rank(hidden)),
            "singular_values": singular.tolist(), "pairwise_distance_summary": {"min": float(np.min(distances)) if distances else 0.0, "median": float(np.median(distances)) if distances else 0.0, "max": float(np.max(distances)) if distances else 0.0},
            "per_unit_mean": np.mean(hidden, axis=0).tolist(), "per_unit_std": np.std(hidden, axis=0).tolist(),
            "saturation_fraction_abs_gt_095": float(np.mean(np.abs(hidden) > 0.95)),
            "duplicate_or_near_duplicate_different_target_witnesses": duplicate_different,
            "hidden_matrix": hidden.tolist(),
            "oracle_weight_rank_16_fraction": oracle["centered_weight_variance_fraction_rank_16"]}


def _runtime_audit() -> dict[str, Any]:
    source = (ROOT / "generic_chess/_native/native_module.c").read_text(encoding="utf-8")
    checks = {
        "candidate_action_generation": "semantic_generate_legal_actions" in source or "gc_semantic_runtime_generate" in source,
        "policy_state_inference": "policy_state_inferences" in source,
        "candidate_make_checked": "gc_semantic_runtime_make_checked" in source,
        "action_feature_logit_calculation": "policy_action" in source and "logit" in source,
        "stable_sort": "qsort" in source or "policy_compare" in source,
    }
    return {"path": ["candidate action generation", "policy state inference", "per-candidate gc_semantic_runtime_make_checked", "action feature/logit calculation", "sorting", "later AlphaBeta child make_checked"],
            "source_checks": checks, "candidate_successors_reconstructed_during_search": True,
            "classification": "NATIVE_POLICY_DUPLICATE_TRANSITION_COST"}


def _diagnose(name: str, path: Path) -> dict[str, Any]:
    bundle, policy = _load_bundle(path, name)
    examples = _examples(bundle)
    counts = Counter(split for split, _example, _row in examples)
    complete = all(len(row["q_values"]) == row["action_count"] == len(row["action_features"]) == len(row["target"]) and row["complete_action_vector"] for _split, _example, row in examples)
    replay = _replay_fit(policy, [item for item in examples if item[0] == "train"], FIT_SEEDS[name])
    metrics = _split_metrics(policy, examples)
    scale = _target_scale_audit(examples)
    collision = _collision_audit(examples)
    oracle = _oracle_audit(examples)
    reconstructed = _reconstruct_actions(name, examples)
    type_audit = _type_audit(examples, reconstructed)
    hidden = _hidden_audit(policy, examples, oracle)
    runtime = _runtime_audit()
    target_material = scale["iqr_lt_1_count"] > 0 and (
        scale["mean_target_kl_current_vs_specified"] > 1e-12
        or abs(scale["mean_current_entropy"] - scale["mean_specified_entropy"]) > 1e-12
        or scale["teacher_top_changes"] > 0
    )
    train_underfit = all(metrics["train"][key] < bound for key, bound in (("top1_q1k_agreement", 0.75), ("complete_pairwise_ranking_accuracy", 0.75)))
    oracle_train = oracle["by_split"]["train"]
    linear_limit = oracle_train["top1_q1k_agreement"] < 0.75 or oracle_train["pairwise_accuracy"] < 0.75
    collision_limit = collision["roots_with_unequal_q_collision"] > 0
    state_mapping = not linear_limit and train_underfit
    saturation = hidden["saturation_fraction_abs_gt_095"] > 0.10
    type_limit = type_audit["non_monotonic_type_witness_count"] > 0
    return {"ruleset": name, "frozen_checkpoint_id": bundle["frozen_checkpoint_id"], "policy_model_sha256": policy.model_sha256,
            "root_counts": dict(counts), "complete_persisted_root_evidence": complete,
            "reconstructed_action_feature_matrices_match": all(value["feature_matrix_match"] for value in reconstructed.values()),
            "metrics": metrics, "deterministic_training_replay": replay,
            "target_scale_contract_audit": scale, "action_feature_collision_audit": collision,
            "linear_action_head_oracle": oracle, "type_index_representation_audit": type_audit,
            "state_encoder_bilinear_audit": hidden, "native_runtime_contract_audit": runtime,
            "flags": {"TARGET_SCALE_CONTRACT_MISMATCH_MATERIAL": target_material, "TRAIN_SET_UNDERFIT": train_underfit,
                      "GENERALIZATION_GAP_SUPPORTED": False, "ACTION_FEATURE_COLLISION_LIMIT_SUPPORTED": collision_limit,
                      "LINEAR_ACTION_HEAD_LIMIT_SUPPORTED": linear_limit, "STATE_TO_POLICY_MAPPING_LIMIT_SUPPORTED": state_mapping,
                      "HIDDEN_SATURATION_SUPPORTED": saturation, "TYPE_INDEX_ENCODING_LIMIT_SUPPORTED": type_limit,
                      "NATIVE_POLICY_DUPLICATE_TRANSITION_COST": True}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chess-bundle", type=Path, required=True)
    parser.add_argument("--shogi-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = {
        "western_chess": _diagnose("western_chess", args.chess_bundle),
        "standard_shogi": _diagnose("standard_shogi", args.shogi_bundle),
    }
    flags = {key: any(result["flags"][key] for result in results.values()) for key in next(iter(results.values()))["flags"]}
    if flags["TARGET_SCALE_CONTRACT_MISMATCH_MATERIAL"]:
        recommendation = "CORRECTED_TARGET_CONSTRUCTION_FIRST"
    elif flags["ACTION_FEATURE_COLLISION_LIMIT_SUPPORTED"] or flags["LINEAR_ACTION_HEAD_LIMIT_SUPPORTED"]:
        recommendation = "ACTION_ENCODER_V1_CATEGORICAL_TYPE_EMBEDDINGS_AND_MINIMAL_CROSS_FEATURES"
    elif flags["STATE_TO_POLICY_MAPPING_LIMIT_SUPPORTED"]:
        recommendation = "STATE_INTERACTION_V1"
    elif flags["GENERALIZATION_GAP_SUPPORTED"]:
        recommendation = "LARGER_FRESH_ON_POLICY_CORPUS_EXPERT_ITERATION"
    else:
        recommendation = "NO_POLICY_V1_CORRECTION_JUSTIFIED_BY_CURRENT_EVIDENCE"
    report = {"work_order_id": WORK_ORDER_ID, "baseline_sha": "839f99f99668b6a7ef7f221f98f8f2d8ccb02947",
              "new_search_performed": False, "new_training_variant_performed": False, "rulesets": results,
              "final_failure_decomposition": {"flags": flags, "selected_next_policy_v1_correction": recommendation,
                                              "native_duplicate_transition_is_separate_efficiency_issue": True},
              "status": "CONTINUE", "candidate_sha": "NONE", "promotion": "HOLD"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
    print(json.dumps({"work_order_id": WORK_ORDER_ID, "selected_next_policy_v1_correction": recommendation, "flags": flags}, sort_keys=True))


if __name__ == "__main__":
    main()
