"""F125: compress one exact known-oracle one-ply search layer."""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import (
        COUNTS,
        FrozenBasis,
        _collect_fresh_roots,
        _json_sha,
    )
    from scripts.f123_reverse_benchmark_identifiability_optimizer_diagnosis import (
        FAMILIES,
        _predict,
        _scalar_summary,
    )
    from scripts.f124_reverse_benchmark_stable_convex_solver import _pcg, _normal_system
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import (
        COUNTS,
        FrozenBasis,
        _collect_fresh_roots,
        _json_sha,
    )
    from f123_reverse_benchmark_identifiability_optimizer_diagnosis import (
        FAMILIES,
        _predict,
        _scalar_summary,
    )
    from f124_reverse_benchmark_stable_convex_solver import _pcg, _normal_system

from generic_chess.core.declarations import available_declarations
from generic_chess.core.identity import position_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


ORACLE_HASHES = {
    "western_chess": "77cfc280d9108a461629e9de492b71d8257213fc8088ce69c1584232c2668ec9",
    "standard_shogi": "dda316e263a8f6e5a12678199e87cbedea7e4d40358d3087e8c78ddb3894a316",
}
CORPUS_HASHES = {
    "western_chess": "79625a972c980c607eb6a9a1b930ebaba2fd447bbe320c52b3ec62ae510b91ac",
    "standard_shogi": "a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b",
}
DECISION_ROOT_SEEDS = {
    "western_chess": 1250121,
    "standard_shogi": 1250221,
}
L2 = 1e-6


def _sorted_actions(state, compiled):
    return sorted(legal_actions(state, compiled), key=str)


def _collect_corpus_states(family, compiled, basis, seed, forbidden):
    needed = sum(COUNTS.values())
    seen = set(forbidden)
    rows = []
    trajectory_lengths = (8, 24, 64, 128, 192, 256)
    trajectory = 0
    while len(rows) < needed:
        rng = random.Random(seed + trajectory * 7919)
        state = initial_state(compiled)
        length = trajectory_lengths[trajectory % len(trajectory_lengths)]
        for ply in range(length):
            actions = _sorted_actions(state, compiled)
            if not actions:
                break
            state = apply_action(state, actions[rng.randrange(len(actions))], compiled)
            key = str(position_identity_key(state.position, compiled))
            if key in seen or state.terminal_status.status is not TerminalStatus.ONGOING:
                continue
            seen.add(key)
            features = basis.vector(state)
            rows.append({
                "identity": key,
                "trajectory": trajectory,
                "ply": state.ply_count,
                "side_to_move": state.position.side_to_move,
                "features": features.tolist(),
                "direct_oracle": basis.oracle(features),
                "state": state,
            })
            if len(rows) >= needed:
                break
        trajectory += 1
        if trajectory > 2000:
            raise RuntimeError(f"corpus generation exceeded trajectory bound for {family}")
    return rows


def _terminal_value(state, basis):
    status = state.terminal_status
    if status.status is TerminalStatus.ONGOING:
        return basis.oracle(basis.vector(state)), False
    if status.winner is None:
        return 0.0, True
    value = 1_000_000.0 if status.winner == state.position.side_to_move else -1_000_000.0
    return value, True


def _t1_from_children(state, basis, children):
    actions = [action for action, _ in children]
    if not actions:
        value, terminal = _terminal_value(state, basis)
        return -value, [], terminal
    scores = []
    terminal_child = False
    for _, child in children:
        child_value, child_terminal = _terminal_value(child, basis)
        terminal_child = terminal_child or child_terminal
        scores.append(-child_value)
    best = max(range(len(actions)), key=lambda index: (scores[index], -index))
    return float(scores[best]), list(zip(actions, scores)), terminal_child


def _t1(state, basis):
    actions = _sorted_actions(state, basis.compiled)
    children = [(action, apply_action(state, action, basis.compiled)) for action in actions]
    return _t1_from_children(state, basis, children)


def _declaration_present(state, compiled):
    return bool(available_declarations(state, compiled))


def _teacher_row(row, basis):
    state = row["state"]
    value, spectrum, terminal_child = _t1(state, basis)
    shogi_declaration = False
    if basis.family == "standard_shogi":
        shogi_declaration = _declaration_present(state, basis.compiled)
        if not shogi_declaration:
            for action, _ in spectrum:
                child = apply_action(state, action, basis.compiled)
                if _declaration_present(child, basis.compiled):
                    shogi_declaration = True
                    break
    return {"t1": value, "spectrum": spectrum, "terminal_child": terminal_child, "shogi_declaration": shogi_declaration}


def _prepare_rows(rows, labels):
    output = []
    for row, label in zip(rows, labels):
        output.append({"identity": row["identity"], "features": row["features"], "oracle": float(label)})
    return output


def _prepare_filtered(rows, labels, basis):
    raw = {split: np.asarray([row["features"] for row in rows if row["split"] == split], dtype=np.float64) for split in ("train", "dev", "holdout")}
    oracle = {split: np.asarray([label for row, label in zip(rows, labels) if row["split"] == split], dtype=np.float64) for split in ("train", "dev", "holdout")}
    train_x = raw["train"]
    train_y = oracle["train"]
    if not all(len(raw[split]) for split in raw) or not len(train_y):
        raise RuntimeError("F125_RETAINED_SPLIT_EMPTY")
    feature_mean = train_x.mean(axis=0)
    feature_scale = train_x.std(axis=0)
    active = feature_scale > 1e-12
    safe_scale = np.where(active, feature_scale, 1.0)
    target_mean = float(train_y.mean())
    target_std = float(train_y.std()) or 1.0
    normalized = {split: (raw[split] - feature_mean) / safe_scale for split in raw}
    design = {split: np.column_stack([normalized[split][:, active], np.ones(len(normalized[split]))]) for split in raw}
    target = {split: (oracle[split] - target_mean) / target_std for split in raw}
    return {"raw": raw, "oracle": oracle, "feature_mean": feature_mean, "feature_scale": safe_scale, "active": active, "target_mean": target_mean, "target_std": target_std, "design": design, "target": target, "feature_count": len(basis.names)}


def _fit_metrics(rows, labels, basis):
    pack = _prepare_filtered(rows, labels, basis)
    model, solver = _pcg(pack)
    hessian, rhs = _normal_system(pack)
    residual = rhs - hessian @ model
    design = pack["design"]["train"]
    gram = design.T @ design / len(design)
    gram[:-1, :-1] += L2 * np.eye(gram.shape[1] - 1)
    matched = np.linalg.solve(gram, design.T @ pack["target"]["train"] / len(design))
    objective = lambda candidate: float(0.5 * np.mean((design @ candidate - pack["target"]["train"]) ** 2) + 0.5 * L2 * np.sum(candidate[:-1] ** 2))
    model_vs_matched = {
        split: float(np.sqrt(np.mean((_predict(model, pack, split) - _predict(matched, pack, split)) ** 2)))
        for split in ("train", "dev", "holdout")
    }
    holdout_std = float(np.std(pack["oracle"]["holdout"])) or 1.0
    prediction_difference = {
        split: {"rmse_oracle_units": value, "normalized_by_holdout_target_std": value / holdout_std}
        for split, value in model_vs_matched.items()
    }
    return {
        "pack": pack,
        "pcg": model,
        "matched": matched,
        "solver": {**solver, "relative_linear_system_residual": float(np.linalg.norm(residual) / max(np.linalg.norm(rhs), 1e-30))},
        "scalar_metrics": {"PCG": _scalar_summary(model, pack), "matched_ridge": _scalar_summary(matched, pack)},
        "objective_excess": objective(model) - objective(matched),
        "prediction_difference_vs_matched": prediction_difference,
    }


def _rank_summary(scores, reference):
    order = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
    ref_order = sorted(range(len(reference)), key=lambda index: (-reference[index], index))
    pair_total = 0
    pair_same = 0
    for left in range(len(scores)):
        for right in range(left + 1, len(scores)):
            pair_total += 1
            pair_same += (order.index(left) < order.index(right)) == (ref_order.index(left) < ref_order.index(right))
    top = order[0]
    regret = float(reference[ref_order[0]] - reference[top])
    gaps = sorted(reference, reverse=True)
    return {"top": top, "order": order, "top1": top == ref_order[0], "pairwise": pair_same / pair_total if pair_total else 1.0, "regret": regret, "top2_gap": float(gaps[0] - gaps[1]) if len(gaps) > 1 else 0.0}


def _decision_records(roots, basis, fit):
    records = []
    for state in roots:
        actions = _sorted_actions(state, basis.compiled)
        if len(actions) < 2:
            continue
        children = [(action, apply_action(state, action, basis.compiled)) for action in actions]
        root_t1, static_spectrum, terminal_child = _t1_from_children(state, basis, children)
        if terminal_child:
            continue
        if basis.family == "standard_shogi" and (_declaration_present(state, basis.compiled) or any(_declaration_present(child, basis.compiled) for _, child in children)):
            continue
        static_scores = [score for _, score in static_spectrum]
        depth2_scores = []
        for _, child in children:
            child_t1, _, _ = _t1(child, basis)
            depth2_scores.append(-child_t1)
        compressed_scores = [-float(_predict_child(fit, basis, child)) for _, child in children]
        static = _rank_summary(static_scores, depth2_scores)
        compressed = _rank_summary(compressed_scores, depth2_scores)
        records.append({"static": static, "compressed": compressed, "depth2_scores": depth2_scores})
    return records


def _predict_child(fit, basis, state):
    vector = basis.vector(state)
    z = (vector - fit["pack"]["feature_mean"]) / fit["pack"]["feature_scale"]
    active = fit["pack"]["active"]
    model = fit["pcg"]
    return fit["pack"]["target_mean"] + fit["pack"]["target_std"] * (np.r_[z[active], 1.0] @ model)


def _decision_summary(records):
    if not records:
        return {"roots": 0, "informative": 0, "static_teacher_agreement": 0.0, "compressed": {}, "teacher_disagreement_recovery": {}, "teacher_correct_retention": {}}
    informative = [row for row in records if not row["static"]["top1"]]
    correct = [row for row in records if row["static"]["top1"]]
    static_regrets = [row["static"]["regret"] for row in records]
    compressed_regrets = [row["compressed"]["regret"] for row in records]
    teacher_std = float(np.std([score for row in records for score in row["depth2_scores"]])) or 1.0
    compressed = {
        "top1_agreement": float(np.mean([row["compressed"]["top1"] for row in records])),
        "pairwise_ordering_agreement": float(np.mean([row["compressed"]["pairwise"] for row in records])),
        "mean_teacher_regret": float(np.mean(compressed_regrets)),
        "median_teacher_regret": float(np.median(compressed_regrets)),
        "p95_teacher_regret": float(np.percentile(compressed_regrets, 95)),
        "mean_normalized_teacher_regret": float(np.mean(compressed_regrets) / teacher_std),
        "teacher_top2_gap_mean": float(np.mean([row["compressed"]["top2_gap"] for row in records])),
    }
    disagreement = {
        "roots": len(informative),
        "recovery": float(np.mean([row["compressed"]["top1"] for row in informative])) if informative else None,
        "static_mean_regret": float(np.mean([row["static"]["regret"] for row in informative])) if informative else None,
        "compressed_mean_regret": float(np.mean([row["compressed"]["regret"] for row in informative])) if informative else None,
        "fractional_regret_reduction": (1.0 - float(np.mean([row["compressed"]["regret"] for row in informative])) / float(np.mean([row["static"]["regret"] for row in informative]))) if informative and np.mean([row["static"]["regret"] for row in informative]) else None,
    }
    retention = {"roots": len(correct), "retention": float(np.mean([row["compressed"]["top1"] for row in correct])) if correct else None}
    return {"roots": len(records), "informative": len(informative), "static_teacher_agreement": float(np.mean([row["static"]["top1"] for row in records])), "static_mean_regret": float(np.mean(static_regrets)), "compressed": compressed, "teacher_disagreement_recovery": disagreement, "teacher_correct_retention": retention}


def _diagnose_family(family, corpus_seed, root_seed, decision_root_limit=256):
    builder = build_western_chess_ruleset if family == "western_chess" else build_standard_shogi_ruleset
    compiled = compile_semantic_ruleset(builder())
    basis = FrozenBasis(family, compiled)
    rows = _collect_corpus_states(family, compiled, basis, corpus_seed, set())
    identity_hash = _json_sha([row["identity"] for row in rows])
    if identity_hash != CORPUS_HASHES[family] or basis.oracle_weight_sha256 != ORACLE_HASHES[family]:
        raise RuntimeError("F125_FROZEN_CORPUS_IDENTITY_MISMATCH")
    labels = [_teacher_row(row, basis) for row in rows]
    retained = [index for index, label in enumerate(labels) if not label["terminal_child"] and not label["shogi_declaration"]]
    split_indices = {"train": [], "dev": [], "holdout": []}
    train_end = COUNTS["train"]
    dev_end = train_end + COUNTS["dev"]
    for index in retained:
        split_indices["train" if index < train_end else "dev" if index < dev_end else "holdout"].append(index)
    retained_rows = []
    for index in retained:
        split = "train" if index < train_end else "dev" if index < dev_end else "holdout"
        retained_rows.append({**rows[index], "split": split})
    direct_labels = [rows[index]["direct_oracle"] for index in retained]
    search_labels = [labels[index]["t1"] for index in retained]
    direct_fit = _fit_metrics(retained_rows, direct_labels, basis)
    search_fit = _fit_metrics(retained_rows, search_labels, basis)
    direct_gate = direct_fit["solver"]["relative_linear_system_residual"] <= 1e-10 and direct_fit["objective_excess"] <= 1e-10 and direct_fit["prediction_difference_vs_matched"]["holdout"]["normalized_by_holdout_target_std"] <= 1e-8 and direct_fit["scalar_metrics"]["PCG"]["holdout"]["normalized_rmse"] <= 0.05 and direct_fit["scalar_metrics"]["PCG"]["holdout"]["r2"] >= 0.99 and direct_fit["scalar_metrics"]["PCG"]["holdout"]["pearson"] >= 0.995
    reference_roots = _collect_fresh_roots(family, compiled, basis, 1220121, {row["identity"] for row in rows}, 256)
    forbidden = {row["identity"] for row in rows} | {str(position_identity_key(root.position, compiled)) for root in reference_roots}
    fresh_roots = _collect_fresh_roots(family, compiled, basis, root_seed, forbidden, decision_root_limit)
    decision_records = _decision_records(fresh_roots, basis, search_fit)
    decision = _decision_summary(decision_records)
    search_gate = {
        "holdout_normalized_rmse": search_fit["scalar_metrics"]["matched_ridge"]["holdout"]["normalized_rmse"] <= 0.15,
        "holdout_r2": search_fit["scalar_metrics"]["matched_ridge"]["holdout"]["r2"] >= 0.95,
        "holdout_pearson": search_fit["scalar_metrics"]["matched_ridge"]["holdout"]["pearson"] >= 0.975,
    }
    search_gate["pass"] = all(search_gate.values())
    search_numerical_gate = search_fit["solver"]["relative_linear_system_residual"] <= 1e-10 and search_fit["objective_excess"] <= 1e-10 and search_fit["prediction_difference_vs_matched"]["holdout"]["normalized_by_holdout_target_std"] <= 1e-8
    informative = decision["informative"] >= 32
    action = decision.get("compressed", {})
    transfer_gate = informative and action.get("top1_agreement", 0.0) >= 0.85 and action.get("pairwise_ordering_agreement", 0.0) >= 0.95 and action.get("mean_normalized_teacher_regret", float("inf")) <= 0.05 and (decision["teacher_disagreement_recovery"]["recovery"] or 0.0) >= 0.50 and (decision["teacher_correct_retention"]["retention"] or 0.0) >= 0.95
    if not direct_gate:
        classification = "F125_DIRECT_CONTROL_REGRESSION"
    elif not informative:
        classification = "F125_T1_TEACHER_INSUFFICIENTLY_INFORMATIVE"
    elif not search_numerical_gate or not search_gate["pass"]:
        classification = "HANDCRAFTED_BASIS_T1_SEARCH_TARGET_COMPRESSION_LIMIT_SUPPORTED"
    elif not transfer_gate:
        classification = "SEARCH_TARGET_FIT_TO_DECISION_TRANSFER_FAILURE_SUPPORTED"
    else:
        classification = "KNOWN_ORACLE_SEARCH_COMPRESSION_PASSES"
    return {
        "basis": {"feature_count": len(basis.names), "oracle_weight_sha256": basis.oracle_weight_sha256},
        "corpus": {"rows": len(rows), "identity_sha256": identity_hash, "retained_rows": len(retained), "retained_by_split": {key: len(value) for key, value in split_indices.items()}, "excluded_terminal_tactical": sum(label["terminal_child"] for label in labels), "excluded_shogi_declaration": sum(label["shogi_declaration"] for label in labels)},
        "direct_control": {"solver": direct_fit["solver"], "scalar_metrics": direct_fit["scalar_metrics"], "numerical_gate": direct_gate},
        "search_target": {"solver": search_fit["solver"], "scalar_metrics": search_fit["scalar_metrics"], "numerical_prediction_difference_vs_matched": search_fit["prediction_difference_vs_matched"], "objective_excess": search_fit["objective_excess"], "numerical_gate": search_numerical_gate, "representation_gate": search_gate},
        "decision_corpus": {"generated": len(fresh_roots), "retained": len(decision_records), "requested": decision_root_limit, "required_informative": 32, "root_seed": root_seed, "summary": decision},
        "classification": classification,
    }


def _selected_families(family):
    if family is None:
        return FAMILIES
    selected = [item for item in FAMILIES if item[0] == family]
    if not selected:
        raise ValueError(f"unknown F125 family: {family}")
    return selected


def run(family=None, decision_root_limit=256):
    if decision_root_limit < 1:
        raise ValueError("decision_root_limit must be positive")
    selected = _selected_families(family)
    result = {"schema": "F125_KNOWN_ORACLE_ONE_PLY_SEARCH_COMPRESSION_V1", "baseline": "23a0b78ad7f67dbe14186ea98f68c1698e3df395", "decision_root_limit": decision_root_limit, "rulesets": {name: _diagnose_family(name, corpus_seed, DECISION_ROOT_SEEDS[name], decision_root_limit) for name, corpus_seed, _, _ in selected}}
    values = [item["classification"] for item in result["rulesets"].values()]
    if len(values) == 1:
        result["classification"] = values[0]
    elif all(value == "KNOWN_ORACLE_SEARCH_COMPRESSION_PASSES" for value in values):
        result["classification"] = "KNOWN_HANDCRAFTED_ORACLE_SEARCH_TEACHER_LAYER_PASSES"
    elif any(value == "F125_DIRECT_CONTROL_REGRESSION" for value in values):
        result["classification"] = "F125_DIRECT_CONTROL_REGRESSION"
    elif all(value == "HANDCRAFTED_BASIS_T1_SEARCH_TARGET_COMPRESSION_LIMIT_SUPPORTED" for value in values):
        result["classification"] = "SEARCH_TARGET_REPRESENTATION_COMPRESSION_IS_PRIMARY"
    elif all(value == "SEARCH_TARGET_FIT_TO_DECISION_TRANSFER_FAILURE_SUPPORTED" for value in values):
        result["classification"] = "SEARCH_EVALUATOR_INTERACTION_IS_PRIMARY"
    else:
        result["classification"] = "KNOWN_ORACLE_SEARCH_COMPRESSION_RULESET_DEPENDENT"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--family", choices=[family for family, _, _, _ in FAMILIES])
    parser.add_argument("--decision-root-limit", type=int, default=256)
    args = parser.parse_args()
    started = time.time()
    result = run(args.family, args.decision_root_limit)
    result["runtime_seconds"] = time.time() - started
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"classification": result["classification"], "rulesets": {family: value["classification"] for family, value in result["rulesets"].items()}, "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))


if __name__ == "__main__":
    main()
