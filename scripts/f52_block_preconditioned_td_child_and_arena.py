"""F52 generic block-preconditioned TD child and arena experiment.

F51 selected one common 5% block-relative update as the only candidate rule.
This runner freezes the current-v2 semantic search/evaluator and tests that
rule on a disjoint S49-M holdout before running the gated paired arena.
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
    _direction,
    _teacher_rows as _f51_teacher_rows,
)
from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.core.identity import position_identity_key  # noqa: E402
from generic_chess.core.actions import action_to_dict  # noqa: E402
from generic_chess.learning.arena import (  # noqa: E402
    _engine_for,
)
from generic_chess.learning.features import DYNAMIC_FEATURE_NAMES  # noqa: E402
from generic_chess.learning.material import LearnableMaterialCheckpoint  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.learning.selfplay import SelfPlayConfig, collect_self_play  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.learning.statistics import bootstrap_pair_mean_ci  # noqa: E402
from generic_chess.learning.tdleaf import TDLeafConfig, tdleaf_update  # noqa: E402
from generic_chess.rules.compiler import compile_ruleset_for_execution  # noqa: E402
from generic_chess.session.session import GameSession  # noqa: E402


OUT = ROOT / ".generic_chess_flow" / "f52-block-preconditioned-td-child-and-arena"
HOLDOUT_OFFSET = 16
HOLDOUT_COUNT = 16
PRECONDITION_FRACTION = 0.05
TEACHER_BUDGETS = (20000, 40000, 80000)
TEACHER_STABILITY_THRESHOLD = 0.80


def _holdout_records(label: str, limit: int = HOLDOUT_COUNT) -> list[dict]:
    raw = json.loads(BUNDLE.read_text(encoding="utf-8"))
    records = raw["observations"][label]["S49-M"]["records"]
    return records[HOLDOUT_OFFSET:HOLDOUT_OFFSET + limit]


def _teacher_rows(label: str, records: list[dict], nodes: int) -> list[dict]:
    compiled, native, _profile = _ruleset(label)

    def run(record):
        row = _case(compiled, native, record, _parent_for(label), nodes)
        return {"action_key": _action_key(row["action"]), "score": row["score"]}

    workers = min(8, max(1, os.cpu_count() or 1), len(records) or 1)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(run, records))


def _parent_for(label: str):
    compiled, _native, profile = _ruleset(label)
    return LearnableMaterialCheckpoint.from_profile(
        compiled, profile, training_seed=4807000, dynamic_weights=dict(WEIGHTS)
    )


def _agreement(left: list[dict], right: list[dict]) -> float:
    if not left:
        return 0.0
    return sum(
        _action_key(a["action_key"]) == _action_key(b["action_key"])
        for a, b in zip(left, right)
    ) / len(left)


def _floating_delta(parent, child) -> dict[str, dict[str, float]]:
    before = _blocks(parent)
    after = _blocks(child)
    return {
        block: {
            key: after[block].get(key, 0.0) - before[block].get(key, 0.0)
            for key in sorted(set(before[block]) | set(after[block]))
        }
        for block in before
    }


def precondition_td_direction(parent, direction, fraction: float = PRECONDITION_FRACTION):
    """Return a child with one common L2 fraction per nonzero TD block."""
    if not (0.0 < fraction <= 1.0):
        raise ValueError("precondition fraction must be in (0, 1]")
    base = _blocks(parent)
    updated: dict[str, dict[str, float]] = {}
    for block in ("board", "hand", "dynamic"):
        values = dict(base[block])
        dnorm = _block_norm(direction[block])
        norm = _block_norm(base[block])
        if dnorm > 0.0 and norm > 0.0:
            multiplier = fraction * norm / dnorm
            for key, value in direction[block].items():
                values[key] = base[block].get(key, 0.0) + multiplier * value
        updated[block] = values
    return parent.child_checkpoint(
        board_weights=updated["board"],
        hand_weights=updated["hand"],
        dynamic_weights=updated["dynamic"],
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=stable_sha256({
            "stage": "F52",
            "rule": "block-preconditioned-td",
            "fraction": fraction,
        }),
        training_seed=4807000,
    )


def _compare(label: str, records: list[dict], parent, candidate, teacher_rows: list[dict], nodes: int) -> dict:
    compiled, native, _profile = _ruleset(label)

    def run(record):
        return _case(compiled, native, record, candidate, nodes)

    workers = min(8, max(1, os.cpu_count() or 1), len(records) or 1)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        candidate_rows = list(pool.map(run, records))
    if candidate.checkpoint_id == parent.checkpoint_id:
        parent_rows = candidate_rows
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            parent_rows = list(pool.map(
                lambda record: _case(compiled, native, record, parent, nodes), records
            ))
    teacher_actions = [_action_key(row["action_key"]) for row in teacher_rows]
    candidate_actions = [_action_key(row["action"]) for row in candidate_rows]
    parent_actions = [_action_key(row["action"]) for row in parent_rows]
    candidate_scores = [row["score"] for row in candidate_rows]
    parent_scores = [row["score"] for row in parent_rows]
    n = len(candidate_rows)
    return {
        "positions": n,
        "workers": workers,
        "teacher_best_move_agreement": sum(
            a == b for a, b in zip(candidate_actions, teacher_actions)
        ) / n if n else 0.0,
        "parent_teacher_best_move_agreement": sum(
            a == b for a, b in zip(parent_actions, teacher_actions)
        ) / n if n else 0.0,
        "move_flip_rate_vs_parent": sum(
            a != b for a, b in zip(candidate_actions, parent_actions)
        ) / n if n else 0.0,
        "mean_score_change_vs_parent": sum(
            b - a for a, b in zip(parent_scores, candidate_scores)
        ) / n if n else 0.0,
        "mean_abs_score_change_vs_parent": sum(
            abs(b - a) for a, b in zip(parent_scores, candidate_scores)
        ) / n if n else 0.0,
    }


def _effective_changed(delta: dict) -> bool:
    return any(
        value
        for block in ("board", "hand", "dynamic")
        for value in delta[block]["delta"]
    )


def _play_game(compiled, native, parent, child, opening, child_owner: int, nodes: int):
    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    opening_key = position_identity_key(session.state.position, compiled)
    parent_engine = _engine_for(compiled, native, parent, 8)
    child_engine = _engine_for(compiled, native, child, 8)
    depth_values: list[int] = []
    node_values: list[int] = []
    plies = 0
    while session.result.status.value == "ongoing":
        side = session.state.position.side_to_move
        result = (child_engine if side == child_owner else parent_engine).search(
            session,
            SearchLimits(max_depth=12, max_nodes=nodes, quiescence_max_depth=0),
        )
        if getattr(result, "declaration_id", None) is not None:
            session.declare(result.declaration_id)
            break
        if result.action is None:
            raise RuntimeError(f"no action on ongoing arena position: {result.termination_reason}")
        depth_values.append(result.completed_depth)
        node_values.append(result.nodes)
        session.submit(result.action)
        plies += 1
    winner = session.result.winner
    points = 0.5 if winner is None else (1.0 if winner == child_owner else 0.0)
    return {
        "opening_id": opening.final_position_key,
        "opening_position_key": opening_key,
        "child_owner": child_owner,
        "winner": winner,
        "result": session.result.status.value,
        "plies": plies,
        "child_points": points,
        "completed_depth_sum": sum(depth_values),
        "completed_depth_count": len(depth_values),
        "nodes_sum": sum(node_values),
        "nodes_count": len(node_values),
    }


def _arena(compiled, native, parent, child, pairs: int, nodes: int) -> dict:
    openings = generate_arena_openings(
        compiled, count=pairs, seed=480752, min_plies=2, max_plies=6
    )

    def play_pair(pair_index: int):
        opening = openings.openings[pair_index]
        return (
            _play_game(compiled, native, parent, child, opening, 0, nodes),
            _play_game(compiled, native, parent, child, opening, 1, nodes),
        )

    workers = min(4, pairs)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pair_rows = list(pool.map(play_pair, range(pairs)))
    pair_scores = tuple(
        (left["child_points"] + right["child_points"]) / 2.0
        for left, right in pair_rows
    )
    wins = draws = losses = 0
    depth_sum = depth_count = nodes_sum = nodes_count = 0
    terminations: dict[str, int] = {}
    for left, right in pair_rows:
        for game in (left, right):
            points = game["child_points"]
            wins += points == 1.0
            draws += points == 0.5
            losses += points == 0.0
            depth_sum += game["completed_depth_sum"]
            depth_count += game["completed_depth_count"]
            nodes_sum += game["nodes_sum"]
            nodes_count += game["nodes_count"]
            terminations[game["result"]] = terminations.get(game["result"], 0) + 1
    low, high = bootstrap_pair_mean_ci(list(pair_scores))
    return {
        "pair_count": pairs,
        "game_count": 2 * pairs,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "mean_paired_score": sum(pair_scores) / len(pair_scores),
        "bootstrap_low": low,
        "bootstrap_high": high,
        "average_completed_depth": depth_sum / depth_count if depth_count else 0.0,
        "average_nodes_per_move": nodes_sum / nodes_count if nodes_count else 0.0,
        "termination_counts": terminations,
        "workers": workers,
        "nodes_per_move_limit": nodes,
        "pair_scores": pair_scores,
    }


def _learn(label: str, games: int, holdout_count: int, search_nodes: int, arena_pairs: int) -> dict:
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
    natural = parent.child_checkpoint(
        board_weights=td.board_weights,
        hand_weights=td.hand_weights,
        dynamic_weights=td.dynamic_weights,
        games_seen_delta=len(trajectories),
        positions_seen_delta=td.positions_seen,
        training_updates_delta=1,
        training_config_hash=stable_sha256({"stage": "F52-natural", "label": label}),
        training_seed=4807000,
    )
    direction = _direction(parent, natural)
    preconditioned = precondition_td_direction(parent, direction)
    records = _holdout_records(label, holdout_count)
    teacher_surfaces = {
        str(budget): _teacher_rows(label, records, budget)
        for budget in TEACHER_BUDGETS
    }
    teacher_stability = {
        "20k_vs_40k": _agreement(teacher_surfaces["20000"], teacher_surfaces["40000"]),
        "40k_vs_80k": _agreement(teacher_surfaces["40000"], teacher_surfaces["80000"]),
        "stable_threshold": TEACHER_STABILITY_THRESHOLD,
    }
    teacher_rows = teacher_surfaces["80000"]
    natural_compare = _compare(label, records, parent, natural, teacher_rows, search_nodes)
    parent_compare = _compare(label, records, parent, parent, teacher_rows, search_nodes)
    preconditioned_compare = _compare(label, records, parent, preconditioned, teacher_rows, search_nodes)
    natural_delta = _native_delta(compiled, native, parent, natural)
    preconditioned_delta = _native_delta(compiled, native, parent, preconditioned)
    signal = (
        teacher_stability["40k_vs_80k"] >= TEACHER_STABILITY_THRESHOLD
        and _effective_changed(preconditioned_delta)
        and preconditioned_compare["move_flip_rate_vs_parent"] > 0.0
        and preconditioned_compare["teacher_best_move_agreement"] > parent_compare["teacher_best_move_agreement"]
    )
    result = {
        "label": label,
        "holdout_offset": HOLDOUT_OFFSET,
        "holdout_count": len(records),
        "teacher_stability": teacher_stability,
        "teacher_search_budgets": TEACHER_BUDGETS,
        "parent_teacher_comparison": parent_compare,
        "natural_child_teacher_comparison": natural_compare,
        "preconditioned_child_teacher_comparison": preconditioned_compare,
        "floating_natural_delta": _floating_delta(parent, natural),
        "floating_preconditioned_delta": _floating_delta(parent, preconditioned),
        "native_natural_delta": natural_delta,
        "native_preconditioned_delta": preconditioned_delta,
        "td_mean_abs_error": td.mean_abs_td_error,
        "training_positions": td.positions_seen,
        "precondition_fraction": PRECONDITION_FRACTION,
        "arena_gate": {
            "teacher_stable": teacher_stability["40k_vs_80k"] >= TEACHER_STABILITY_THRESHOLD,
            "native_effective": _effective_changed(preconditioned_delta),
            "decision_changed": preconditioned_compare["move_flip_rate_vs_parent"] > 0.0,
            "teacher_improved": preconditioned_compare["teacher_best_move_agreement"] > parent_compare["teacher_best_move_agreement"],
            "passed": signal,
        },
        "classification": "F52_PRECONDITIONING_SIGNAL_GENERALIZES" if signal else "F51_PRECONDITIONING_SIGNAL_DID_NOT_GENERALIZE",
        "arena": None,
        "confirmation_arena": None,
    }
    if signal:
        result["arena"] = _arena(compiled, native, parent, preconditioned, arena_pairs, 2000)
        if result["arena"]["mean_paired_score"] > 0.5 and result["arena"]["bootstrap_low"] > 0.5:
            result["confirmation_arena"] = _arena(compiled, native, parent, preconditioned, 32, 2000)
    return result


def _generated_sanity() -> dict:
    sys.path.insert(0, str(ROOT / "tests"))
    from phase19c1_native_semantic_fixtures import semantic_corpus
    from generic_chess.native.compiler import compile_native_semantic_rules
    from generic_chess.native.semantic_engine import SemanticSearchEngine

    compiled = dict(semantic_corpus())["weird_0"]
    native = compile_native_semantic_rules(compiled)
    profile = __import__("generic_chess.ai.evaluation.profile", fromlist=["build_ruleset_profile"]).build_ruleset_profile(
        compiled._legacy_compiled, EvaluationConfig()
    )
    parent = LearnableMaterialCheckpoint.from_profile(compiled, profile, dynamic_weights=dict(WEIGHTS))
    trajectories = collect_self_play(
        compiled, native, parent,
        SelfPlayConfig(games=1, nodes_per_move=20, max_depth=1, seed=480709,
                       epsilon=1.0, tt_megabytes=0, max_plies=2),
    )
    td = tdleaf_update(trajectories, parent, TDLeafConfig(alpha=0.01, lambd=0.7))
    natural = replace(parent, board_weights=td.board_weights, hand_weights=td.hand_weights,
                      dynamic_weights=td.dynamic_weights)
    preconditioned = precondition_td_direction(parent, _direction(parent, natural))
    action = SemanticSearchEngine(compiled, native, checkpoint=preconditioned, tt_megabytes=0).search(
        GameSession(compiled), SearchLimits(max_depth=1, max_nodes=100, quiescence_max_depth=0)
    ).action
    return {
        "ruleset": "generated_semantic_weird_0",
        "native_executable": native.native_executable,
        "precondition_fraction": PRECONDITION_FRACTION,
        "action_present": action is not None,
        "td_positions": td.positions_seen,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--positions", type=int, default=HOLDOUT_COUNT)
    parser.add_argument("--games", type=int, default=2)
    parser.add_argument("--arena-pairs", type=int, default=8)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    result = {
        "work_order": "GENERICCHESS-F52-BLOCK-PRECONDITIONED-TD-CHILD-AND-ARENA",
        "parent_checkpoint": "current-v2-reconstructed-from-seed-4807000",
        "holdout": {"offset": HOLDOUT_OFFSET, "count": args.positions},
        "precondition_fraction": PRECONDITION_FRACTION,
        "results": [
            _learn("A_CANONICAL_WESTERN_CHESS", args.games, args.positions, 2000, args.arena_pairs),
            _learn("B_CANONICAL_STANDARD_SHOGI", args.games, args.positions, 2000, args.arena_pairs),
        ],
        "generated_sanity": _generated_sanity(),
        "wall_seconds": time.perf_counter() - started,
    }
    (OUT / "f52_results.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
