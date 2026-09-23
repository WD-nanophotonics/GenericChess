"""Static evaluator-surface audit over the two already-recorded F158 games.

No player, root search, new opening, or new game is run here. The exact saved
trajectories are replayed and every legal one-ply action is scored directly.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.core.transition import apply_action
from generic_chess.session.session import GameSession
from scripts import f149_shogi_material_score_race_deep_openings as race
from scripts.f144_shogi_material_only_arena_evolution import MaterialOnlyEvaluator

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BASE_SHA = "a971e251e8032a78626acab61dc613ab31532de3"
CATEGORIES = ("capture_only", "check_only", "capture_plus_check", "zero")


def _category(event: dict) -> str:
    if event["capture"] and event["check"]:
        return "capture_plus_check"
    if event["capture"]:
        return "capture_only"
    if event["check"]:
        return "check_only"
    return "zero"


def _delta_bucket(delta: int) -> str:
    return "better" if delta > 0 else "worse" if delta < 0 else "neutral"


def _stats(deltas: list[int]) -> dict:
    ordered = sorted(deltas)
    if not ordered:
        return {"count": 0, "min": None, "q1": None, "median": None, "q3": None, "max": None,
                "mean": None, "values": {}}
    def quantile(fraction: float) -> int:
        return ordered[round((len(ordered) - 1) * fraction)]
    return {
        "count": len(ordered), "min": ordered[0], "q1": quantile(.25),
        "median": quantile(.5), "q3": quantile(.75), "max": ordered[-1],
        "mean": sum(ordered) / len(ordered),
        "values": {str(k): v for k, v in sorted(Counter(ordered).items())},
    }


def _best(candidates: list[dict], evaluator: str, *, categories: set[str] | None = None) -> dict | None:
    eligible = [row for row in candidates if categories is None or row["category"] in categories]
    return max(eligible, key=lambda row: row[f"{evaluator}_mover_value"], default=None)


def _classify(summary: dict) -> dict:
    missed = summary["missed_zero_scoring_opportunities"]
    total_missed = missed["root_count"]
    check_only = missed["by_best_scoring_action_category"]["check_only"]
    outside_count = check_only["best_action_material_neutral_under_both"]
    outside_rate = outside_count / total_missed if total_missed else 0.0
    material_better_count = missed["capture_or_combo_best_materially_better_under_either_root_count"]
    material_rate = material_better_count / total_missed if total_missed else 0.0
    if total_missed and outside_rate > 0.5 and material_rate > 0:
        label = "SCORE_RACE_MIXED_ALIGNMENT"
    elif total_missed and outside_rate > 0.5:
        label = "SCORE_RACE_CHECK_REWARD_OUTSIDE_MATERIAL_LEARNABLE_SURFACE"
    elif material_rate > 0:
        label = "SCORE_RACE_MIXED_ALIGNMENT"
    else:
        label = "SCORE_RACE_MATERIALLY_ALIGNED"
    return {
        "label": label,
        "rule": "Check-reward is outside the material-only surface when strictly more than half of all missed scoring-opportunity roots have a best check-only action that is material-neutral under both evaluators. Mixed alignment applies when that condition coexists with missed capture/capture+check actions materially better than the recorded zero-score move, or when such materially better capture opportunities occur without the check-only majority. No arbitrary score cutoff is used.",
        "missed_roots": total_missed,
        "check_only_best_neutral_under_both": outside_count,
        "check_only_neutral_fraction_of_missed_roots": outside_rate,
        "missed_capture_or_combo_best_materially_better_under_either": material_better_count,
        "materially_better_capture_or_combo_fraction_of_missed_roots": material_rate,
    }


def _materially_changes(candidate: dict) -> bool:
    action = candidate["action"]
    return bool(candidate["capture"] or action.get("promotion_target_id"))


def _analyze_root(compiled, session, recorded: dict, evaluator_by_name: dict[str, MaterialOnlyEvaluator], game_index: int, ply: int, cycle_indices: set[int]) -> dict:
    before_state = session.state
    mover = before_state.position.side_to_move
    legal = session.legal_actions()
    actual = race.v2.action_from_dict(recorded["action"])
    if actual not in legal or mover != int(recorded["actor"]):
        raise AssertionError(f"recorded move not legal/actor mismatch game={game_index} ply={ply}")
    candidates = []
    for action in legal:
        after = apply_action(before_state, action, compiled)
        event = race.score_event(before_state.position, action, after.position, mover, compiled)
        row = {
            "action": race.v2.action_to_dict(action),
            "category": _category(event),
            "capture": int(event["capture"]),
            "check": int(event["check"]),
            "points": int(event["points"]),
            "changes_material_by_capture_or_promotion": bool(event["capture"] or getattr(action, "promotion_target_id", None)),
        }
        for name, evaluator in evaluator_by_name.items():
            # evaluate() is side-to-move perspective after the action (opponent).
            row[f"{name}_mover_value"] = -evaluator.evaluate(after)
        candidates.append(row)

    actual_dict = race.v2.action_to_dict(actual)
    actual_row = next(row for row in candidates if row["action"] == actual_dict)
    if {key: actual_row[key] for key in ("capture", "check", "points")} != {
        key: int(recorded[key]) for key in ("capture", "check", "points")
    }:
        raise AssertionError("recorded event differs from reconstructed event")
    per_evaluator = {}
    for name in evaluator_by_name:
        best_value = max(row[f"{name}_mover_value"] for row in candidates)
        argmax = [row for row in candidates if row[f"{name}_mover_value"] == best_value]
        for row in candidates:
            row[f"{name}_delta_vs_actual"] = row[f"{name}_mover_value"] - actual_row[f"{name}_mover_value"]
            row[f"{name}_in_static_argmax"] = row[f"{name}_mover_value"] == best_value
        per_evaluator[name] = {
            "actual_value": actual_row[f"{name}_mover_value"],
            "best_value": best_value,
            "argmax_action_count": len(argmax),
            "actual_action_in_argmax": actual_row[f"{name}_in_static_argmax"],
            "best_scoring_action": _best(candidates, name, categories={"capture_only", "check_only", "capture_plus_check"}),
        }
        best_scoring = per_evaluator[name]["best_scoring_action"]
        if best_scoring is not None:
            per_evaluator[name]["best_scoring_action_delta_vs_actual"] = best_scoring[f"{name}_delta_vs_actual"]
            per_evaluator[name]["best_scoring_action_delta_bucket"] = _delta_bucket(best_scoring[f"{name}_delta_vs_actual"])
            per_evaluator[name]["best_scoring_action_category"] = best_scoring["category"]
    return {
        "game_index": game_index,
        "scored_ply": ply,
        "mover": mover,
        "recorded_action": actual_dict,
        "recorded_category": actual_row["category"],
        "recorded_points": actual_row["points"],
        "cycle_zero_score_root": ply in cycle_indices,
        "legal_action_count": len(candidates),
        "category_action_counts": dict(Counter(row["category"] for row in candidates)),
        "evaluators": per_evaluator,
        "candidates": candidates,
    }


def _aggregate(roots: list[dict]) -> dict:
    category_result = {}
    for category in CATEGORIES:
        opportunity = [root for root in roots if root["category_action_counts"].get(category, 0) > 0]
        selected = [root for root in opportunity if root["recorded_category"] == category]
        missed_zero = [root for root in opportunity if root["recorded_points"] == 0]
        per_eval = {}
        for name in ("gen0", "mutant0"):
            deltas = []
            buckets = Counter()
            best_category_rows = []
            top1 = sum(root["evaluators"][name]["actual_action_in_argmax"] for root in opportunity)
            for root in missed_zero:
                best_cat = _best(root["candidates"], name, categories={category})
                if best_cat:
                    delta = best_cat[f"{name}_delta_vs_actual"]
                    deltas.append(delta)
                    buckets[_delta_bucket(delta)] += 1
                    best_category_rows.append(best_cat)
            per_eval[name] = {
                "static_material_top1_agreement_count": top1,
                "static_material_top1_agreement_denominator": len(opportunity),
                "static_material_top1_agreement_fraction": top1 / len(opportunity) if opportunity else None,
                "missed_zero_best_category_action_delta_vs_actual": _stats(deltas),
                "missed_zero_best_category_action_delta_buckets": dict(buckets),
                "missed_zero_best_category_action_material_better_under_either_count": sum(
                    best[f"{name}_delta_vs_actual"] > 0 for best in best_category_rows
                ),
                "missed_zero_best_category_action_material_neutral_count": sum(
                    best[f"{name}_delta_vs_actual"] == 0 for best in best_category_rows
                ),
                "missed_zero_best_category_action_material_worse_count": sum(
                    best[f"{name}_delta_vs_actual"] < 0 for best in best_category_rows
                ),
            }
        category_result[category] = {
            "opportunity_root_count": len(opportunity),
            "selected_root_count": len(selected),
            "selected_fraction_of_opportunity_roots": len(selected) / len(opportunity) if opportunity else None,
            "missed_zero_root_count": len(missed_zero),
            "missed_zero_fraction_of_opportunity_roots": len(missed_zero) / len(opportunity) if opportunity else None,
            "best_scoring_action_material_neutral_worse_better_than_recorded_move": {
                name: per_eval[name]["missed_zero_best_category_action_delta_buckets"] for name in per_eval
            },
            "evaluators": per_eval,
        }

    missed_roots = [root for root in roots if root["recorded_points"] == 0 and any(
        root["category_action_counts"].get(category, 0) for category in CATEGORIES[:-1]
    )]
    best_category_by_eval = {}
    for category in CATEGORIES[:-1]:
        rows = [root for root in missed_roots if root["category_action_counts"].get(category, 0)]
        result_by_eval = {}
        for name in ("gen0", "mutant0"):
            candidates = [_best(root["candidates"], name, categories={category}) for root in rows]
            candidates = [row for row in candidates if row is not None]
            deltas = [row[f"{name}_delta_vs_actual"] for row in candidates]
            changes = sum(_materially_changes(row) for row in candidates)
            result_by_eval[name] = {
                "best_action_delta_bucket_counts": dict(Counter(_delta_bucket(v) for v in deltas)),
                "best_action_delta_distribution": _stats(deltas),
                "best_action_material_neutral_count": sum(v == 0 for v in deltas),
                "best_action_material_worse_count": sum(v < 0 for v in deltas),
                "best_action_material_better_count": sum(v > 0 for v in deltas),
                "best_action_changes_material_count": changes,
            }
        best_category_by_eval[category] = {
            "opportunity_root_count": len(rows),
            "best_action_comparison_vs_actual": result_by_eval,
        }

    no_capture_check = []
    for root in missed_roots:
        options = [row for row in root["candidates"] if row["category"] == "check_only"
                   and not row["capture"] and not row["action"].get("promotion_target_id")]
        if options:
            no_capture_check.append(root)

    category_neutral_both = {}
    category_better_either = {}
    for category in CATEGORIES[:-1]:
        category_roots = [root for root in missed_roots if root["category_action_counts"].get(category, 0)]
        category_neutral_both[category] = sum(
            _best(root["candidates"], "gen0", categories={category})["gen0_delta_vs_actual"] == 0
            and _best(root["candidates"], "mutant0", categories={category})["mutant0_delta_vs_actual"] == 0
            for root in category_roots
        )
        category_better_either[category] = sum(
            any(_best(root["candidates"], name, categories={category})[f"{name}_delta_vs_actual"] > 0
                for name in ("gen0", "mutant0"))
            for root in category_roots
        )
    capture_or_combo_better_roots = sum(
        any(
            root["category_action_counts"].get(category, 0)
            and any(_best(root["candidates"], name, categories={category})[f"{name}_delta_vs_actual"] > 0
                    for name in ("gen0", "mutant0"))
            for category in ("capture_only", "capture_plus_check")
        )
        for root in missed_roots
    )

    cycling = [root for root in roots if root["cycle_zero_score_root"]]
    cycle_result = {}
    for name in ("gen0", "mutant0"):
        gaps, tied, inferior, agreement = [], 0, 0, 0
        for root in cycling:
            actual_value = root["evaluators"][name]["actual_value"]
            best_value = root["evaluators"][name]["best_value"]
            gap = best_value - actual_value
            gaps.append(gap)
            tied += int(gap == 0)
            inferior += int(gap > 0)
            agreement += int(gap == 0)
        cycle_result[name] = {
            "cycling_zero_score_root_count": len(cycling),
            "actual_move_in_material_argmax_set_count": agreement,
            "material_tied_count": tied,
            "materially_inferior_count": inferior,
            "best_legal_material_value_minus_recorded_move_distribution": _stats(gaps),
        }

    top1_all = {}
    for name in ("gen0", "mutant0"):
        top1_all[name] = {
            "recorded_move_in_static_material_argmax_count": sum(root["evaluators"][name]["actual_action_in_argmax"] for root in roots),
            "recorded_root_count": len(roots),
            "fraction": sum(root["evaluators"][name]["actual_action_in_argmax"] for root in roots) / len(roots) if roots else None,
        }
    result = {
        "recorded_root_count": len(roots),
        "roots_with_scoring_action_but_recorded_zero_count": len(missed_roots),
        "category_opportunity_summary": category_result,
        "missed_zero_scoring_opportunities": {
            "root_count": len(missed_roots),
            "by_best_scoring_action_category": {
                category: {
                    "opportunity_root_count": best_category_by_eval[category]["opportunity_root_count"],
                    "best_action_material_neutral_under_both": category_neutral_both[category],
                    "best_action_material_better_under_either": category_better_either[category],
                    "per_evaluator": best_category_by_eval[category]["best_action_comparison_vs_actual"],
                } for category in CATEGORIES[:-1]
            },
            "capture_or_combo_best_materially_better_under_either_root_count": capture_or_combo_better_roots,
            "missed_check_only_options_without_capture_or_promotion_root_count": len(no_capture_check),
            "missed_check_only_options_without_capture_or_promotion_roots": [
                {"game_index": root["game_index"], "scored_ply": root["scored_ply"]}
                for root in no_capture_check
            ],
            "material_change_explanation": "For check-only candidates with no capture and no promotion, material-only leaf scores cannot reward the check event; the immediate evaluator value may still vary only if board material changes (which these flags rule out).",
        },
        "static_material_top1_agreement_all_roots": top1_all,
        "cycling_roots": cycle_result,
    }
    result["classification"] = _classify(result)
    return result


def run(*, source_path: Path, replay_path: Path, output_path: Path) -> dict:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != EXPECTED_BASE_SHA:
        raise ValueError("working base SHA differs from the Chat work order")
    raw = source_path.read_bytes()
    source = json.loads(raw.decode("utf-8"))
    replay_raw = replay_path.read_bytes()
    replay = json.loads(replay_raw.decode("utf-8"))
    if source.get("schema") != "F158_SHOGI_SIGMA070_SINGLE_PAIR_CAUSAL_DIAGNOSTIC_V1" or len(source.get("games", [])) != 2:
        raise ValueError("unexpected source experiment or game count")
    if replay.get("schema") != "F158_SHOGI_SCORE_EVENT_ACCRUAL_CAUSE_REPLAY_V1":
        raise ValueError("unexpected F158 replay evidence")
    if replay.get("source_result_sha256") != hashlib.sha256(raw).hexdigest():
        raise ValueError("replay evidence does not match the exact source result")
    if replay.get("trajectory_scored_plies") != 214:
        raise ValueError("expected exactly the previously reconstructed 214 roots")

    compiled = race._compile()
    opening = race.opening_corpus(compiled, int(source["opening"]["seed"]), int(source["opening"]["count"]))[0]
    if opening.final_position_key != source["opening"]["opening_id"] or len(opening.actions) != int(source["opening"]["actual_plies"]):
        raise AssertionError("saved opening reconstruction mismatch")
    if source["gen0"]["type_ids"] != source["mutant"]["type_ids"]:
        raise AssertionError("material evaluator type-id order differs")
    evaluators = {
        "gen0": MaterialOnlyEvaluator(tuple(source["gen0"]["values"]), source["search"]["fixed_ordering_values"]),
        "mutant0": MaterialOnlyEvaluator(tuple(source["mutant"]["values"]), source["search"]["fixed_ordering_values"]),
    }
    roots = []
    for game_index, game in enumerate(source["games"]):
        session = GameSession(compiled)
        for action in opening.actions:
            session.submit(action)
        replay_game = replay["games"][game_index]
        cycle_indices = set(replay_game["zero_point_plies_in_repeated_move_or_reversal_pattern_indices"])
        if len(game["actions"]) != int(replay_game["scored_ply_count"]):
            raise AssertionError("saved trajectory root count mismatch")
        for ply, recorded in enumerate(game["actions"], 1):
            root = _analyze_root(compiled, session, recorded, evaluators, game_index, ply, cycle_indices)
            roots.append(root)
            session.submit(race.v2.action_from_dict(recorded["action"]))
    if len(roots) != 214:
        raise AssertionError(f"expected 214 roots, got {len(roots)}")
    summary = _aggregate(roots)
    result = {
        "schema": "F158_SHOGI_SCORE_RACE_MATERIAL_OBJECTIVE_ALIGNMENT_V1",
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "classification": summary["classification"],
        "source_result_sha256": hashlib.sha256(raw).hexdigest(),
        "source_replay_sha256": hashlib.sha256(replay_raw).hexdigest(),
        "source_published_git_sha": source.get("git_sha"),
        "analysis_base_git_sha": EXPECTED_BASE_SHA,
        "source_run_id": source.get("run_id"),
        "opening_id": opening.final_position_key,
        "material_evaluators": {
            "gen0_values": list(evaluators["gen0"].values),
            "mutant0_values": list(evaluators["mutant0"].values),
            "fixed_ordering_values": source["search"]["fixed_ordering_values"],
        },
        "unknown": "whether score-race fitness is coupled enough to the 13 learnable material parameters to serve as an evolution objective",
        "method": "reconstruct the exact saved opening and 214 recorded roots; enumerate legal actions and apply each once; score immediate capture/check category and one-ply mover-perspective material values; no search/player/game is started",
        "no_new_game_search_opening_or_mutant": True,
        "classification_basis": summary["classification"]["rule"],
        **summary,
        "roots": roots,
    }
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite analysis result: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp = output_path.with_name(output_path.name + ".tmp")
    temp.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(output_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(source_path=args.source, replay_path=args.replay, output_path=args.output)
    print(json.dumps({
        "classification": result["classification"]["label"],
        "roots": result["recorded_root_count"],
        "missed_scoring_roots": result["roots_with_scoring_action_but_recorded_zero_count"],
        "check_only_without_capture_or_promotion": result["missed_zero_scoring_opportunities"]["missed_check_only_options_without_capture_or_promotion_root_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
