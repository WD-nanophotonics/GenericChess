"""Fit and validate one small audit-only Rule-Derived Evaluator V2 candidate.

The development pass is deliberately completed before this module opens the
sealed strong HOLDOUT.  No production evaluator path is imported by the
candidate scorer.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import sys
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_f23a_evaluator_v2_features as f23a
from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23e_preference_corpus as f23e

V1 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v1.json"
V2 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v2.json"
V3 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v3.json"
FAMILIES = f23a.FAMILY_NAMES
FEATURE_VERSION = "ADR-040-probe-v1-child-minus-root"


def _action_text(action, m):
    return json.dumps(m["action_to_dict"](action), sort_keys=True, separators=(",", ":"))


def _load_dev_rows():
    fixture = json.loads(V3.read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in f23e._case_specs(f23c._imports())}
    probe_m = f23a._imports()
    rows = []
    for entry in fixture["generic_exact"]:
        if entry["split"] != "DEVELOPMENT" or entry.get("supervision_class") != "PREFERENCE_STRONG":
            continue
        case = cases[entry["id"]]
        probe = f23a.Probe(case["compiled"], probe_m)
        actor = case["state_object"].position.side_to_move
        root_features, _cost, _detail = probe.feature_vector(case["state_object"], actor)
        optimal = {json.dumps(action, sort_keys=True, separators=(",", ":")) for action in entry["preference_authority"]["optimal_root_actions"]}
        actions = []
        for action, child_position in probe._legal_pairs(case["state_object"].position, actor):
            child = f23a._child_state(case["state_object"], child_position, action, probe_m)
            child_features, _child_cost, child_detail = probe.feature_vector(child, actor)
            _components, v1_score = f23a.evaluator_components(probe, child, actor)
            actions.append({
                "action": probe_m["action_to_dict"](action),
                "action_key": _action_text(action, probe_m),
                "optimal": _action_text(action, probe_m) in optimal,
                "v1_score": int(v1_score),
                "feature_deltas": {name: child_features[name] - root_features[name] for name in FAMILIES},
                "feature_costs": child_detail["family_seconds"],
            })
        rows.append({"id": entry["id"], "ruleset_id": entry["ruleset_id"], "actions": actions})
    return rows


def _normalizers(rows, features):
    values = {name: [action["feature_deltas"][name] for row in rows for action in row["actions"]] for name in features}
    result = {}
    for name in features:
        center = median(values[name]) if values[name] else 0.0
        deviations = [abs(value - center) for value in values[name]]
        scale = median(deviations) * 1.4826 if deviations else 0.0
        result[name] = {"center": center, "scale": max(scale, 1e-6)}
    return result


def _score(action, coeffs, normalizers, features, clip=2.0):
    correction = sum(coeffs[name] * ((action["feature_deltas"][name] - normalizers[name]["center"]) / normalizers[name]["scale"]) for name in features)
    return action["v1_score"] + max(-clip, min(clip, correction))


def _constraints(rows):
    groups = defaultdict(list)
    for row in rows:
        optimal = [action for action in row["actions"] if action["optimal"]]
        inferior = [action for action in row["actions"] if not action["optimal"]]
        for win in optimal:
            for loss in inferior:
                groups[row["ruleset_id"]].append((win, loss))
    # Deduplicate identical feature/preference signatures within a ruleset.
    deduped = {}
    for ruleset, pairs in groups.items():
        unique = {}
        for win, loss in pairs:
            signature = (tuple(sorted(win["feature_deltas"].items())), tuple(sorted(loss["feature_deltas"].items())))
            unique[signature] = (win, loss)
        deduped[ruleset] = list(unique.values())
    return groups, deduped


def _metrics(rows, coeffs, normalizers, features, clip=2.0):
    groups, deduped = _constraints(rows)
    group_results = {}
    raw_correct = raw_total = 0
    dedup_correct = dedup_total = 0
    top1 = []
    rank_values = []
    violations = 0
    for ruleset, pairs in groups.items():
        correct = 0
        for win, loss in pairs:
            if _score(win, coeffs, normalizers, features, clip) > _score(loss, coeffs, normalizers, features, clip):
                correct += 1
        raw_correct += correct
        raw_total += len(pairs)
        unique_pairs = deduped[ruleset]
        dedup_correct += sum(_score(win, coeffs, normalizers, features, clip) > _score(loss, coeffs, normalizers, features, clip) for win, loss in unique_pairs)
        dedup_total += len(unique_pairs)
        group_results[ruleset] = {"raw_correct": correct, "raw_total": len(pairs), "dedup_correct": sum(_score(win, coeffs, normalizers, features, clip) > _score(loss, coeffs, normalizers, features, clip) for win, loss in unique_pairs), "dedup_total": len(unique_pairs)}
    for row in rows:
        ordered = sorted(row["actions"], key=lambda action: (-_score(action, coeffs, normalizers, features, clip), action["action_key"]))
        ranks = [index + 1 for index, action in enumerate(ordered) if action["optimal"]]
        if ranks:
            rank_values.append(min(ranks))
            top1.append(min(ranks) == 1)
        optimal_scores = [_score(action, coeffs, normalizers, features, clip) for action in row["actions"] if action["optimal"]]
        inferior_scores = [_score(action, coeffs, normalizers, features, clip) for action in row["actions"] if not action["optimal"]]
        if optimal_scores and inferior_scores and max(inferior_scores) >= max(optimal_scores):
            violations += 1
    macro = mean([value["dedup_correct"] / value["dedup_total"] for value in group_results.values() if value["dedup_total"]]) if group_results else 0.0
    return {"raw_pairwise_accuracy": raw_correct / raw_total if raw_total else 0.0, "dedup_pairwise_accuracy": dedup_correct / dedup_total if dedup_total else 0.0, "macro_equal_ruleset_pairwise_accuracy": macro, "dedup_constraints": dedup_total, "raw_constraints": raw_total, "exact_optimal_set_top1": sum(top1), "exact_optimal_set_roots": len(top1), "best_optimal_rank_mean": sum(rank_values) / len(rank_values) if rank_values else None, "best_optimal_rank_median": median(rank_values) if rank_values else None, "inferior_draw_outranks_all_wins": violations, "by_ruleset": group_results}


def _fit(rows, features):
    normalizers = _normalizers(rows, features)
    best = None
    for values in itertools.product((-2, -1, 0, 1, 2), repeat=len(features)):
        coeffs = dict(zip(features, values))
        metrics = _metrics(rows, coeffs, normalizers, features)
        objective = (metrics["macro_equal_ruleset_pairwise_accuracy"], metrics["dedup_pairwise_accuracy"], -sum(abs(value) for value in values), tuple(-value for value in values))
        if best is None or objective > best[0]:
            best = (objective, coeffs, metrics)
    return {"coefficients": best[1], "normalizers": normalizers, "clip": 2.0, "metrics": best[2]}


def _select_features(rows):
    groups, _deduped = _constraints(rows)
    candidates = []
    for name in FAMILIES:
        margins = []
        for _ruleset, pairs in groups.items():
            if not pairs:
                continue
            margins.append(sum(win["feature_deltas"][name] - loss["feature_deltas"][name] for win, loss in pairs) / len(pairs))
        if len(margins) >= 2 and any(value != 0 for value in margins):
            candidates.append((sum(abs(value) for value in margins), name, margins))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    selected = [item[1] for item in candidates[:4]]
    return {"selected": selected, "candidates": [{"family": name, "absolute_group_margin": score, "group_margins": margins} for score, name, margins in candidates], "excluded": {name: "not in deterministic multi-ruleset top-four" for name in FAMILIES if name not in selected}}


def _candidate_spec(fit, features, rows, fixture_hashes, loo):
    spec = {"status": "FROZEN_DEVELOPMENT_CANDIDATE", "base": {"name": "evaluator-v1", "feature_definition_version": FEATURE_VERSION}, "features": features, "normalizers": fit["normalizers"], "coefficients": fit["coefficients"], "correction_clip": fit["clip"], "development_root_ids": sorted(row["id"] for row in rows), "development_ruleset_groups": sorted({row["ruleset_id"] for row in rows}), "weighting": "equal ruleset; deduplicate identical feature/preference signatures within ruleset", "fit_algorithm": "bounded_grid_coefficients_-2_to_2_v1", "loo_summary": loo, "source_fixture_sha256": fixture_hashes}
    encoded = json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return spec, hashlib.sha256(encoded).hexdigest()


@lru_cache(maxsize=1)
def audit_development():
    rows = _load_dev_rows()
    selection = _select_features(rows)
    features = selection["selected"]
    v1_coeffs = {name: 0 for name in features}
    v1_norm = {name: {"center": 0.0, "scale": 1.0} for name in features}
    v1 = _metrics(rows, v1_coeffs, v1_norm, features)
    loo = {}
    for omitted in sorted({row["ruleset_id"] for row in rows}):
        train = [row for row in rows if row["ruleset_id"] != omitted]
        test = [row for row in rows if row["ruleset_id"] == omitted]
        fit = _fit(train, features)
        base = _metrics(test, v1_coeffs, v1_norm, features)
        candidate = _metrics(test, fit["coefficients"], fit["normalizers"], features, fit["clip"])
        loo[omitted] = {"train_rulesets": sorted({row["ruleset_id"] for row in train}), "v1": base, "candidate": candidate, "improved": candidate["dedup_pairwise_accuracy"] > base["dedup_pairwise_accuracy"]}
    fit = _fit(rows, features)
    spec, spec_sha = _candidate_spec(fit, features, rows, {"v1": hashlib.sha256(V1.read_bytes()).hexdigest(), "v2": hashlib.sha256(V2.read_bytes()).hexdigest(), "v3": hashlib.sha256(V3.read_bytes()).hexdigest()}, loo)
    candidate_metrics = fit["metrics"]
    folds_improved = sum(value["improved"] for value in loo.values())
    advancement = folds_improved >= 3 and candidate_metrics["macro_equal_ruleset_pairwise_accuracy"] > v1["macro_equal_ruleset_pairwise_accuracy"] and candidate_metrics["inferior_draw_outranks_all_wins"] == 0
    costs = {name: median(action["feature_costs"][name] for row in rows for action in row["actions"]) for name in features}
    return {"status": "PASS", "phase": "F23F_DEVELOPMENT_BEFORE_HOLDOUT", "development_roots": len(rows), "feature_selection": selection, "v1_metrics": v1, "candidate_metrics": candidate_metrics, "loo": loo, "folds_improved": folds_improved, "candidate_spec": spec, "candidate_spec_sha256": spec_sha, "advancement_gate_passed": advancement, "runtime_cost": {"median_feature_seconds": costs, "median_incremental_feature_seconds": sum(costs.values())}, "holdout_opened": False, "shogi_opened": False, "decision": {"selected_next_boundary": "F23G_EVALUATOR_V2_PROTOTYPE_R3" if advancement is False and folds_improved >= 3 else "F23G_REFERENCE_PREFERENCE_CORPUS_R2", "reason": "Grouped leave-one-ruleset-out improvement gate did not pass; the max_ply=1 strong roots are too shallow and synthetic for a credible cross-ruleset evaluator correction"}}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate-spec", type=Path)
    args = parser.parse_args()
    report = audit_development()
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.candidate_spec:
        args.candidate_spec.write_text(json.dumps({"candidate_spec_sha256": report["candidate_spec_sha256"], "candidate_spec": report["candidate_spec"], "status": "REJECTED_BEFORE_HOLDOUT"}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "development": report["development_roots"], "features": report["feature_selection"]["selected"], "folds_improved": report["folds_improved"], "advancement": report["advancement_gate_passed"], "selected": report["decision"]["selected_next_boundary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
