"""F61 strength-first triage of the F60 learner-derived candidates.

F60 established offline policy/distribution signals but did not persist model
parameters.  This stage deterministically reconstructs only the F60
fit/development source data, serializes the three work-order-selected models,
and tests them in the real semantic search before any teacher gate can reject
an Arena run.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f60_disjoint_policy_objective_validation as f60  # noqa: E402
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.learning.arena import ArenaConfig, run_arena  # noqa: E402
from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402


LABEL = f60.LABEL
F60_RESULT = ROOT / ".generic_chess_flow" / "f60-disjoint-policy-validation" / "f60_results_corrected.json"
OUT = ROOT / ".generic_chess_flow" / "f61-strength-first-triage"
MODEL_WIDTH = f59.MODEL_WIDTH
MODEL_REGULARIZATION = f59.MODEL_REGULARIZATION
TEMPERATURE = f59.TEMPERATURE
FIT_AND_DEVELOPMENT = ("fit", "development")
TRIAGE_PAIRS = 4
TRIAGE_NODES = 2_000
TRIAGE_MAX_DEPTH = 12


def _json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def _load_f60() -> dict:
    if not F60_RESULT.exists():
        raise FileNotFoundError(f"F60 result is required for F61 reconstruction: {F60_RESULT}")
    payload = json.loads(F60_RESULT.read_text(encoding="utf-8"))
    result = payload["results"][0]
    return result


def _median_seed(row: dict) -> int:
    runs = list(zip(f59.TRAINING_SEEDS, row["seed_runs"]))
    ordered = sorted(runs, key=lambda item: (item[1]["aggregate"]["normalized_regret_mean"], item[0]))
    return int(ordered[1][0])


def _best_config(result: dict, training_distribution: str) -> dict:
    rows = [
        row for row in result["development_matrix"]
        if row["training_distribution"] == training_distribution
    ]
    if not rows:
        raise ValueError(f"F60 development matrix lacks {training_distribution}")
    return min(
        rows,
        key=lambda row: (
            row["aggregate"]["normalized_regret_mean"],
            -row["aggregate"]["top1_agreement"],
            -row["aggregate"]["ranking_accuracy"],
            row["objective"],
        ),
    )


def _candidate_specs(result: dict) -> list[dict]:
    d12 = _best_config(result, "D12_D1_D2_MIX")
    d2 = _best_config(result, "D2_V2_PV_CORRIDOR")
    return [
        {
            "candidate_id": "F60_D0_PAIRWISE_SEED_59012",
            "training_distribution": "D0_RANDOM_REACHABLE",
            "objective": "PAIRWISE_RANKING",
            "seed": 59012,
            "selection_basis": "explicit F61 work-order candidate",
        },
        {
            "candidate_id": "F60_D12_MEDIAN_DEVELOPMENT_SEED",
            "training_distribution": d12["training_distribution"],
            "objective": d12["objective"],
            "seed": _median_seed(d12),
            "selection_basis": "best F60 development aggregate then median seed",
        },
        {
            "candidate_id": "F60_D2_MEDIAN_DEVELOPMENT_SEED",
            "training_distribution": d2["training_distribution"],
            "objective": d2["objective"],
            "seed": _median_seed(d2),
            "selection_basis": "best F60 development aggregate then median seed",
        },
    ]


def _fit_serializable(features, base_q, targets, groups, objective, seed):
    """Exact F59 optimizer, retaining parameters for a deployable checkpoint."""
    x = np.asarray(features, dtype=float)
    residual = np.asarray(targets, dtype=float) - np.asarray(base_q, dtype=float)
    mean = np.mean(x, axis=0)
    scale = np.where(np.std(x, axis=0) > 1e-9, np.std(x, axis=0), 1.0)
    xn = (x - mean) / scale
    target_scale = float(np.std(residual)) or 1.0
    yn = residual / target_scale
    rng = np.random.default_rng(seed)
    hidden_weights = rng.normal(
        0.0, np.sqrt(2.0 / (x.shape[1] + MODEL_WIDTH)),
        size=(MODEL_WIDTH, x.shape[1]),
    )
    hidden_bias = np.zeros(MODEL_WIDTH)
    output_weights = rng.normal(0.0, 1.0 / np.sqrt(MODEL_WIDTH), size=MODEL_WIDTH)
    output_bias = np.asarray(0.0)
    moments = [(np.zeros_like(p), np.zeros_like(p)) for p in (
        hidden_weights, hidden_bias, output_weights, output_bias
    )]
    for step in range(1, 601):
        hidden = np.tanh(xn @ hidden_weights.T + hidden_bias)
        prediction = hidden @ output_weights + output_bias
        grad_prediction = np.zeros(len(x), dtype=float)
        if objective == "POINTWISE_Q":
            grad_prediction = (prediction - yn) / len(x)
        elif objective == "SOFT_POLICY_DISTILLATION":
            for indices in groups:
                grad_prediction[indices] = f59._soft_policy_grad_prediction(
                    targets[indices], base_q[indices], prediction[indices], target_scale,
                    TEMPERATURE,
                )
            grad_prediction /= max(len(groups), 1)
        elif objective == "PAIRWISE_RANKING":
            pair_count = 0
            for indices in groups:
                for left in range(len(indices)):
                    for right in range(left + 1, len(indices)):
                        i, j = indices[left], indices[right]
                        delta = (targets[i] - targets[j]) / target_scale
                        if abs(delta) < 1e-9:
                            continue
                        sign = 1.0 if delta > 0 else -1.0
                        total_prediction = base_q + prediction * target_scale
                        margin = sign * (total_prediction[i] - total_prediction[j]) / target_scale
                        derivative = -sign / (1.0 + math.exp(min(60.0, max(-60.0, margin))))
                        grad_prediction[i] += derivative
                        grad_prediction[j] -= derivative
                        pair_count += 1
            grad_prediction /= max(pair_count, 1)
        else:
            raise ValueError(f"unknown objective {objective}")
        grad_output = hidden.T @ grad_prediction + MODEL_REGULARIZATION * output_weights
        grad_hidden = (
            (grad_prediction[:, None] * output_weights[None, :])
            * (1.0 - hidden * hidden)
        ).T @ xn + MODEL_REGULARIZATION * hidden_weights
        grad_hidden_bias = np.sum(
            (grad_prediction[:, None] * output_weights[None, :])
            * (1.0 - hidden * hidden), axis=0
        )
        gradients = (
            grad_hidden, grad_hidden_bias, grad_output,
            np.asarray(np.sum(grad_prediction)),
        )
        for index, (param, gradient) in enumerate(zip(
            (hidden_weights, hidden_bias, output_weights, output_bias), gradients
        )):
            first, second = moments[index]
            first[...] = 0.9 * first + 0.1 * gradient
            second[...] = 0.999 * second + 0.001 * gradient * gradient
            param[...] -= 0.01 * (first / (1.0 - 0.9 ** step)) / (
                np.sqrt(second / (1.0 - 0.999 ** step)) + 1e-8
            )
    return CompactNonlinearResidual(
        input_mean=tuple(mean.tolist()), input_scale=tuple(scale.tolist()),
        target_scale=target_scale,
        hidden_weights=tuple(tuple(row) for row in hidden_weights.tolist()),
        hidden_bias=tuple(hidden_bias.tolist()),
        output_weights=tuple(output_weights.tolist()),
        output_bias=float(output_bias), width=MODEL_WIDTH,
        regularization=MODEL_REGULARIZATION, seed=seed,
    )


def _training_set(summaries: dict, name: str):
    return f60._train_rows(summaries[name], summaries[name]["split_indices"]["fit"])


def _candidate_training_set(summaries: dict, spec: dict):
    name = spec["training_distribution"]
    if name != "D12_D1_D2_MIX":
        return _training_set(summaries, name)
    equal_count = min(
        len(summaries[name]["split_indices"]["fit"])
        for name in ("D1_V2_SELFPLAY", "D2_V2_PV_CORRIDOR")
    )
    roots = [
        summaries[name]["roots"][index]
        for name in ("D1_V2_SELFPLAY", "D2_V2_PV_CORRIDOR")
        for index in summaries[name]["split_indices"]["fit"][:equal_count]
    ]
    features = np.vstack([row.features for root in roots for row in root])
    base = np.asarray([row.base_q for root in roots for row in root])
    targets = np.asarray([row.q_20k for root in roots for row in root])
    groups = []
    cursor = 0
    for root in roots:
        groups.append(np.arange(cursor, cursor + len(root)))
        cursor += len(root)
    return roots, features, base, targets, groups


def _hand_type_indices(compiled):
    current = tuple(sorted(compiled.support.type_metadata))
    base = tuple(sorted(piece_type.type_id for piece_type in compiled._legacy_compiled.piece_types))
    return tuple(current.index(type_id) for type_id in base)


def _candidate_checkpoint(parent, compiled, model, spec):
    payload = replace(
        model, hand_type_indices=_hand_type_indices(compiled),
        perspective="successor_root_q",
    ).to_dict()
    config_hash = stable_sha256({
        "stage": "F61_STRENGTH_FIRST_TRIAGE",
        "parent": parent.checkpoint_id,
        "candidate": spec,
        "model": payload,
    })
    return parent.child_checkpoint(
        board_weights=parent.board_weights,
        hand_weights=parent.hand_weights,
        dynamic_weights=parent.dynamic_weights,
        compact_nonlinear=payload,
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=config_hash,
        training_seed=spec["seed"],
    ), payload


def _opening_record(opening):
    return {"action_history": [f59.action_to_dict(action) for action in opening.actions]}


def _search_validation(compiled, native, parent, child, openings, nodes):
    rows = []
    for opening in openings.openings:
        record = _opening_record(opening)
        session = f59._session(compiled, record)
        started = time.perf_counter()
        parent_result = SemanticSearchEngine(
            compiled, native, checkpoint=parent, tt_megabytes=8
        ).search(session, SearchLimits(max_depth=TRIAGE_MAX_DEPTH, max_nodes=nodes, quiescence_max_depth=0))
        parent_seconds = time.perf_counter() - started
        started = time.perf_counter()
        child_result = SemanticSearchEngine(
            compiled, native, checkpoint=child, tt_megabytes=8
        ).search(session, SearchLimits(max_depth=TRIAGE_MAX_DEPTH, max_nodes=nodes, quiescence_max_depth=0))
        child_seconds = time.perf_counter() - started
        parent_action = None if parent_result.action is None else f59.action_to_dict(parent_result.action)
        child_action = None if child_result.action is None else f59.action_to_dict(child_result.action)
        rows.append({
            "opening_id": opening.final_position_key,
            "parent_action": parent_action,
            "child_action": child_action,
            "decision_changed": parent_action != child_action,
            "parent_score": int(parent_result.score),
            "child_score": int(child_result.score),
            "parent_nodes": int(parent_result.nodes),
            "child_nodes": int(child_result.nodes),
            "parent_seconds": parent_seconds,
            "child_seconds": child_seconds,
        })
    first_divergence = next(
        (dict(row) for row in rows if row["decision_changed"]), None
    )
    return {
        "opening_count": len(rows),
        "decision_changes": sum(row["decision_changed"] for row in rows),
        "first_decision_divergence": first_divergence,
        "rows": rows,
    }


def _arena_payload(summary):
    return {
        "pair_count": summary.pair_count,
        "pair_scores": list(summary.pair_scores),
        "mean_pair_score": summary.mean_pair_score,
        "child_better_pairs": summary.child_better_pairs,
        "tied_pairs": summary.tied_pairs,
        "child_worse_pairs": summary.child_worse_pairs,
        "bootstrap_low": summary.bootstrap_low,
        "bootstrap_high": summary.bootstrap_high,
        "game_wins": summary.game_wins,
        "game_draws": summary.game_draws,
        "game_losses": summary.game_losses,
        "game_score_rate": summary.game_score_rate,
        "pairs": [
            {
                "pair_index": pair.pair_index,
                "opening_id": pair.opening_id,
                "games": [
                    {
                        "child_owner": game.child_owner,
                        "winner": game.winner,
                        "result": game.result,
                        "plies": game.plies,
                        "actions": [f59.action_to_dict(action) for action in game.actions],
                        "final_position_key": game.final_position_key,
                    }
                    for game in (pair.game_child_owner0, pair.game_child_owner1)
                ],
            }
            for pair in summary.pairs
        ],
    }


def _run(root_count=f60.ROOT_COUNT, smoke=False):
    result = _load_f60()
    specs = _candidate_specs(result)
    compiled, native, _profile = f59._ruleset(LABEL)
    parent = f59._parent(LABEL)
    if parent.checkpoint_id != result["parent_checkpoint_id"]:
        raise ValueError("reconstructed F61 parent does not match F60")

    distributions, provenance = f60._fresh_distributions(
        compiled, native, parent, 3 if smoke else root_count, smoke=smoke
    )
    if not smoke:
        if provenance["source_ids"] != result["provenance"]["source_ids"]:
            raise ValueError("F60 source regeneration digest mismatch")
    records = {
        name: [record for record in values if record.get("source_split") in FIT_AND_DEVELOPMENT]
        for name, values in distributions.items()
    }
    computed = f60._compute_spectra(records, smoke=smoke)
    split_ends = (1, 2, 3) if smoke else f60.SPLIT_ENDS
    summaries = {
        name: f60._summarize_spectrum(records[name], computed[name], split_ends)
        for name in records
    }
    if any(
        not summaries[name]["split_indices"][part]
        for name in summaries
        for part in FIT_AND_DEVELOPMENT
    ):
        raise ValueError("F61 reconstructed fit/development split is insufficient")

    candidate_rows = []
    checkpoints = {}
    for spec in specs:
        roots, features, base, targets, groups = _candidate_training_set(summaries, spec)
        model = _fit_serializable(features, base, targets, groups, spec["objective"], spec["seed"])
        checkpoint, model_payload = _candidate_checkpoint(parent, compiled, model, spec)
        if spec["training_distribution"] == "D12_D1_D2_MIX":
            dev_parts = [
                (name, summaries[name]["split_indices"]["development"])
                for name in ("D1_V2_SELFPLAY", "D2_V2_PV_CORRIDOR")
            ]
            dev_roots = [summaries[name]["roots"][index] for name, indices in dev_parts for index in indices]
            dev_source_groups = [
                records[name][index].get("source_group", "")
                for name, indices in dev_parts for index in indices
            ]
        else:
            dev_indices = summaries[spec["training_distribution"]]["split_indices"]["development"]
            dev_summary = summaries[spec["training_distribution"]]
            dev_roots = [dev_summary["roots"][index] for index in dev_indices]
            dev_source_groups = [records[spec["training_distribution"]][index].get("source_group", "") for index in dev_indices]
        dev_metrics = f60._metrics_with_normalized_regret(
            dev_roots,
            [model.predict(np.vstack([row.features for row in root])) for root in dev_roots],
        )
        checkpoints[spec["candidate_id"]] = checkpoint
        candidate_rows.append({
            **spec,
            "parent_checkpoint_id": parent.checkpoint_id,
            "checkpoint_id": checkpoint.checkpoint_id,
            "model_sha256": stable_sha256(model_payload),
            "input_dimension": len(model.input_mean),
            "fit_root_count": len(roots),
            "fit_action_count": int(len(features)),
            "model": model_payload,
            "development_metrics": dev_metrics,
            "development_source_groups": sorted(set(dev_source_groups)),
        })

    openings = generate_arena_openings(
        compiled, count=TRIAGE_PAIRS if smoke else TRIAGE_PAIRS,
        seed=610601, min_plies=2, max_plies=6,
    )
    for row in candidate_rows:
        child = checkpoints[row["candidate_id"]]
        validation_openings = generate_arena_openings(
            compiled, count=8 if not smoke else 2, seed=610500 + len(row["candidate_id"]),
            min_plies=2, max_plies=6,
        )
        validation = _search_validation(
            compiled, native, parent, child, validation_openings,
            100 if smoke else TRIAGE_NODES,
        )
        row["search_validation"] = validation
        if validation["decision_changes"] == 0:
            row["arena_status"] = "DROPPED_BEHAVIORALLY_IDENTICAL"
            continue
        arena = run_arena(
            compiled, native, parent, child,
            ArenaConfig(
                pairs=2 if smoke else TRIAGE_PAIRS,
                nodes_per_move=100 if smoke else TRIAGE_NODES,
                max_depth=4 if smoke else TRIAGE_MAX_DEPTH,
                tt_megabytes=2 if smoke else 8,
                opening_seed=610601,
                opening_count=2 if smoke else TRIAGE_PAIRS,
                min_plies=2,
                max_plies=6,
                workers=1 if smoke else min(4, max(1, os.cpu_count() or 1)),
            ),
            openings=generate_arena_openings(
                compiled, count=2 if smoke else TRIAGE_PAIRS,
                seed=610601, min_plies=2, max_plies=6,
            ),
        )
        row["arena_triage"] = _arena_payload(arena)
        triage = row["arena_triage"]
        catastrophic = (
            triage["mean_pair_score"] <= 0.25
            and triage["child_worse_pairs"] >= triage["pair_count"] - 1
        )
        row["not_clearly_bad_after_4_pairs"] = not catastrophic
        row["early_stop_reason"] = (
            "catastrophic_4_pair_loss" if catastrophic else None
        )
        row["arena_status"] = (
            "EARLY_STOP_CATASTROPHIC" if catastrophic else "TRIAGE_COMPLETE"
        )

    active = [
        row for row in candidate_rows
        if row["arena_status"] == "TRIAGE_COMPLETE"
        and row.get("not_clearly_bad_after_4_pairs", False)
    ]
    best = max(active, key=lambda row: (row["arena_triage"]["mean_pair_score"], row["candidate_id"])) if active else None
    if best is not None and not smoke and best["not_clearly_bad_after_4_pairs"]:
        extension_openings = generate_arena_openings(
            compiled, count=8, seed=610602, min_plies=2, max_plies=6,
        )
        child = checkpoints[best["candidate_id"]]
        eight = run_arena(
            compiled, native, parent, child,
            ArenaConfig(
                pairs=8, nodes_per_move=TRIAGE_NODES, max_depth=TRIAGE_MAX_DEPTH,
                tt_megabytes=8, opening_seed=610602, opening_count=8,
                min_plies=2, max_plies=6, workers=min(4, max(1, os.cpu_count() or 1)),
            ),
            openings=extension_openings,
        )
        best["arena_extension_8_pairs"] = _arena_payload(eight)
        if eight.mean_pair_score >= 0.5:
            confirmation = run_arena(
                compiled, native, parent, child,
                ArenaConfig(
                    pairs=32, nodes_per_move=TRIAGE_NODES, max_depth=TRIAGE_MAX_DEPTH,
                    tt_megabytes=8, opening_seed=610603, opening_count=32,
                    min_plies=2, max_plies=6, workers=min(4, max(1, os.cpu_count() or 1)),
                ),
                openings=generate_arena_openings(
                    compiled, count=32, seed=610603, min_plies=2, max_plies=6,
                ),
            )
            best["arena_confirmation_32_pairs"] = _arena_payload(confirmation)

    return {
        "work_order": "GENERICCHESS-F61-STRENGTH-FIRST-TRIAGE-AND-TERMINAL-CONTRACT",
        "parent_checkpoint_id": parent.checkpoint_id,
        "f60_result_sha256": stable_sha256(result),
        "source_reconstruction": {
            "root_count": 3 if smoke else root_count,
            "computed_splits": list(FIT_AND_DEVELOPMENT),
            "provenance": provenance,
        },
        "candidate_selection": specs,
        "candidates": candidate_rows,
        "best_candidate_id": None if best is None else best["candidate_id"],
        "teacher_metrics_are_diagnostic_only": True,
        "arena_gate": "actual_parent_child_behavior_only",
        "terminal_contract": {
            "ongoing_without_bootstrap": "rejected",
            "explicit_bootstrap": "accepted_for_future_cutoff_td",
            "historical_f50_f53": "not_reclassified",
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-count", type=int, default=f60.ROOT_COUNT)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output-name", default="f61_results.json")
    args = parser.parse_args()
    if args.smoke:
        root_count = 3
    elif args.root_count != f60.ROOT_COUNT:
        raise ValueError("F61 root-count is frozen at 96 outside smoke mode")
    else:
        root_count = f60.ROOT_COUNT
    OUT.mkdir(parents=True, exist_ok=True)
    payload = _run(root_count=root_count, smoke=args.smoke)
    (OUT / args.output_name).write_text(
        json.dumps(payload, sort_keys=True, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "work_order": payload["work_order"],
        "parent_checkpoint_id": payload["parent_checkpoint_id"],
        "candidate_ids": [row["candidate_id"] for row in payload["candidates"]],
        "arena_status": {
            row["candidate_id"]: row["arena_status"] for row in payload["candidates"]
        },
        "best_candidate_id": payload["best_candidate_id"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
