"""F51 TD-direction and teacher-target diagnosis.

This experiment freezes the F50 semantic evaluator/search and five-block
representation.  It builds a fixed teacher from the current v2 parent at
deeper budgets, then measures raw and block-preconditioned versions of the
actual TD direction plus a small positive/negative dynamic finite-difference
surface; no engine or learner infrastructure is changed.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from f50_generic_learnable_evaluator import WEIGHTS, _case, _native_delta, _records, _ruleset

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.selfplay import SelfPlayConfig, collect_self_play
from generic_chess.learning.serialization import stable_sha256
from generic_chess.learning.tdleaf import TDLeafConfig, tdleaf_update
from generic_chess.rules.compiler import compile_ruleset_for_execution


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / ".generic_chess_flow" / "f49-semantic-reentry-authoritative" / "f49_evidence_bundle.json"
OUT = ROOT / ".generic_chess_flow" / "f51-learning-direction-target-diagnosis"
BLOCKS = ("board", "hand", "dynamic")
AMPLITUDES = (0.005, 0.01, 0.02, 0.05, 0.10)
DYNAMIC_NAMES = ("mobility", "promotion_potential", "anchor_safety")


def _teacher_rows(label: str, parent, limit: int, nodes: int) -> list[dict]:
    compiled, native, _profile = _ruleset(label)
    records = _records(label, limit)

    def run(record):
        row = _case(compiled, native, record, parent, nodes)
        return {"action_key": _action_key(row["action"]), "score": row["score"]}

    workers = min(8, max(1, os.cpu_count() or 1), len(records) or 1)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(run, records))


def _agreement(left: list[dict], right: list[dict]) -> float:
    if not left:
        return 0.0
    return sum(_action_key(a["action_key"]) == _action_key(b["action_key"]) for a, b in zip(left, right)) / len(left)


def _blocks(checkpoint) -> dict[str, dict[str, float]]:
    return {
        "board": dict(checkpoint.board_weights),
        "hand": dict(checkpoint.hand_weights),
        "dynamic": dict(checkpoint.dynamic_weights),
    }


def _block_norm(values: dict[str, float]) -> float:
    return math.sqrt(sum(value * value for value in values.values()))


def _direction(parent, child) -> dict[str, dict[str, float]]:
    before = _blocks(parent)
    after = _blocks(child)
    return {
        block: {
            key: after[block].get(key, 0.0) - before[block].get(key, 0.0)
            for key in set(before[block]) | set(after[block])
        }
        for block in BLOCKS
    }


def _scaled_direction_checkpoint(parent, direction, fraction):
    base = _blocks(parent)
    updated = {}
    for block in BLOCKS:
        norm = _block_norm(base[block])
        dnorm = _block_norm(direction[block])
        multiplier = fraction * norm / dnorm if norm > 0.0 and dnorm > 0.0 else 0.0
        updated[block] = {
            key: base[block].get(key, 0.0) + multiplier * value
            for key, value in direction[block].items()
        }
    return replace(
        parent,
        board_weights=updated["board"],
        hand_weights=updated["hand"],
        dynamic_weights=updated["dynamic"],
        training_config_hash=f"F51:td-direction:{fraction}",
        training_seed=None,
    )


def _raw_scaled_direction_checkpoint(parent, direction, fraction):
    """Apply one scalar in the complete, un-preconditioned parameter space."""
    base = _blocks(parent)
    base_norm = math.sqrt(sum(_block_norm(base[block]) ** 2 for block in BLOCKS))
    direction_norm = math.sqrt(sum(_block_norm(direction[block]) ** 2 for block in BLOCKS))
    multiplier = fraction * base_norm / direction_norm if base_norm > 0.0 and direction_norm > 0.0 else 0.0
    updated = {
        block: {
            key: base[block].get(key, 0.0) + multiplier * value
            for key, value in direction[block].items()
        }
        for block in BLOCKS
    }
    return replace(
        parent,
        board_weights=updated["board"],
        hand_weights=updated["hand"],
        dynamic_weights=updated["dynamic"],
        training_config_hash=f"F51:td-raw-direction:{fraction}",
        training_seed=None,
    )


def _dynamic_finite_difference(parent, name: str, sign: int, fraction: float):
    dynamic = dict(parent.dynamic_weights)
    delta = sign * fraction * _block_norm(dynamic)
    dynamic[name] = dynamic.get(name, 0.0) + delta
    return replace(
        parent,
        dynamic_weights=dynamic,
        training_config_hash=f"F51:finite-difference:{name}:{sign}:{fraction}",
        training_seed=None,
    )


def _action_key(payload) -> str | None:
    if payload is None:
        return None
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return payload
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _compare(label: str, parent, candidate, teacher_rows: list[dict], limit: int, nodes: int) -> dict:
    compiled, native, _profile = _ruleset(label)
    records = _records(label, limit)

    def run(record):
        return _case(compiled, native, record, candidate, nodes)

    workers = min(8, max(1, os.cpu_count() or 1), len(records) or 1)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(run, records))
    parent_rows = []
    if candidate.checkpoint_id == parent.checkpoint_id:
        parent_rows = rows
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            parent_rows = list(pool.map(lambda record: _case(compiled, native, record, parent, nodes), records))
    teacher_actions = [_action_key(row["action_key"]) for row in teacher_rows]
    candidate_actions = [_action_key(row["action"]) for row in rows]
    parent_actions = [_action_key(row["action"]) for row in parent_rows]
    candidate_scores = [row["score"] for row in rows]
    parent_scores = [row["score"] for row in parent_rows]
    teacher_scores = [int(row["score"]) for row in teacher_rows]
    n = len(rows)
    candidate_agreement = sum(a == b for a, b in zip(candidate_actions, teacher_actions)) / n if n else 0.0
    parent_agreement = sum(a == b for a, b in zip(parent_actions, teacher_actions)) / n if n else 0.0
    rank_pairs = [(i, j) for i in range(n) for j in range(i + 1, n) if teacher_scores[i] != teacher_scores[j]]
    rank_agreement = (
        sum((candidate_scores[i] - candidate_scores[j]) * (teacher_scores[i] - teacher_scores[j]) > 0 for i, j in rank_pairs)
        / len(rank_pairs)
        if rank_pairs else None
    )
    return {
        "positions": n,
        "workers": workers,
        "teacher_best_move_agreement": candidate_agreement,
        "parent_teacher_best_move_agreement": parent_agreement,
        "move_flip_rate_vs_parent": sum(a != b for a, b in zip(candidate_actions, parent_actions)) / n if n else 0.0,
        "mean_score_change_vs_parent": sum(b - a for a, b in zip(parent_scores, candidate_scores)) / n if n else 0.0,
        "mean_abs_score_change_vs_parent": sum(abs(b - a) for a, b in zip(parent_scores, candidate_scores)) / n if n else 0.0,
        "teacher_score_ranking_agreement": rank_agreement,
    }


def _cosine(left: list[float], right: list[float]) -> float | None:
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return None
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def _run_label(label: str, games: int, limit: int, nodes: int) -> dict:
    compiled, native, profile = _ruleset(label)
    parent = LearnableMaterialCheckpoint.from_profile(
        compiled, profile, training_seed=4807000, dynamic_weights=dict(WEIGHTS)
    )
    trajectories = collect_self_play(
        compiled, native, parent,
        SelfPlayConfig(games=games, nodes_per_move=400, max_depth=6,
                       seed=4807000, epsilon=0.10, tt_megabytes=8),
    )
    td = tdleaf_update(trajectories, parent, TDLeafConfig(alpha=0.05, lambd=0.7))
    child = parent.child_checkpoint(
        board_weights=td.board_weights,
        hand_weights=td.hand_weights,
        dynamic_weights=td.dynamic_weights,
        games_seen_delta=len(trajectories),
        positions_seen_delta=td.positions_seen,
        training_updates_delta=1,
        training_config_hash=stable_sha256({"stage": "F51", "label": label}),
        training_seed=4807000,
    )
    direction = _direction(parent, child)
    effective = _native_delta(compiled, native, parent, child)
    teacher_surfaces = {}
    for budget in (20000, 40000, 80000):
        teacher_surfaces[str(budget)] = _teacher_rows(label, parent, limit, budget)
    teacher_stability = {
        "20k_vs_40k": _agreement(teacher_surfaces["20000"], teacher_surfaces["40000"]),
        "40k_vs_80k": _agreement(teacher_surfaces["40000"], teacher_surfaces["80000"]),
        "stable_threshold": 0.80,
    }
    teacher_rows = teacher_surfaces["80000"]
    if teacher_stability["40k_vs_80k"] < teacher_stability["stable_threshold"]:
        return {
            "label": label,
            "classification": "TEACHER_UNSTABLE",
            "teacher_stability": teacher_stability,
            "actual_child_native_delta": effective,
            "floating_td_direction": direction,
        }
    natural_child_comparison = _compare(label, parent, child, teacher_rows, limit, nodes)
    parent_comparison = _compare(label, parent, parent, teacher_rows, limit, nodes)
    raw_td_amplitudes = []
    block_td_amplitudes = []
    for fraction in AMPLITUDES:
        raw_candidate = _raw_scaled_direction_checkpoint(parent, direction, fraction)
        block_candidate = _scaled_direction_checkpoint(parent, direction, fraction)
        raw_td_amplitudes.append({
            "amplitude_fraction_of_full_norm": fraction,
            "native_bound_delta": _native_delta(compiled, native, parent, raw_candidate),
            "comparison": _compare(label, parent, raw_candidate, teacher_rows, limit, nodes),
        })
        block_td_amplitudes.append({
            "amplitude_fraction_of_block_norm": fraction,
            "native_bound_delta": _native_delta(compiled, native, parent, block_candidate),
            "comparison": _compare(label, parent, block_candidate, teacher_rows, limit, nodes),
        })
    finite = []
    finite_jobs = [(name, sign, fraction) for name in DYNAMIC_NAMES for sign in (-1, 1) for fraction in (0.01, 0.05, 0.10)]

    def finite_job(job):
        name, sign, fraction = job
        candidate = _dynamic_finite_difference(parent, name, sign, fraction)
        return {
            "feature": name,
            "sign": sign,
            "fraction_of_dynamic_norm": fraction,
            "native_bound_delta": _native_delta(compiled, native, parent, candidate),
            "comparison": _compare(label, parent, candidate, teacher_rows, limit, nodes),
        }

    with ThreadPoolExecutor(max_workers=min(8, max(1, os.cpu_count() or 1))) as pool:
        finite = list(pool.map(finite_job, finite_jobs))
    best = max(finite, key=lambda row: (row["comparison"]["teacher_best_move_agreement"], row["comparison"]["teacher_score_ranking_agreement"] or -1.0))
    td_dynamic = [direction["dynamic"].get(name, 0.0) for name in DYNAMIC_NAMES]
    teacher_dynamic = [best["sign"] * best["fraction_of_dynamic_norm"] * _block_norm(parent.dynamic_weights) if name == best["feature"] else 0.0 for name in DYNAMIC_NAMES]
    best_raw = max(raw_td_amplitudes, key=lambda row: row["comparison"]["teacher_best_move_agreement"])
    best_block = max(block_td_amplitudes, key=lambda row: row["comparison"]["teacher_best_move_agreement"])
    parent_agreement = parent_comparison["teacher_best_move_agreement"]
    best_agreement = best["comparison"]["teacher_best_move_agreement"]
    best_raw_agreement = best_raw["comparison"]["teacher_best_move_agreement"]
    best_block_agreement = best_block["comparison"]["teacher_best_move_agreement"]
    if natural_child_comparison["teacher_best_move_agreement"] > parent_agreement + 0.01:
        classification = "POSITIVE_LEARNED_CHILD_SIGNAL"
    elif best_raw_agreement > parent_agreement + 0.01 or best_block_agreement > parent_agreement + 0.01:
        classification = "TD_DIRECTION_GOOD_STEP_TOO_SMALL"
    elif best_agreement > parent_agreement + 0.01:
        classification = "TD_DIRECTION_GOOD_STEP_TOO_SMALL" if (_cosine(td_dynamic, teacher_dynamic) or -1.0) > 0.5 else "TD_TARGET_OR_CREDIT_ASSIGNMENT_MISALIGNED"
    elif best_agreement <= parent_agreement + 0.01:
        classification = "LOCAL_EVALUATOR_CAPACITY_STILL_LIMITING"
    else:
        classification = "TD_TARGET_OR_CREDIT_ASSIGNMENT_MISALIGNED"
    return {
        "label": label,
        "classification": classification,
        "trajectories": len(trajectories),
        "training_positions": td.positions_seen,
        "td_mean_abs_error": td.mean_abs_td_error,
        "floating_td_direction": direction,
        "actual_child_native_delta": effective,
        "teacher_stability": teacher_stability,
        "parent_teacher_comparison": parent_comparison,
        "natural_child_teacher_comparison": natural_child_comparison,
        "raw_td_amplitudes": raw_td_amplitudes,
        "block_preconditioned_td_amplitudes": block_td_amplitudes,
        "dynamic_finite_difference": finite,
        "best_local_teacher_direction": best,
        "td_dynamic_teacher_direction_cosine": _cosine(td_dynamic, teacher_dynamic),
    }


def _natural_only(label: str, previous: dict, limit: int, nodes: int) -> dict:
    compiled, native, profile = _ruleset(label)
    parent = LearnableMaterialCheckpoint.from_profile(
        compiled, profile, training_seed=4807000, dynamic_weights=dict(WEIGHTS)
    )
    direction = previous["floating_td_direction"]
    base = _blocks(parent)
    child = replace(
        parent,
        board_weights={key: base["board"].get(key, 0.0) + value for key, value in direction["board"].items()},
        hand_weights={key: base["hand"].get(key, 0.0) + value for key, value in direction["hand"].items()},
        dynamic_weights={key: base["dynamic"].get(key, 0.0) + value for key, value in direction["dynamic"].items()},
    )
    teacher_rows = _teacher_rows(label, parent, limit, 80000)
    return {
        "label": label,
        "parent_teacher_comparison": _compare(label, parent, parent, teacher_rows, limit, nodes),
        "natural_child_teacher_comparison": _compare(label, parent, child, teacher_rows, limit, nodes),
        "native_delta": _native_delta(compiled, native, parent, child),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--positions", type=int, default=16)
    parser.add_argument("--games", type=int, default=2)
    parser.add_argument("--nodes", type=int, default=2000)
    parser.add_argument("--natural-only", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.natural_only:
        previous = json.loads((OUT / "f51_results.json").read_text(encoding="utf-8"))
        result = {
            "work_order": "GENERICCHESS-F51-LEARNING-DIRECTION-AND-TARGET-DIAGNOSIS",
            "natural_child_results": [
                _natural_only(label, prior, args.positions, args.nodes)
                for label, prior in zip(
                    ("A_CANONICAL_WESTERN_CHESS", "B_CANONICAL_STANDARD_SHOGI"),
                    previous["results"],
                )
            ],
        }
        (OUT / "f51_natural_child_results.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, sort_keys=True))
        return
    started = time.perf_counter()
    result = {
        "work_order": "GENERICCHESS-F51-LEARNING-DIRECTION-AND-TARGET-DIAGNOSIS",
        "teacher": "F49 S49-M 80000-node fixed results",
        "amplitudes": AMPLITUDES,
        "results": [
            _run_label("A_CANONICAL_WESTERN_CHESS", args.games, args.positions, args.nodes),
            _run_label("B_CANONICAL_STANDARD_SHOGI", args.games, args.positions, args.nodes),
        ],
        "wall_seconds": time.perf_counter() - started,
    }
    (OUT / "f51_results.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
