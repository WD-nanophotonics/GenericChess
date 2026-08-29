"""Audit one fresh V2 correction on V5 effective DEVELOPMENT orbits only."""

from __future__ import annotations

import argparse
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
from scripts import build_f23g_preference_corpus_r2 as f23g
from scripts import build_f23h_preference_corpus_r3 as f23h

V1 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v1.json"
V2 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v2.json"
V3 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v3.json"
V4 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v4.json"
V5 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v5.json"
FAMILY_NAMES = tuple(f23a.FAMILY_NAMES)
FEATURE_VERSION = "ADR-040-recomputed-child-minus-root-f23i-v1"


def _action_text(action, m):
    return json.dumps(m["action_to_dict"](action), sort_keys=True, separators=(",", ":"))


def _load_development_rows():
    fixture = json.loads(V5.read_text(encoding="utf-8"))
    eligible_ids = set(fixture["effective_orbits"]["fit_eligible_development_orbit_ids"])
    entries = {entry["id"]: entry for entry in fixture["generic_exact"] if entry.get("effective_orbit_id") in eligible_ids}
    if set(entry["effective_orbit_id"] for entry in entries.values()) != eligible_ids:
        raise RuntimeError("F23I_ELIGIBLE_ORBIT_SET_MISMATCH")
    m = f23c._imports()
    probe_m = f23a._imports()
    rows = []
    for entry in sorted(entries.values(), key=lambda item: item["effective_orbit_id"]):
        parts = entry["ruleset_id"].split("-")
        variant = int(parts[-1])
        capture = parts[1] == "capture"
        compiled, _pieces = f23g._semantic_variant(m, variant, capture=capture)
        spec = entry["state"]
        state = m["make_state"](compiled, spec["rows"], side_to_move=spec["side_to_move"], hands=spec["hands"])
        probe = f23a.Probe(compiled, probe_m)
        actor = state.position.side_to_move
        root_features, _cost, _detail = probe.feature_vector(state, actor)
        optimal = {json.dumps(action, sort_keys=True, separators=(",", ":")) for action in entry["preference_authority"]["optimal_root_actions"]}
        actions = []
        for action, child_position in probe._legal_pairs(state.position, actor):
            child = f23a._child_state(state, child_position, action, probe_m)
            child_features, _child_cost, child_detail = probe.feature_vector(child, actor)
            _components, v1_score = f23a.evaluator_components(probe, child, actor)
            action_dict = probe_m["action_to_dict"](action)
            actions.append({
                "action": action_dict,
                "action_key": _action_text(action, probe_m),
                "optimal": json.dumps(action_dict, sort_keys=True, separators=(",", ":")) in optimal,
                "v1_score": int(v1_score),
                "feature_deltas": {name: child_features[name] - root_features[name] for name in FAMILY_NAMES},
                "feature_costs": child_detail["family_seconds"],
            })
        rows.append({"id": entry["id"], "orbit_id": entry["effective_orbit_id"], "ruleset_id": entry["ruleset_id"], "mechanic_family": entry["mechanic_family"], "actions": actions})
    if len(rows) != len(eligible_ids):
        raise RuntimeError("F23I_DEVELOPMENT_ROW_COUNT_MISMATCH")
    return rows, sorted(eligible_ids)


def _normalizers(rows, features):
    result = {}
    for name in features:
        values = [action["feature_deltas"][name] for row in rows for action in row["actions"]]
        center = median(values) if values else 0.0
        deviations = [abs(value - center) for value in values]
        result[name] = {"center": center, "scale": max(median(deviations) * 1.4826 if deviations else 0.0, 1e-6)}
    return result


def _score(action, coeffs, normalizers, features, clip=2.0):
    correction = sum(coeffs[name] * ((action["feature_deltas"][name] - normalizers[name]["center"]) / normalizers[name]["scale"]) for name in features)
    return action["v1_score"] + max(-clip, min(clip, correction))


def _pairs(rows):
    groups = defaultdict(list)
    for row in rows:
        optimal = [action for action in row["actions"] if action["optimal"]]
        inferior = [action for action in row["actions"] if not action["optimal"]]
        for win in optimal:
            for loss in inferior:
                groups[row["ruleset_id"]].append((win, loss))
    deduped = {}
    for ruleset, pairs in groups.items():
        unique = {}
        for win, loss in pairs:
            signature = (tuple(sorted(win["feature_deltas"].items())), tuple(sorted(loss["feature_deltas"].items())))
            unique[signature] = (win, loss)
        deduped[ruleset] = list(unique.values())
    return groups, deduped


def _metrics(rows, coeffs, normalizers, features, clip=2.0):
    groups, deduped = _pairs(rows)
    by_ruleset = {}
    raw_correct = raw_total = dedup_correct = dedup_total = 0
    ranks = []
    top1 = []
    violations = 0
    for ruleset, pairs in groups.items():
        correct = sum(_score(win, coeffs, normalizers, features, clip) > _score(loss, coeffs, normalizers, features, clip) for win, loss in pairs)
        unique = deduped[ruleset]
        unique_correct = sum(_score(win, coeffs, normalizers, features, clip) > _score(loss, coeffs, normalizers, features, clip) for win, loss in unique)
        raw_correct += correct; raw_total += len(pairs); dedup_correct += unique_correct; dedup_total += len(unique)
        by_ruleset[ruleset] = {"dedup_correct": unique_correct, "dedup_total": len(unique)}
    for row in rows:
        ordered = sorted(row["actions"], key=lambda action: (-_score(action, coeffs, normalizers, features, clip), action["action_key"]))
        best = min((index + 1 for index, action in enumerate(ordered) if action["optimal"]), default=None)
        if best is not None:
            ranks.append(best); top1.append(best == 1)
        optimal_scores = [_score(action, coeffs, normalizers, features, clip) for action in row["actions"] if action["optimal"]]
        inferior_scores = [_score(action, coeffs, normalizers, features, clip) for action in row["actions"] if not action["optimal"]]
        if optimal_scores and inferior_scores and max(inferior_scores) >= max(optimal_scores):
            violations += 1
    macro = mean(value["dedup_correct"] / value["dedup_total"] for value in by_ruleset.values() if value["dedup_total"]) if by_ruleset else 0.0
    return {"raw_pairwise_accuracy": raw_correct / raw_total if raw_total else 0.0, "dedup_pairwise_accuracy": dedup_correct / dedup_total if dedup_total else 0.0, "macro_equal_ruleset_pairwise_accuracy": macro, "raw_constraints": raw_total, "dedup_constraints": dedup_total, "exact_optimal_set_top1": sum(top1), "exact_optimal_set_roots": len(top1), "best_optimal_rank_mean": mean(ranks) if ranks else None, "best_optimal_rank_median": median(ranks) if ranks else None, "inferior_draw_outranks_all_wins": violations, "by_ruleset": by_ruleset}


def _select_features(rows):
    by_ruleset = defaultdict(list); by_mechanic = defaultdict(list)
    for row in rows:
        by_ruleset[row["ruleset_id"]].append(row); by_mechanic[row["mechanic_family"]].append(row)
    candidates = []
    for name in FAMILY_NAMES:
        group_margins = {}
        for group, group_rows in sorted(by_ruleset.items()):
            pairs, _ = _pairs(group_rows); flat = [pair for pairs_for_group in pairs.values() for pair in pairs_for_group]
            group_margins[group] = mean(win["feature_deltas"][name] - loss["feature_deltas"][name] for win, loss in flat) if flat else 0.0
        mechanic_margins = {}
        for group, group_rows in sorted(by_mechanic.items()):
            pairs, _ = _pairs(group_rows); flat = [pair for pairs_for_group in pairs.values() for pair in pairs_for_group]
            mechanic_margins[group] = mean(win["feature_deltas"][name] - loss["feature_deltas"][name] for win, loss in flat) if flat else 0.0
        nonzero_rulesets = sum(value != 0 for value in group_margins.values())
        nonzero_mechanics = sum(value != 0 for value in mechanic_margins.values())
        if nonzero_rulesets >= 2 and nonzero_mechanics >= 2:
            candidates.append((sum(abs(value) for value in group_margins.values()), name, group_margins, mechanic_margins))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    selected = [item[1] for item in candidates[:4]]
    return {"selected": selected, "candidates": [{"family": name, "absolute_ruleset_margin": score, "ruleset_margins": margins, "mechanic_margins": mechanic} for score, name, margins, mechanic in candidates], "excluded": {name: "not in deterministic grouped top-four" for name in FAMILY_NAMES if name not in selected}}


def _fit(rows, features):
    normalizers = _normalizers(rows, features)
    best = None
    for values in itertools.product((-2, -1, 0, 1, 2), repeat=len(features)):
        coeffs = dict(zip(features, values)); metrics = _metrics(rows, coeffs, normalizers, features)
        objective = (metrics["macro_equal_ruleset_pairwise_accuracy"], metrics["dedup_pairwise_accuracy"], -sum(abs(value) for value in values), tuple(-value for value in values))
        if best is None or objective > best[0]: best = (objective, coeffs, metrics)
    return {"coefficients": best[1], "normalizers": normalizers, "clip": 2.0, "metrics": best[2]}


def _base_metrics(rows):
    return _metrics(rows, {}, {}, (), 0.0)


def _candidate_spec(fit, features, rows, loo, transfer):
    spec = {"status": "FROZEN_DEVELOPMENT_CANDIDATE", "base": {"name": "evaluator-v1", "feature_definition_version": FEATURE_VERSION}, "features": features, "normalizers": fit["normalizers"], "coefficients": fit["coefficients"], "correction_clip": fit["clip"], "development_orbit_ids": sorted(row["orbit_id"] for row in rows), "development_ruleset_groups": sorted({row["ruleset_id"] for row in rows}), "mechanic_families": sorted({row["mechanic_family"] for row in rows}), "weighting": "equal effective decision orbit", "fit_algorithm": "bounded_grid_coefficients_-2_to_2_f23i_v1", "loo_summary": loo, "mechanic_transfer": transfer, "source_fixture_sha256": {"v1": hashlib.sha256(V1.read_bytes()).hexdigest(), "v2": hashlib.sha256(V2.read_bytes()).hexdigest(), "v3": hashlib.sha256(V3.read_bytes()).hexdigest(), "v4": hashlib.sha256(V4.read_bytes()).hexdigest(), "v5": hashlib.sha256(V5.read_bytes()).hexdigest()}}
    encoded = json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return spec, hashlib.sha256(encoded).hexdigest()


@lru_cache(maxsize=1)
def audit_development():
    rows, eligible_ids = _load_development_rows()
    selection = _select_features(rows)
    features = selection["selected"]
    v1 = _base_metrics(rows)
    loo = {}; folds_improved = 0; no_material_regression = True
    for omitted in sorted({row["ruleset_id"] for row in rows}):
        train = [row for row in rows if row["ruleset_id"] != omitted]; test = [row for row in rows if row["ruleset_id"] == omitted]
        fold_selection = _select_features(train); fold_features = fold_selection["selected"]
        fit = _fit(train, fold_features); base = _base_metrics(test); candidate = _metrics(test, fit["coefficients"], fit["normalizers"], fold_features, fit["clip"])
        improved = candidate["dedup_pairwise_accuracy"] > base["dedup_pairwise_accuracy"]
        folds_improved += improved; no_material_regression &= candidate["dedup_pairwise_accuracy"] + 0.25 >= base["dedup_pairwise_accuracy"]
        loo[omitted] = {"train_rulesets": sorted({row["ruleset_id"] for row in train}), "selected_features": fold_features, "v1": base, "candidate": candidate, "improved": improved}
    transfer = {}
    families = sorted({row["mechanic_family"] for row in rows})
    transfer_improved = 0; transfer_no_catastrophe = True
    for held_out in families:
        train = [row for row in rows if row["mechanic_family"] != held_out]; test = [row for row in rows if row["mechanic_family"] == held_out]
        fold_selection = _select_features(train); fold_features = fold_selection["selected"]; fit = _fit(train, fold_features)
        base = _base_metrics(test); candidate = _metrics(test, fit["coefficients"], fit["normalizers"], fold_features, fit["clip"])
        improved = candidate["dedup_pairwise_accuracy"] > base["dedup_pairwise_accuracy"]; transfer_improved += improved; transfer_no_catastrophe &= candidate["dedup_pairwise_accuracy"] + 0.25 >= base["dedup_pairwise_accuracy"]
        transfer[held_out] = {"train_mechanics": sorted({row["mechanic_family"] for row in train}), "selected_features": fold_features, "v1": base, "candidate": candidate, "improved": improved}
    fit = _fit(rows, features)
    advancement = bool(features) and folds_improved >= 4 and no_material_regression and transfer_improved >= 1 and transfer_no_catastrophe and fit["metrics"]["macro_equal_ruleset_pairwise_accuracy"] > v1["macro_equal_ruleset_pairwise_accuracy"] and fit["metrics"]["inferior_draw_outranks_all_wins"] <= v1["inferior_draw_outranks_all_wins"]
    costs = {name: median(action["feature_costs"][name] for row in rows for action in row["actions"]) for name in features}
    candidate_spec = None; candidate_sha = None
    if advancement:
        candidate_spec, candidate_sha = _candidate_spec(fit, features, rows, loo, transfer)
    return {"status": "PASS", "phase": "F23I_DEVELOPMENT_BEFORE_HOLDOUT", "development_orbits": len(rows), "eligible_orbit_ids": eligible_ids, "feature_selection": selection, "v1_metrics": v1, "candidate_metrics": fit["metrics"], "loo": loo, "folds_improved": folds_improved, "mechanic_transfer": transfer, "transfer_improved": transfer_improved, "candidate_spec": candidate_spec, "candidate_spec_sha256": candidate_sha, "advancement_gate_passed": advancement, "runtime_cost": {"median_feature_seconds": costs, "median_incremental_feature_seconds": sum(costs.values())}, "holdout_opened": False, "shogi_opened": False, "decision": {"selected_next_boundary": "F23J_SEMANTIC_FEATURE_API_FOUNDATION" if advancement else "F23J_REFERENCE_PREFERENCE_CORPUS_R4", "reason": "fresh grouped LOO and mechanic transfer decision"}}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--candidate-spec", type=Path); args = parser.parse_args()
    report = audit_development(); args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.candidate_spec and report["candidate_spec"] is not None:
        args.candidate_spec.write_text(json.dumps({"candidate_spec_sha256": report["candidate_spec_sha256"], "candidate_spec": report["candidate_spec"]}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "development": report["development_orbits"], "features": report["feature_selection"]["selected"], "folds_improved": report["folds_improved"], "transfer_improved": report["transfer_improved"], "advancement": report["advancement_gate_passed"], "selected": report["decision"]["selected_next_boundary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
