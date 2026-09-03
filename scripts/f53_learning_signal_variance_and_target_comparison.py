"""F53 TD signal variance and target comparison.

The semantic evaluator and search are frozen.  F53 measures independent
TDLeaf direction variance, then compares terminal-return and deeper-search
self-distillation targets using the same five feature blocks and a single
fixed full-vector diagnostic magnitude.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from f50_generic_learnable_evaluator import (  # noqa: E402
    BUNDLE,
    WEIGHTS,
    _case,
    _native_delta,
    _ruleset,
)
from f51_learning_direction_target_diagnosis import (  # noqa: E402
    _action_key,
    _blocks,
    _block_norm,
)
from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.core.transition import initial_state  # noqa: E402
from generic_chess.learning.arena import ArenaConfig, run_arena  # noqa: E402
from generic_chess.learning.features import DYNAMIC_FEATURE_NAMES, linear_value  # noqa: E402
from generic_chess.learning.material import LearnableMaterialCheckpoint  # noqa: E402
from generic_chess.learning.selfplay import SelfPlayConfig, collect_self_play  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.learning.tdleaf import _normalized_value  # noqa: E402
from generic_chess.rules.compiler import compile_semantic_ruleset  # noqa: E402
from generic_chess.session.session import GameSession  # noqa: E402


OUT = ROOT / ".generic_chess_flow" / "f53-learning-signal-variance-and-target-comparison"
BATCHES = 4
TRAJECTORIES_PER_BATCH = 8
TRAJECTORY_NODES = 400
DISTILL_NODES = 4000
DISTILL_POINTS_PER_TRAJECTORY = 4
VALIDATION_SLICES = ((32, 16), (48, 16))
TEACHER_BUDGETS = (20000, 40000, 80000)
TEACHER_THRESHOLD = 0.80
# The first F53 probe at 5% saturated the search surface.  This smaller
# fraction is frozen and shared by every target and RuleSet; it is not tuned
# independently per candidate.
DIAGNOSTIC_FRACTION = 0.0005
TARGET_NAMES = ("tdleaf_lambda", "monte_carlo_terminal", "deep_search_distillation")


def _records(label: str, offset: int, limit: int) -> list[dict]:
    raw = json.loads(BUNDLE.read_text(encoding="utf-8"))
    return raw["observations"][label]["S49-M"]["records"][offset:offset + limit]


def _parent(label: str):
    compiled, _native, profile = _ruleset(label)
    return LearnableMaterialCheckpoint.from_profile(
        compiled, profile, training_seed=5300000, dynamic_weights=dict(WEIGHTS)
    )


def _vector(direction: dict[str, dict[str, float]]) -> list[float]:
    return [
        direction[block][key]
        for block in ("board", "hand", "dynamic")
        for key in sorted(direction[block])
    ]


def _cosine(left: dict, right: dict) -> float | None:
    a = _vector(left)
    b = _vector(right)
    left_norm = math.sqrt(sum(x * x for x in a))
    right_norm = math.sqrt(sum(x * x for x in b))
    if left_norm == 0.0 or right_norm == 0.0:
        return None
    return sum(x * y for x, y in zip(a, b)) / (left_norm * right_norm)


def _norm(direction: dict[str, dict[str, float]]) -> float:
    return math.sqrt(sum(value * value for value in _vector(direction)))


def _add(left: dict, right: dict) -> dict:
    return {
        block: {
            key: left[block].get(key, 0.0) + right[block].get(key, 0.0)
            for key in set(left[block]) | set(right[block])
        }
        for block in ("board", "hand", "dynamic")
    }


def _zero_like(parent) -> dict:
    base = _blocks(parent)
    return {block: {key: 0.0 for key in values} for block, values in base.items()}


def _scale(direction: dict, factor: float) -> dict:
    return {
        block: {key: value * factor for key, value in values.items()}
        for block, values in direction.items()
    }


def _sign_consistency(directions: list[dict]) -> dict:
    if not directions:
        return {"full": 0.0, "by_block": {}}
    result = {}
    for block in ("board", "hand", "dynamic"):
        keys = sorted(set().union(*(set(d[block]) for d in directions)))
        fractions = []
        for key in keys:
            signs = [
                1 if d[block].get(key, 0.0) > 0 else
                -1 if d[block].get(key, 0.0) < 0 else 0
                for d in directions
            ]
            nonzero = [sign for sign in signs if sign]
            if nonzero:
                fractions.append(max(nonzero.count(1), nonzero.count(-1)) / len(nonzero))
        result[block] = sum(fractions) / len(fractions) if fractions else 0.0
    keys = range(len(_vector(directions[0])))
    fractions = []
    vectors = [_vector(d) for d in directions]
    for index in keys:
        signs = [1 if v[index] > 0 else -1 if v[index] < 0 else 0 for v in vectors]
        nonzero = [sign for sign in signs if sign]
        if nonzero:
            fractions.append(max(nonzero.count(1), nonzero.count(-1)) / len(nonzero))
    result["full"] = sum(fractions) / len(fractions) if fractions else 0.0
    return {"full": result.pop("full"), "by_block": result}


def _raw_target_direction(trajectories, parent, target_kind: str, distill_targets=None) -> dict:
    """Compute an unscaled gradient direction for one target on fixed data."""
    direction = _zero_like(parent)
    value_scale = parent.value_scale
    for trajectory_index, trajectory in enumerate(trajectories):
        points = trajectory.points
        values = [
            _normalized_value(
                trajectory.leaf_features_at(point),
                parent.board_weights,
                parent.hand_weights,
                value_scale,
                trajectory.dynamic_features_at(point),
                parent.dynamic_weights,
            )
            for point in points
        ]
        eligibility = {block: {} for block in ("board", "hand", "dynamic")}
        for point_index, point in enumerate(points):
            current = values[point_index]
            if target_kind == "tdleaf_lambda":
                target = trajectory.terminal_z if point_index == len(points) - 1 else values[point_index + 1]
            elif target_kind == "monte_carlo_terminal":
                target = trajectory.terminal_z
            else:
                target = distill_targets.get((trajectory_index, point_index), trajectory.terminal_z)
            delta = target - current
            grad_scale = (1.0 - current * current) / value_scale
            for key, count in zip(trajectory.type_ids, point.leaf_feature_board):
                eligibility["board"][key] = 0.7 * eligibility["board"].get(key, 0.0) + grad_scale * count
            for key, count in zip(trajectory.type_ids, point.leaf_feature_hand):
                eligibility["hand"][key] = 0.7 * eligibility["hand"].get(key, 0.0) + grad_scale * count
            for name, feature in zip(DYNAMIC_FEATURE_NAMES, trajectory.dynamic_features_at(point).as_tuple()):
                eligibility["dynamic"][name] = 0.7 * eligibility["dynamic"].get(name, 0.0) + grad_scale * feature
            for block in ("board", "hand", "dynamic"):
                for key, value in eligibility[block].items():
                    direction[block][key] = direction[block].get(key, 0.0) + delta * value
    return direction


def _tdleaf_direction(trajectories, parent) -> dict:
    return _raw_target_direction(trajectories, parent, "tdleaf_lambda")


def _candidate(parent, direction, fraction=DIAGNOSTIC_FRACTION):
    parent_norm = math.sqrt(sum(_block_norm(values) ** 2 for values in _blocks(parent).values()))
    direction_norm = _norm(direction)
    multiplier = fraction * parent_norm / direction_norm if parent_norm and direction_norm else 0.0
    delta = _scale(direction, multiplier)
    base = _blocks(parent)
    updated = {
        block: {
            key: base[block].get(key, 0.0) + delta[block].get(key, 0.0)
            for key in set(base[block]) | set(delta[block])
        }
        for block in ("board", "hand", "dynamic")
    }
    return parent.child_checkpoint(
        board_weights=updated["board"], hand_weights=updated["hand"],
        dynamic_weights=updated["dynamic"], games_seen_delta=0,
        positions_seen_delta=0, training_updates_delta=1,
        training_config_hash=stable_sha256({"stage": "F53", "fraction": fraction}),
        training_seed=5300000,
    )


def _direction_stats(label: str, parent, directions: list[dict]) -> dict:
    compiled, native, _profile = _ruleset(label)
    rows = []
    for index, direction in enumerate(directions):
        probe = _candidate(parent, direction)
        native_delta = _native_delta(compiled, native, parent, probe)
        rows.append({
            "batch": index,
            "full_norm": _norm(direction),
            "block_norms": {block: _block_norm(direction[block]) for block in ("board", "hand", "dynamic")},
            "native_effective_parameter_count": sum(
                abs(value) > 0 for block in ("board", "hand", "dynamic") for value in native_delta[block]["delta"]
            ),
            "native_effective_parameter_count_by_block": {
                block: sum(abs(value) > 0 for value in native_delta[block]["delta"])
                for block in ("board", "hand", "dynamic")
            },
        })
    pairwise = []
    for i in range(len(directions)):
        for j in range(i + 1, len(directions)):
            pairwise.append({"left": i, "right": j, "full_cosine": _cosine(directions[i], directions[j]), "block_cosine": {
                block: _cosine(
                    {block: directions[i][block], **{b: {} for b in ("board", "hand", "dynamic") if b != block}},
                    {block: directions[j][block], **{b: {} for b in ("board", "hand", "dynamic") if b != block}},
                ) for block in ("board", "hand", "dynamic")
            }})
    return {"batches": rows, "pairwise": pairwise, "sign_consistency": _sign_consistency(directions)}


def _cumulative_directions(directions: list[dict], parent) -> dict:
    output = {}
    aggregate = _zero_like(parent)
    for count, direction in zip((8, 16, 24, 32), directions):
        aggregate = _add(aggregate, direction)
        output[str(count)] = {
            "full_norm": _norm(aggregate),
            "block_norms": {block: _block_norm(aggregate[block]) for block in ("board", "hand", "dynamic")},
            "cosine_to_previous": None if count == 8 else _cosine(aggregate, previous),
        }
        previous = aggregate
    return output


def _teacher_rows(label: str, parent, records: list[dict], nodes: int) -> list[dict]:
    compiled, native, _profile = _ruleset(label)

    def run(record):
        row = _case(compiled, native, record, parent, nodes)
        return {"action_key": _action_key(row["action"]), "score": row["score"]}

    with ThreadPoolExecutor(max_workers=min(8, len(records) or 1)) as pool:
        return list(pool.map(run, records))


def _compare(label: str, parent, candidate, records: list[dict], teacher_rows: list[dict], nodes: int) -> dict:
    compiled, native, _profile = _ruleset(label)

    def run(record, checkpoint):
        return _case(compiled, native, record, checkpoint, nodes)

    workers = min(8, len(records) or 1)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        candidate_rows = list(pool.map(lambda record: run(record, candidate), records))
        parent_rows = candidate_rows if candidate.checkpoint_id == parent.checkpoint_id else list(pool.map(lambda record: run(record, parent), records))
    teacher_actions = [_action_key(row["action_key"]) for row in teacher_rows]
    candidate_actions = [_action_key(row["action"]) for row in candidate_rows]
    parent_actions = [_action_key(row["action"]) for row in parent_rows]
    n = len(records)
    return {
        "positions": n,
        "teacher_best_move_agreement": sum(a == b for a, b in zip(candidate_actions, teacher_actions)) / n if n else 0.0,
        "parent_teacher_best_move_agreement": sum(a == b for a, b in zip(parent_actions, teacher_actions)) / n if n else 0.0,
        "move_flip_rate_vs_parent": sum(a != b for a, b in zip(candidate_actions, parent_actions)) / n if n else 0.0,
        "mean_abs_score_change_vs_parent": sum(abs(a["score"] - b["score"]) for a, b in zip(parent_rows, candidate_rows)) / n if n else 0.0,
    }


def _distill_target_for_point(compiled, native, parent, trajectory, point_index: int):
    session = GameSession(compiled)
    for action in trajectory.actions[:trajectory.points[point_index].ply]:
        session.submit(action)
    for action in trajectory.points[point_index].pv:
        if session.result.status.value != "ongoing":
            break
        session.submit(action)
    if session.result.status.value != "ongoing":
        winner = session.result.winner
        return 0.0 if winner is None else (1.0 if winner == 0 else -1.0)
    result = __import__("generic_chess.native.semantic_engine", fromlist=["SemanticSearchEngine"]).SemanticSearchEngine(
        compiled, native, checkpoint=parent, tt_megabytes=8
    ).search(session, SearchLimits(max_depth=12, max_nodes=DISTILL_NODES, quiescence_max_depth=0))
    return math.tanh(result.score / parent.value_scale) if parent.value_scale else 0.0


def _distill_targets(compiled, native, parent, trajectories):
    jobs = [
        (trajectory_index, point_index)
        for trajectory_index, trajectory in enumerate(trajectories)
        for point_index in range(min(DISTILL_POINTS_PER_TRAJECTORY, len(trajectory.points)))
    ]

    def run(job):
        trajectory_index, point_index = job
        return job, _distill_target_for_point(compiled, native, parent, trajectories[trajectory_index], point_index)

    with ThreadPoolExecutor(max_workers=min(8, len(jobs) or 1)) as pool:
        return dict(pool.map(run, jobs))


def _learn_label(label: str, batch_trajectories: list[list], validation_nodes: int) -> dict:
    compiled, native, _profile = _ruleset(label)
    parent = _parent(label)
    td_directions = [_tdleaf_direction(trajectories, parent) for trajectories in batch_trajectories]
    variance = _direction_stats(label, parent, td_directions)
    cumulative = _cumulative_directions(td_directions, parent)
    distill_by_batch = []
    target_directions = {name: [] for name in TARGET_NAMES}
    for trajectories in batch_trajectories:
        distill_targets = _distill_targets(compiled, native, parent, trajectories)
        distill_values = list(distill_targets.values())
        distill_by_batch.append({
            "label_count": len(distill_values),
            "label_min": min(distill_values) if distill_values else None,
            "label_max": max(distill_values) if distill_values else None,
            "label_mean": sum(distill_values) / len(distill_values) if distill_values else None,
        })
        target_directions["tdleaf_lambda"].append(_tdleaf_direction(trajectories, parent))
        target_directions["monte_carlo_terminal"].append(_raw_target_direction(trajectories, parent, "monte_carlo_terminal"))
        target_directions["deep_search_distillation"].append(_raw_target_direction(trajectories, parent, "deep_search_distillation", distill_targets))
    records_by_slice = {
        f"{offset}:{offset + count}": _records(label, offset, count)
        for offset, count in VALIDATION_SLICES
    }
    teacher_surfaces = {
        key: {str(budget): _teacher_rows(label, parent, records, budget) for budget in TEACHER_BUDGETS}
        for key, records in records_by_slice.items()
    }
    teacher_stability = {
        key: {
            "20k_vs_40k": sum(_action_key(a["action_key"]) == _action_key(b["action_key"]) for a, b in zip(surface["20000"], surface["40000"])) / len(surface["20000"]),
            "40k_vs_80k": sum(_action_key(a["action_key"]) == _action_key(b["action_key"]) for a, b in zip(surface["40000"], surface["80000"])) / len(surface["40000"]),
        }
        for key, surface in teacher_surfaces.items()
    }
    target_results = {}
    aggregate_directions = {}
    for name in TARGET_NAMES:
        aggregate = _zero_like(parent)
        for direction in target_directions[name]:
            aggregate = _add(aggregate, direction)
        aggregate_directions[name] = aggregate
        candidate = _candidate(parent, aggregate)
        native_delta = _native_delta(compiled, native, parent, candidate)
        target_results[name] = {
            "direction_norm": _norm(aggregate),
            "direction_block_norms": {block: _block_norm(aggregate[block]) for block in ("board", "hand", "dynamic")},
            "native_effective_parameter_count": sum(
                abs(value) > 0 for block in ("board", "hand", "dynamic") for value in native_delta[block]["delta"]
            ),
            "validation": {
                key: _compare(label, parent, candidate, records_by_slice[key], teacher_surfaces[key]["80000"], validation_nodes)
                for key in records_by_slice
            },
            "floating_delta": {
                block: {
                    key: candidate_block_value - parent_block_value
                    for key, candidate_block_value in candidate_values.items()
                    for parent_block_value in [ _blocks(parent)[block].get(key, 0.0) ]
                }
                for block, candidate_values in _blocks(candidate).items()
            },
        }
    target_cosines = {
        left: {right: _cosine(aggregate_directions[left], aggregate_directions[right])
               for right in TARGET_NAMES if right != left}
        for left in TARGET_NAMES
    }
    target_direction_distances = {
        left: {
            right: None if target_cosines[left][right] is None else math.sqrt(
                max(0.0, 2.0 - 2.0 * target_cosines[left][right])
            )
            for right in target_cosines[left]
        }
        for left in TARGET_NAMES
    }
    target_improves = any(
        comparison["teacher_best_move_agreement"] > comparison["parent_teacher_best_move_agreement"] + 0.01
        and comparison["move_flip_rate_vs_parent"] > 0.0
        for target in target_results.values()
        for comparison in target["validation"].values()
    )
    high_variance = (
        variance["sign_consistency"]["full"] < 0.75
        or any(
            pair["full_cosine"] is not None and pair["full_cosine"] < 0.25
            for pair in variance["pairwise"]
        )
    )
    return {
        "label": label,
        "batch_count": len(batch_trajectories),
        "trajectories_per_batch": [len(batch) for batch in batch_trajectories],
        "variance": variance,
        "cumulative_directions": cumulative,
        "distill_points_by_batch": distill_by_batch,
        "teacher_stability": teacher_stability,
        "target_direction_cosines": target_cosines,
        "target_direction_unit_distances": target_direction_distances,
        "target_results": target_results,
        "classification": (
            "TD_SIGNAL_HIGH_VARIANCE" if high_variance
            else "TARGET_DIRECTION_GENERALIZES" if target_improves
            else "TD_TARGET_OR_CREDIT_ASSIGNMENT_MISALIGNED"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games-per-batch", type=int, default=TRAJECTORIES_PER_BATCH)
    parser.add_argument("--batches", type=int, default=BATCHES)
    parser.add_argument("--validation-nodes", type=int, default=2000)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    jobs = []
    for label_index, label in enumerate(("A_CANONICAL_WESTERN_CHESS", "B_CANONICAL_STANDARD_SHOGI")):
        compiled, native, profile = _ruleset(label)
        parent = LearnableMaterialCheckpoint.from_profile(compiled, profile, training_seed=5300000, dynamic_weights=dict(WEIGHTS))
        for batch_index in range(args.batches):
            jobs.append((label, compiled, native, parent, label_index, batch_index))

    def collect(job):
        label, compiled, native, parent, label_index, batch_index = job
        trajectories = collect_self_play(
            compiled, native, parent,
            SelfPlayConfig(games=args.games_per_batch, nodes_per_move=TRAJECTORY_NODES,
                           max_depth=6, seed=5300000 + label_index * 100000 + batch_index * 1000,
                           epsilon=0.10, tt_megabytes=8),
        )
        return label, batch_index, trajectories

    with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as pool:
        collected = list(pool.map(collect, jobs))
    grouped = {label: [None] * args.batches for label in ("A_CANONICAL_WESTERN_CHESS", "B_CANONICAL_STANDARD_SHOGI")}
    for label, batch_index, trajectories in collected:
        grouped[label][batch_index] = trajectories
    results = [
        _learn_label(label, grouped[label], args.validation_nodes)
        for label in grouped
    ]
    result = {
        "work_order": "GENERICCHESS-F53-LEARNING-SIGNAL-VARIANCE-AND-TARGET-COMPARISON",
        "batch_count": args.batches,
        "trajectories_per_batch": args.games_per_batch,
        "diagnostic_fraction": DIAGNOSTIC_FRACTION,
        "validation_slices": VALIDATION_SLICES,
        "results": results,
        "wall_seconds": time.perf_counter() - started,
    }
    (OUT / "f53_results.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
