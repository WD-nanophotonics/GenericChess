"""F60 disjoint policy-objective and state-distribution validation.

F60 keeps the F59 evaluator/search implementation frozen and constructs fresh,
fully disjoint Shogi data for a three-way fit/selection/final-holdout matrix.
The F59 action-spectrum helpers are reused only for the frozen search and
fixed representation; no F59 roots are loaded or used as examples.
"""

from __future__ import annotations

import argparse
import json
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    from scripts import f59_action_spectrum_diagnosis as f59
except ModuleNotFoundError:  # direct ``python scripts/...`` entry point
    import f59_action_spectrum_diagnosis as f59
from generic_chess.learning.diagnostics import generate_diagnostic_corpus
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.selfplay import SelfPlayConfig, collect_self_play
from generic_chess.learning.serialization import stable_sha256


OUT = ROOT / ".generic_chess_flow" / "f60-disjoint-policy-validation"
LABEL = "B_CANONICAL_STANDARD_SHOGI"
ROOT_COUNT = 96
FIT_COUNT = 48
DEV_COUNT = 24
FINAL_COUNT = 24
SPLIT_ENDS = (FIT_COUNT, FIT_COUNT + DEV_COUNT, ROOT_COUNT)
F60_SELFPLAY_GAMES = 12
F60_PV_NODES = 10_000
MATERIAL_IMPROVEMENT = 0.10
TRAINING_DISTRIBUTIONS = ("D0_RANDOM_REACHABLE", "D1_V2_SELFPLAY", "D2_V2_PV_CORRIDOR", "D12_D1_D2_MIX")
OBJECTIVES = ("POINTWISE_Q", "PAIRWISE_RANKING", "SOFT_POLICY_DISTILLATION")


def _json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def _record_keys(records):
    return {record["position_key"] for record in records}


def _with_source_group(record, source_group):
    result = dict(record)
    result["source_group"] = str(source_group)
    return result


def _take_unique(records, forbidden, count):
    selected = []
    seen = set(forbidden)
    for record in records:
        key = record["position_key"]
        if key in seen:
            continue
        selected.append(record)
        seen.add(key)
        if len(selected) >= count:
            return selected
    raise ValueError(f"fresh disjoint pool supplied only {len(selected)} of {count} roots")


def _unique_pool(records, forbidden):
    selected = []
    seen = set(forbidden)
    for record in records:
        key = record["position_key"]
        if key not in seen:
            selected.append(record)
            seen.add(key)
    return selected


def _partition_by_source_group(records, targets):
    groups = {}
    for record in records:
        groups.setdefault(record["source_group"], []).append(record)
    group_values = list(groups.values())
    parts = []
    cursor = 0
    for target in targets:
        part = []
        while cursor < len(group_values) and len(part) < target:
            part.extend(group_values[cursor])
            cursor += 1
        if len(part) < target:
            raise ValueError(f"source-group pool supplied only {len(part)} of target {target}")
        parts.append(part)
    return parts


def _source_group_overlap(distributions):
    names = tuple(distributions)
    return {
        f"{left}|{left_split}": {
            f"{right}|{right_split}": len(
                {r["source_group"] for r in distributions[left][left_split]}
                & {r["source_group"] for r in distributions[right][right_split]}
            )
            for right in names for right_split in ("fit", "development", "final_holdout")
        }
        for left in names for left_split in ("fit", "development", "final_holdout")
    }


def _flatten_split_parts(parts):
    return [dict(record, source_split=split)
            for split, part in zip(("fit", "development", "final_holdout"), parts)
            for record in part]


def _trajectory_records(compiled, trajectories, prefix):
    records = []
    seen = set()
    for trajectory_index, trajectory in enumerate(trajectories):
        actions = tuple(trajectory.actions)
        for point in trajectory.points:
            if point.ply >= len(actions):
                continue
            record = f59._record_from_actions(compiled, actions[:point.ply])
            if record is not None and record["position_key"] not in seen:
                seen.add(record["position_key"])
                records.append(_with_source_group(record, f"{prefix}_TRAJECTORY_{trajectory_index}"))
    return records


def _fresh_selfplay(compiled, native, parent, seed, root_count, smoke=False):
    trajectories = collect_self_play(
        compiled, native, parent,
        SelfPlayConfig(games=4 if smoke else F60_SELFPLAY_GAMES,
                       nodes_per_move=50 if smoke else 2_000,
                       max_depth=12, seed=seed, epsilon=0.10,
                       tt_megabytes=8, max_plies=4 if smoke else f59.SELFPLAY_MAX_PLIES),
    )
    records = _trajectory_records(compiled, trajectories, "D1" if seed % 2 == 0 else "D2")
    return records, stable_sha256({
        "seed": seed,
        "trajectories": [list(map(f59.action_to_dict, trajectory.actions)) for trajectory in trajectories],
    })


def _fresh_distributions(compiled, native, parent, root_count, smoke=False):
    seed = f59.SEEDS[LABEL] + (600 if not smoke else 60_000)
    corpus_count = root_count * 2
    openings = generate_arena_openings(compiled, count=corpus_count, seed=seed,
                                       min_plies=2, max_plies=6)
    corpus = generate_diagnostic_corpus(compiled, openings, count=corpus_count,
                                        seed=seed + 1, min_plies=8, max_plies=40)
    d0_pool = [_with_source_group(f59._record_dict(position), f"D0_OPENING_{position.index}")
               for position in corpus.positions]
    targets = (1, 1, 1) if smoke else (FIT_COUNT, DEV_COUNT, FINAL_COUNT)
    d0_parts = _partition_by_source_group(d0_pool, targets)
    d0 = _flatten_split_parts(d0_parts)
    d0_keys = _record_keys(d0)

    d1_pool, d1_source_id = _fresh_selfplay(compiled, native, parent, seed + 2, root_count, smoke=smoke)
    d1_pool = _unique_pool(d1_pool, d0_keys)
    d1_parts = _partition_by_source_group(d1_pool, targets)
    d1 = _flatten_split_parts(d1_parts)
    used = d0_keys | _record_keys(d1)

    # D2 has an independent self-play trajectory pool and never uses D1 roots.
    d2_pool, d2_source_id = _fresh_selfplay(compiled, native, parent, seed + 3, root_count, smoke=smoke)
    d2_base = _unique_pool(d2_pool, used)[: (root_count * 2)]
    d2_roots = f59._parallel_root(compiled, native, parent, d2_base, F60_PV_NODES)
    d2_candidates = []
    for base_index, (record, root) in enumerate(zip(d2_base, d2_roots)):
        history = [f59.action_from_dict(item) for item in record["action_history"]]
        selected = None
        for payload in root["pv"]:
            history.append(f59.action_from_dict(payload))
            candidate = f59._record_from_actions(compiled, history)
            if candidate is not None:
                selected = _with_source_group(candidate, f"D2_BASE_ROOT_{base_index}")
                break
        if selected is not None:
            d2_candidates.append(selected)
    d2_parts = _partition_by_source_group(_unique_pool(d2_candidates, used), targets)
    d2 = _flatten_split_parts(d2_parts)
    distributions = {
        "D0_RANDOM_REACHABLE": d0,
        "D1_V2_SELFPLAY": d1,
        "D2_V2_PV_CORRIDOR": d2,
    }
    source_ids = {
        "D0_RANDOM_REACHABLE": stable_sha256(corpus.to_dict()),
        "D1_V2_SELFPLAY": d1_source_id,
        "D2_V2_PV_CORRIDOR": stable_sha256({"trajectory_pool": d2_source_id,
                                               "base_root_keys": [r["position_key"] for r in d2_base]}),
    }
    overlap = {left: {right: len(_record_keys(distributions[left]) & _record_keys(distributions[right]))
                      for right in distributions} for left in distributions}
    if any(overlap[left][right] for left in distributions for right in distributions if left != right):
        raise AssertionError(f"F60 distributions overlap: {overlap}")
    split_records = {name: {split: part for split, part in zip(("fit", "development", "final_holdout"), parts)}
                     for name, parts in (("D0_RANDOM_REACHABLE", d0_parts),
                                         ("D1_V2_SELFPLAY", d1_parts),
                                         ("D2_V2_PV_CORRIDOR", d2_parts))}
    source_group_overlap = _source_group_overlap(split_records)
    if any(value for left, values in source_group_overlap.items() for right, value in values.items()
           if value and left != right):
        raise AssertionError(f"F60 source groups cross splits: {source_group_overlap}")
    return distributions, {"source_ids": source_ids, "overlap_matrix": overlap,
                            "source_group_overlap_matrix": source_group_overlap,
                            "pool_sizes": {name: len(records) for name, records in distributions.items()},
                            "split_sizes": {name: [len(part) for part in parts]
                                            for name, parts in (("D0_RANDOM_REACHABLE", d0_parts),
                                                                ("D1_V2_SELFPLAY", d1_parts),
                                                                ("D2_V2_PV_CORRIDOR", d2_parts))},
                            "d2_independent_from_d1": True}


def _compute_spectra(records_by_distribution, smoke=False):
    computed = {}
    workers = min(8, max(1, __import__("os").cpu_count() or 1))
    for name, records in records_by_distribution.items():
        with ProcessPoolExecutor(max_workers=workers, initializer=f59._init_root_worker,
                                 initargs=(LABEL, smoke)) as pool:
            computed[name] = list(pool.map(f59._spectrum_root_worker, records))
    return computed


def _rows_from_meta(root_meta):
    return [f59.SpectrumRow(item["action"], item["action_key"],
                            np.asarray(item["features"], dtype=float), item["base_q"],
                            item["q_1k"], item["q_10k"], item["q_20k"])
            for item in root_meta["action_rows"]]


def _summarize_spectrum(records, computed, split_ends=SPLIT_ENDS):
    metadata = []
    roots = []
    for index, (rows, root_meta) in enumerate(computed):
        roots.append(rows)
        metadata.append({"index": index, "position_key": records[index]["position_key"], "root": root_meta})
    stable = [m["root"]["spectrum_top_10k_action_key"] == m["root"]["spectrum_top_20k_action_key"] for m in metadata]
    stable_indices = [i for i, value in enumerate(stable) if value]
    ordinary = [i for i in stable_indices if f59._ordinary_usable(metadata[i]["root"])]
    split = {part: [i for i in ordinary if records[i].get("source_split") == part]
             for part in ("fit", "development", "final_holdout")}
    mate_counts = {
        "root_80k_mate_band_roots": sum(m["root"]["root_80k_mate_band"] for m in metadata),
        "retained_q20_mate_band_roots": sum(m["root"]["retained_q20_any_mate_band"] for m in metadata),
        "retained_q20_mate_band_actions": int(sum(m["root"]["retained_q20_mate_band_action_count"] for m in metadata)),
    }
    return {"roots": roots, "roots_metadata": metadata, "stable_indices": stable_indices,
            "ordinary_usable_indices": ordinary, "split_indices": split,
            "stable_count": len(stable_indices), "stable_rate": len(stable_indices) / len(records),
            "mate_band_counts": mate_counts,
            "teacher_action_spectrum": {
                "top1_10k_vs_20k": float(np.mean(stable)),
                "root_40k_vs_80k_agreement": float(np.mean([
                    m["root"]["root_40k"]["action_key"] == m["root"]["root_80k"]["action_key"] for m in metadata
                ])),
                "candidate_count_mean": float(np.mean([len(rows) for rows in roots])),
                "legal_action_count_mean": float(np.mean([m["root"]["legal_action_count"] for m in metadata])),
            }}


def _train_rows(summary, indices):
    rows = [summary["roots"][i] for i in indices]
    features = np.vstack([row.features for root in rows for row in root])
    base = np.asarray([row.base_q for root in rows for row in root])
    targets = np.asarray([row.q_20k for root in rows for row in root])
    groups = []
    cursor = 0
    for root in rows:
        groups.append(np.arange(cursor, cursor + len(root)))
        cursor += len(root)
    return rows, features, base, targets, groups


def _metrics_with_normalized_regret(root_rows, predicted):
    metrics = f59._metrics(root_rows, predicted)
    normalized = []
    for root, values in zip(root_rows, predicted):
        teacher = np.asarray([row.q_20k for row in root], dtype=float)
        span = max(float(np.max(teacher) - np.min(teacher)), 1.0)
        normalized.append(float(np.max(teacher) - teacher[int(np.argmax(values))]) / span)
    metrics["normalized_regret_mean"] = float(np.mean(normalized)) if normalized else 0.0
    return metrics


def _evaluate_model(model, summary, indices):
    roots = [summary["roots"][i] for i in indices]
    return _metrics_with_normalized_regret(roots, [f59._predict_total_q(root, model) for root in roots])


def _aggregate_policy(metrics_by_distribution):
    selected = [metrics_by_distribution[name] for name in ("D1_V2_SELFPLAY", "D2_V2_PV_CORRIDOR")]
    return {"normalized_regret_mean": float(np.mean([m["normalized_regret_mean"] for m in selected])),
            "top1_agreement": float(np.mean([m["top1_agreement"] for m in selected])),
            "ranking_accuracy": float(np.mean([m["ranking_accuracy"] for m in selected]))}


def _objective_classification(final, train_distributions):
    evidence = []
    for train_name in train_distributions:
        pointwise = {name: [final[(train_name, "POINTWISE_Q", seed)][name]
                            for seed in f59.TRAINING_SEEDS]
                     for name in ("D1_V2_SELFPLAY", "D2_V2_PV_CORRIDOR")}
        for objective in ("PAIRWISE_RANKING", "SOFT_POLICY_DISTILLATION"):
            per_distribution = {}
            supported = True
            for name in pointwise:
                candidate = [final[(train_name, objective, seed)][name]
                             for seed in f59.TRAINING_SEEDS]
                regret_wins = sum(c["normalized_regret_mean"] <= p["normalized_regret_mean"]
                                  for c, p in zip(candidate, pointwise[name]))
                metric_improves = (np.mean([c["top1_agreement"] for c in candidate])
                                   >= np.mean([p["top1_agreement"] for p in pointwise[name]])
                                   or np.mean([c["ranking_accuracy"] for c in candidate])
                                   >= np.mean([p["ranking_accuracy"] for p in pointwise[name]]))
                regret_improves = np.mean([c["normalized_regret_mean"] for c in candidate]) \
                    < np.mean([p["normalized_regret_mean"] for p in pointwise[name]])
                per_distribution[name] = {"regret_wins_of_three": regret_wins,
                                          "regret_improves": regret_improves,
                                          "policy_metric_improves": metric_improves}
                supported = supported and regret_wins >= 2 and regret_improves and metric_improves
            evidence.append({"training_distribution": train_name, "objective": objective,
                             "per_distribution": per_distribution, "supported": supported})
    supported = any(item["supported"] for item in evidence)
    return ("POLICY_OBJECTIVE_MISMATCH_SUPPORTED" if supported
            else "LEARNING_OBJECTIVE_MISMATCH_UNRESOLVED"), evidence


def _distribution_classification(final):
    evidence = []
    for objective in OBJECTIVES:
        for learner_distribution in ("D1_V2_SELFPLAY", "D2_V2_PV_CORRIDOR", "D12_D1_D2_MIX"):
            per_distribution = {}
            supported = True
            for eval_name in ("D1_V2_SELFPLAY", "D2_V2_PV_CORRIDOR"):
                reference = [final[("D0_RANDOM_REACHABLE", objective, seed)][eval_name]
                             for seed in f59.TRAINING_SEEDS]
                learner = [final[(learner_distribution, objective, seed)][eval_name]
                           for seed in f59.TRAINING_SEEDS]
                regret_wins = sum(l["normalized_regret_mean"] < r["normalized_regret_mean"]
                                  for l, r in zip(learner, reference))
                regret_improves = np.mean([l["normalized_regret_mean"] for l in learner]) \
                    < np.mean([r["normalized_regret_mean"] for r in reference])
                policy_metric_improves = (np.mean([l["top1_agreement"] for l in learner])
                                          >= np.mean([r["top1_agreement"] for r in reference])
                                          or np.mean([l["ranking_accuracy"] for l in learner])
                                          >= np.mean([r["ranking_accuracy"] for r in reference]))
                per_distribution[eval_name] = {"regret_wins_of_three": regret_wins,
                                               "regret_improves": regret_improves,
                                               "policy_metric_improves": policy_metric_improves}
                supported = supported and regret_wins >= 2 and regret_improves and policy_metric_improves
            evidence.append({"objective": objective, "learner_distribution": learner_distribution,
                             "per_distribution": per_distribution, "supported": supported})
    supported = any(item["supported"] for item in evidence)
    return ("STATE_DISTRIBUTION_MISMATCH_SUPPORTED" if supported
            else "STATE_DISTRIBUTION_MISMATCH_UNRESOLVED"), evidence


def _run(label=LABEL, root_count=ROOT_COUNT, smoke=False):
    compiled, native, _profile = f59._ruleset(label)
    parent = f59._parent(label)
    distributions, provenance = _fresh_distributions(compiled, native, parent, root_count, smoke=smoke)
    print(json.dumps({"phase": "sources_verified", "provenance": provenance}, sort_keys=True,
                     default=_json_default), flush=True)
    computed = _compute_spectra(distributions, smoke=smoke)
    split_ends = (1, 2, 3) if smoke else SPLIT_ENDS
    summaries = {name: _summarize_spectrum(distributions[name], computed[name], split_ends)
                 for name in distributions}
    if any(not summary["split_indices"][part] for summary in summaries.values()
           for part in ("fit", "development", "final_holdout")):
        raise ValueError("INSUFFICIENT_FROZEN_SPLIT")

    train_sets = {}
    for name in TRAINING_DISTRIBUTIONS[:3]:
        train_sets[name] = _train_rows(summaries[name], summaries[name]["split_indices"]["fit"])
    equal_count = min(len(summaries[name]["split_indices"]["fit"]) for name in ("D1_V2_SELFPLAY", "D2_V2_PV_CORRIDOR"))
    d12_indices = {name: summaries[name]["split_indices"]["fit"][:equal_count]
                   for name in ("D1_V2_SELFPLAY", "D2_V2_PV_CORRIDOR")}
    d12_roots = [summaries[name]["roots"][i] for name in d12_indices for i in d12_indices[name]]
    x = np.vstack([row.features for root in d12_roots for row in root])
    base = np.asarray([row.base_q for root in d12_roots for row in root])
    targets = np.asarray([row.q_20k for root in d12_roots for row in root])
    groups = []
    cursor = 0
    for root in d12_roots:
        groups.append(np.arange(cursor, cursor + len(root)))
        cursor += len(root)
    train_sets["D12_D1_D2_MIX"] = (d12_roots, x, base, targets, groups)

    models = {}
    development = {}
    for train_name, (_roots, x, base, targets, groups) in train_sets.items():
        for objective in OBJECTIVES:
            for seed in f59.TRAINING_SEEDS:
                model = f59._fit_model(x, base, targets, groups, objective, seed)
                key = (train_name, objective, seed)
                models[key] = model
                d1 = _evaluate_model(model, summaries["D1_V2_SELFPLAY"], summaries["D1_V2_SELFPLAY"]["split_indices"]["development"])
                d2 = _evaluate_model(model, summaries["D2_V2_PV_CORRIDOR"], summaries["D2_V2_PV_CORRIDOR"]["split_indices"]["development"])
                development[key] = {"D1_V2_SELFPLAY": d1, "D2_V2_PV_CORRIDOR": d2,
                                     "aggregate": _aggregate_policy({"D1_V2_SELFPLAY": d1, "D2_V2_PV_CORRIDOR": d2})}

    config_rows = []
    for train_name in TRAINING_DISTRIBUTIONS:
        for objective in OBJECTIVES:
            runs = [development[(train_name, objective, seed)] for seed in f59.TRAINING_SEEDS]
            config_rows.append({"training_distribution": train_name, "objective": objective,
                                "seed_runs": runs,
                                "aggregate": {metric: float(np.mean([run["aggregate"][metric] for run in runs]))
                                              for metric in ("normalized_regret_mean", "top1_agreement", "ranking_accuracy")}})
    selected_config = sorted(config_rows, key=lambda row: (
        row["aggregate"]["normalized_regret_mean"], -row["aggregate"]["top1_agreement"],
        -row["aggregate"]["ranking_accuracy"], row["training_distribution"], row["objective"]))[0]
    selected_runs = [development[(selected_config["training_distribution"], selected_config["objective"], seed)]
                     for seed in f59.TRAINING_SEEDS]
    selected_seed = sorted(zip(f59.TRAINING_SEEDS, selected_runs),
                           key=lambda item: (item[1]["aggregate"]["normalized_regret_mean"], item[0]))[1][0]
    selection = {"config": selected_config, "selected_seed": selected_seed,
                 "rule": "median development-only seed by aggregate normalized D1/D2 regret"}
    reference_runs = [development[("D0_RANDOM_REACHABLE", "POINTWISE_Q", seed)]
                      for seed in f59.TRAINING_SEEDS]
    reference_aggregate = [_aggregate_policy(run) for run in reference_runs]
    reference_seed = sorted(zip(f59.TRAINING_SEEDS, reference_aggregate),
                            key=lambda item: (item[1]["normalized_regret_mean"], item[0]))[1][0]
    reference_selection = {"training_distribution": "D0_RANDOM_REACHABLE",
                           "objective": "POINTWISE_Q", "selected_seed": reference_seed,
                           "seed_runs": reference_aggregate,
                           "rule": "median development-only seed by aggregate normalized D1/D2 regret"}
    print(json.dumps({"phase": "development_selection_frozen", "selection": selection}, sort_keys=True,
                     default=_json_default), flush=True)

    final = {}
    for key, model in models.items():
        train_name, objective, seed = key
        final[key] = {name: _evaluate_model(model, summaries[name], summaries[name]["split_indices"]["final_holdout"])
                      for name in ("D0_RANDOM_REACHABLE", "D1_V2_SELFPLAY", "D2_V2_PV_CORRIDOR")}

    selected_key = (selected_config["training_distribution"], selected_config["objective"], selected_seed)
    reference_key = ("D0_RANDOM_REACHABLE", "POINTWISE_Q", reference_seed)
    pointwise_d0 = final[reference_key]
    selected_final = final[selected_key]
    reference = _aggregate_policy(pointwise_d0)
    selected_aggregate = _aggregate_policy(selected_final)
    per_distribution_gate = {}
    flips = 0
    for name in ("D1_V2_SELFPLAY", "D2_V2_PV_CORRIDOR"):
        candidate = selected_final[name]
        baseline = pointwise_d0[name]
        distribution_flips = 0
        for index in summaries[name]["split_indices"]["final_holdout"]:
            candidate_values = f59._predict_total_q(summaries[name]["roots"][index], models[selected_key])
            baseline_values = f59._predict_total_q(summaries[name]["roots"][index], models[reference_key])
            distribution_flips += int(np.argmax(candidate_values) != np.argmax(baseline_values))
        flips += distribution_flips
        per_distribution_gate[name] = {
            "material_normalized_regret_improvement": candidate["normalized_regret_mean"]
            <= baseline["normalized_regret_mean"] * (1.0 - MATERIAL_IMPROVEMENT),
            "not_single_side_catastrophic": candidate["normalized_regret_mean"]
            <= max(baseline["normalized_regret_mean"] * 1.5, baseline["normalized_regret_mean"] + 0.05),
            "top1_or_ranking_improves": candidate["top1_agreement"] >= baseline["top1_agreement"]
            or candidate["ranking_accuracy"] >= baseline["ranking_accuracy"],
            "action_choice_flips": distribution_flips,
        }
    seed_robustness = []
    for seed in f59.TRAINING_SEEDS:
        candidate = _aggregate_policy(final[(selected_config["training_distribution"], selected_config["objective"], seed)])
        baseline = _aggregate_policy(final[("D0_RANDOM_REACHABLE", "POINTWISE_Q", seed)])
        seed_robustness.append({"seed": seed, "regret_not_worse": candidate["normalized_regret_mean"] <= baseline["normalized_regret_mean"],
                                "policy_metric_not_worse": candidate["top1_agreement"] >= baseline["top1_agreement"]
                                or candidate["ranking_accuracy"] >= baseline["ranking_accuracy"]})
    robust_seed_count = sum(item["regret_not_worse"] and item["policy_metric_not_worse"] for item in seed_robustness)
    candidate_gate = {
        "selected_key": list(selected_key),
        "reference_key": list(reference_key),
        "reference": reference,
        "selected": selected_aggregate,
        "per_distribution": per_distribution_gate,
        "seed_robustness": seed_robustness,
        "robust_seed_count": robust_seed_count,
        "material_normalized_regret_improvement": all(item["material_normalized_regret_improvement"]
                                                      for item in per_distribution_gate.values()),
        "top1_or_ranking_improves": selected_aggregate["top1_agreement"] > reference["top1_agreement"]
        or selected_aggregate["ranking_accuracy"] > reference["ranking_accuracy"],
        "action_choice_flips": flips,
    }
    candidate_gate["eligible_for_shallow_policy_gate"] = all((candidate_gate["material_normalized_regret_improvement"],
                                                               candidate_gate["top1_or_ranking_improves"],
                                                               robust_seed_count >= 2, flips > 0,
                                                               all(item["not_single_side_catastrophic"] and item["top1_or_ranking_improves"]
                                                                   for item in per_distribution_gate.values())))
    policy_classification, policy_evidence = _objective_classification(final, TRAINING_DISTRIBUTIONS)
    state_classification, state_evidence = _distribution_classification(final)
    return {"label": label, "parent_checkpoint_id": parent.checkpoint_id,
            "root_count": root_count, "provenance": provenance,
            "distributions": {name: {key: value for key, value in summary.items() if key != "roots"}
                              for name, summary in summaries.items()},
            "training_matrix": {"training_distributions": TRAINING_DISTRIBUTIONS,
                                "objectives": OBJECTIVES, "model_width": f59.MODEL_WIDTH,
                                "regularization": f59.MODEL_REGULARIZATION,
                                "temperature": f59.TEMPERATURE,
                                "d12_equal_fit_root_count": equal_count},
            "development_selection": selection,
            "reference_selection": reference_selection,
            "development_matrix": config_rows,
            "final_matrix": {"|".join(map(str, key)): value for key, value in final.items()},
            "candidate_gate": candidate_gate,
            "classifications": {"policy_objective": policy_classification,
                                "state_distribution": state_classification},
            "classification_evidence": {"policy_objective": policy_evidence,
                                         "state_distribution": state_evidence}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-count", type=int, default=ROOT_COUNT)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output-name", default="f60_results.json")
    args = parser.parse_args()
    if args.smoke:
        root_count = 3
    elif args.root_count != ROOT_COUNT:
        raise ValueError("F60 root-count is frozen at 96 outside smoke mode")
    else:
        root_count = ROOT_COUNT
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {"work_order": "GENERICCHESS-F60-DISJOINT-POLICY-OBJECTIVE-AND-DISTRIBUTION-VALIDATION",
               "parent_checkpoint": "790695da03cd4bdcc9412f3566517063b0c674e3",
               "smoke": args.smoke, "results": [_run(root_count=root_count, smoke=args.smoke)]}
    (OUT / args.output_name).write_text(json.dumps(payload, sort_keys=True, indent=2,
                                                    default=_json_default) + "\n", encoding="utf-8")
    print(json.dumps({"work_order": payload["work_order"], "root_count": root_count,
                      "candidate_gate": payload["results"][0]["candidate_gate"]},
                     sort_keys=True, default=_json_default))


if __name__ == "__main__":
    main()
