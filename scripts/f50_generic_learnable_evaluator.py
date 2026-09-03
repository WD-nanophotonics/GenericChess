"""F50 generic dynamic evaluator expansion experiment.

The runner deliberately keeps evidence in ``.generic_chess_flow``.  It
replays the accepted F49 stable corpora, measures dynamic-feature leverage,
then performs a small deterministic TDLeaf update and paired arena.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.learning.arena import ArenaConfig, run_arena
from generic_chess.learning.features import DYNAMIC_FEATURE_NAMES
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.selfplay import SelfPlayConfig, collect_self_play
from generic_chess.learning.serialization import stable_sha256
from generic_chess.learning.tdleaf import TDLeafConfig, tdleaf_update
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import dynamic_features as native_dynamic_features
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / ".generic_chess_flow" / "f49-semantic-reentry-authoritative" / "f49_evidence_bundle.json"
OUT = ROOT / ".generic_chess_flow" / "f50-generic-learnable-evaluator"
WEIGHTS = {
    "mobility": EvaluationConfig().dynamic_mobility_weight,
    "promotion_potential": EvaluationConfig().promotion_potential_weight,
    "anchor_safety": EvaluationConfig().anchor_escape_weight,
}


def _records(label: str, limit: int) -> list[dict]:
    raw = json.loads(BUNDLE.read_text(encoding="utf-8"))
    return raw["observations"][label]["S49-M"]["records"][:limit]


def _ruleset(label: str):
    ruleset = (
        build_western_chess_ruleset()
        if label == "A_CANONICAL_WESTERN_CHESS"
        else build_standard_shogi_ruleset()
    )
    compiled = compile_semantic_ruleset(ruleset)
    native = compile_native_semantic_rules(compiled)
    profile = build_ruleset_profile(compile_ruleset_for_execution(ruleset), EvaluationConfig())
    return compiled, native, profile


def _session(compiled, record: dict) -> GameSession:
    session = GameSession(compiled)
    for payload in record["action_history"]:
        session.submit(action_from_dict(payload))
    return session


def _case(compiled, native, record, checkpoint, nodes: int) -> dict:
    session = _session(compiled, record)
    packed = pack_semantic_search_position(compiled, native, session)
    feature = native_dynamic_features(native, packed)
    started = time.perf_counter()
    result = SemanticSearchEngine(
        compiled, native, checkpoint=checkpoint, tt_megabytes=8
    ).search(session, SearchLimits(max_depth=12, max_nodes=nodes, quiescence_max_depth=0))
    elapsed = time.perf_counter() - started
    return {
        "action": None if result.action is None else action_to_dict(result.action),
        "score": result.score,
        "feature": list(feature),
        "feature_value": sum(
            checkpoint.dynamic_weights.get(name, 0.0) * value
            for name, value in zip(DYNAMIC_FEATURE_NAMES, feature)
        ),
        "nodes": result.nodes,
        "elapsed_seconds": elapsed,
        "completed_depth": result.completed_depth,
    }


def _prescreen(label: str, limit: int, nodes: int = 2000) -> dict:
    compiled, native, profile = _ruleset(label)
    parent = LearnableMaterialCheckpoint.from_profile(compiled, profile)
    cases = _records(label, limit)
    variants = {
        "parent_v1": parent,
        **{
            name: replace(parent, dynamic_weights={name: weight})
            for name, weight in WEIGHTS.items()
        },
        "joint_v2": replace(parent, dynamic_weights=dict(WEIGHTS)),
    }
    jobs = [(variant, index, record) for variant, checkpoint in variants.items()
            for index, record in enumerate(cases)]

    def run(job):
        variant, index, record = job
        return variant, index, _case(compiled, native, record, variants[variant], nodes)

    workers = min(8, max(1, os.cpu_count() or 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(run, jobs))
    grouped: dict[str, list[dict]] = {name: [None] * len(cases) for name in variants}
    for variant, index, row in rows:
        grouped[variant][index] = row
    base = grouped["parent_v1"]
    summary = {}
    for variant, values in grouped.items():
        flips = sum(values[i]["action"] != base[i]["action"] for i in range(len(base)))
        score_changes = [values[i]["score"] - base[i]["score"] for i in range(len(base))]
        feature_changes = [values[i]["feature_value"] for i in range(len(base))]
        summary[variant] = {
            "flip_rate": flips / len(base) if base else 0.0,
            "mean_score_change": sum(score_changes) / len(score_changes) if score_changes else 0.0,
            "mean_feature_value": sum(feature_changes) / len(feature_changes) if feature_changes else 0.0,
            "nodes": sum(row["nodes"] for row in values),
            "seconds": sum(row["elapsed_seconds"] for row in values),
            "native_nps": (
                sum(row["nodes"] for row in values) /
                sum(row["elapsed_seconds"] for row in values)
                if sum(row["elapsed_seconds"] for row in values) else 0.0
            ),
        }
    return {"label": label, "positions": len(cases), "nodes_per_search": nodes,
            "workers": workers, "variants": summary}


def _native_delta(compiled, native, parent, child) -> dict:
    parent_values = SemanticSearchEngine(
        compiled, native, checkpoint=parent, tt_megabytes=0
    ).native_evaluator_values
    child_values = SemanticSearchEngine(
        compiled, native, checkpoint=child, tt_megabytes=0
    ).native_evaluator_values
    return {
        "scale": {"parent": parent_values["scale"], "child": child_values["scale"]},
        "board": {
            "parent": list(parent_values["board"]),
            "child": list(child_values["board"]),
            "delta": [b - a for a, b in zip(parent_values["board"], child_values["board"])],
        },
        "hand": {
            "parent": list(parent_values["hand"]),
            "child": list(child_values["hand"]),
            "delta": [b - a for a, b in zip(parent_values["hand"], child_values["hand"])],
        },
        "dynamic": {
            "parent": list(parent_values["dynamic"]),
            "child": list(child_values["dynamic"]),
            "delta": [b - a for a, b in zip(parent_values["dynamic"], child_values["dynamic"])],
        },
    }


def _stable_checkpoint_comparison(label: str, parent, child, limit: int = 16, nodes: int = 2000, workers: int | None = None) -> dict:
    compiled, native, _profile = _ruleset(label)
    cases = _records(label, limit)
    def compare(record):
        before = _case(compiled, native, record, parent, nodes)
        after = _case(compiled, native, record, child, nodes)
        return before, after
    worker_count = min(workers or 8, max(1, os.cpu_count() or 1), len(cases) or 1)
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        rows = list(pool.map(compare, cases))
    score_delta = [after["score"] - before["score"] for before, after in rows]
    return {
        "positions": len(rows),
        "move_flip_rate": (
            sum(before["action"] != after["action"] for before, after in rows) / len(rows)
            if rows else 0.0
        ),
        "mean_score_difference": sum(score_delta) / len(score_delta) if score_delta else 0.0,
        "score_difference_min": min(score_delta) if score_delta else 0,
        "score_difference_max": max(score_delta) if score_delta else 0,
        "workers": worker_count,
    }


def _amplitude_surface(label: str, parent, child, limit: int = 16, nodes: int = 2000) -> list[dict]:
    compiled, native, _profile = _ruleset(label)
    cases = _records(label, limit)
    board_delta = {
        key: child.board_weights.get(key, 0.0) - parent.board_weights.get(key, 0.0)
        for key in set(parent.board_weights) | set(child.board_weights)
    }
    hand_delta = {
        key: child.hand_weights.get(key, 0.0) - parent.hand_weights.get(key, 0.0)
        for key in set(parent.hand_weights) | set(child.hand_weights)
    }
    dynamic_delta = {
        key: child.dynamic_weights.get(key, 0.0) - parent.dynamic_weights.get(key, 0.0)
        for key in set(parent.dynamic_weights) | set(child.dynamic_weights)
    }
    amplitudes = (0.25, 0.5, 1.0, 2.0, 4.0)

    def measure(amplitude):
        candidate = replace(
            parent,
            board_weights={key: parent.board_weights.get(key, 0.0) + amplitude * value for key, value in board_delta.items()},
            hand_weights={key: parent.hand_weights.get(key, 0.0) + amplitude * value for key, value in hand_delta.items()},
            dynamic_weights={key: parent.dynamic_weights.get(key, 0.0) + amplitude * value for key, value in dynamic_delta.items()},
        )
        comparison = _stable_checkpoint_comparison(label, parent, candidate, limit, nodes, workers=1)
        comparison["amplitude"] = amplitude
        return comparison

    with ThreadPoolExecutor(max_workers=min(len(amplitudes), max(1, os.cpu_count() or 1))) as pool:
        return list(pool.map(measure, amplitudes))


def _learn_and_arena(label: str, games: int, arena_pairs: int) -> dict:
    compiled, native, profile = _ruleset(label)
    parent = LearnableMaterialCheckpoint.from_profile(
        compiled, profile, training_seed=4807000,
        dynamic_weights=dict(WEIGHTS),
    )
    started = time.perf_counter()
    trajectories = collect_self_play(
        compiled, native, parent,
        SelfPlayConfig(games=games, nodes_per_move=400, max_depth=6,
                       seed=4807000, epsilon=0.10, tt_megabytes=8),
    )
    td = tdleaf_update(trajectories, parent, TDLeafConfig(alpha=0.05, lambd=0.7))
    training_seconds = time.perf_counter() - started
    child = parent.child_checkpoint(
        board_weights=td.board_weights,
        hand_weights=td.hand_weights,
        dynamic_weights=td.dynamic_weights,
        games_seen_delta=len(trajectories),
        positions_seen_delta=td.positions_seen,
        training_updates_delta=1,
        training_config_hash=stable_sha256({"stage": "F50", "label": label}),
        training_seed=4807000,
    )
    effective_delta = _native_delta(compiled, native, parent, child)
    floating_delta = {
        "board": {
            key: child.board_weights.get(key, 0.0) - parent.board_weights.get(key, 0.0)
            for key in sorted(set(parent.board_weights) | set(child.board_weights))
        },
        "hand": {
            key: child.hand_weights.get(key, 0.0) - parent.hand_weights.get(key, 0.0)
            for key in sorted(set(parent.hand_weights) | set(child.hand_weights))
        },
        "dynamic": {
            key: child.dynamic_weights.get(key, 0.0) - parent.dynamic_weights.get(key, 0.0)
            for key in sorted(set(parent.dynamic_weights) | set(child.dynamic_weights))
        },
    }
    effective_changed = any(
        value
        for group in (effective_delta["board"], effective_delta["hand"], effective_delta["dynamic"])
        for value in group["delta"]
    )
    if not effective_changed:
        return {
            "label": label,
            "status": "QUANTIZATION_NOOP",
            "floating_checkpoint_delta": floating_delta,
            "native_bound_evaluator_delta": effective_delta,
            "training_seconds": training_seconds,
            "trajectories": len(trajectories),
            "training_positions": td.positions_seen,
        }
    stable_comparison = _stable_checkpoint_comparison(label, parent, child)
    amplitude_surface = []
    if stable_comparison["move_flip_rate"] == 0.0:
        amplitude_surface = _amplitude_surface(label, parent, child)
    arena_started = time.perf_counter()
    arena = run_arena(
        compiled, native, parent, child,
        ArenaConfig(pairs=arena_pairs, nodes_per_move=300, max_depth=6,
                    tt_megabytes=8, opening_seed=480708,
                    opening_count=arena_pairs, min_plies=2, max_plies=6,
                    workers=min(4, arena_pairs)),
    ) if stable_comparison["move_flip_rate"] > 0.0 else None
    return {
        "label": label,
        "status": "EFFECTIVE_CHILD",
        "training_seconds": training_seconds,
        "arena_seconds": time.perf_counter() - arena_started if arena is not None else 0.0,
        "trajectories": len(trajectories),
        "training_positions": td.positions_seen,
        "td_mean_abs_error": td.mean_abs_td_error,
        "dynamic_weights_before": parent.dynamic_weights,
        "dynamic_weights_after": child.dynamic_weights,
        "dynamic_weight_delta": {
            name: child.dynamic_weights.get(name, 0.0) - parent.dynamic_weights.get(name, 0.0)
            for name in DYNAMIC_FEATURE_NAMES
        },
        "floating_checkpoint_delta": floating_delta,
        "native_bound_evaluator_delta": effective_delta,
        "stable_corpus_comparison": stable_comparison,
        "td_direction_amplitude_surface": amplitude_surface,
        "arena": {
            "pair_count": 0 if arena is None else arena.pair_count,
            "wins": 0 if arena is None else arena.game_wins,
            "draws": 0 if arena is None else arena.game_draws,
            "losses": 0 if arena is None else arena.game_losses,
            "mean_pair_score": None if arena is None else arena.mean_pair_score,
            "bootstrap_low": None if arena is None else arena.bootstrap_low,
            "bootstrap_high": None if arena is None else arena.bootstrap_high,
            "workers": min(4, arena_pairs),
        },
    }


def _generated_sanity() -> dict:
    """Exercise the same evaluator/search/TD path on generated semantic IR."""
    import sys
    sys.path.insert(0, str(ROOT / "tests"))
    from phase19c1_native_semantic_fixtures import semantic_corpus

    compiled = dict(semantic_corpus())["weird_0"]
    native = compile_native_semantic_rules(compiled)
    profile = build_ruleset_profile(compiled._legacy_compiled, EvaluationConfig())
    parent = LearnableMaterialCheckpoint.from_profile(
        compiled, profile, dynamic_weights=dict(WEIGHTS)
    )
    session = GameSession(compiled)
    result = SemanticSearchEngine(
        compiled, native, checkpoint=parent, tt_megabytes=0
    ).search(session, SearchLimits(max_depth=1, max_nodes=100, quiescence_max_depth=0))
    trajectories = collect_self_play(
        compiled, native, parent,
        SelfPlayConfig(games=1, nodes_per_move=20, max_depth=1, seed=480709,
                       epsilon=1.0, tt_megabytes=0, max_plies=2),
    )
    td = tdleaf_update(trajectories, parent, TDLeafConfig(alpha=0.01, lambd=0.7))
    return {
        "ruleset": "generated_semantic_weird_0",
        "fingerprint": compiled.ruleset_fingerprint,
        "native_executable": native.native_executable,
        "feature_names": list(DYNAMIC_FEATURE_NAMES),
        "search_action_present": result.action is not None,
        "search_dynamic_features": list(result.dynamic_features),
        "td_positions": td.positions_seen,
        "td_dynamic_weights": td.dynamic_weights,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--positions", type=int, default=16)
    parser.add_argument("--games", type=int, default=2)
    parser.add_argument("--arena-pairs", type=int, default=8)
    parser.add_argument("--sanity-only", action="store_true")
    parser.add_argument("--corrective-only", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    work_order = (
        "GENERICCHESS-F50-CORRECTIVE-EFFECTIVE-LEARNED-WEIGHT-RESOLUTION-AND-ARENA-RERUN"
        if args.corrective_only
        else "GENERICCHESS-F50-GENERIC-LEARNABLE-EVALUATOR-EXPANSION"
    )
    if args.sanity_only:
        result = {
            "work_order": work_order,
            "generated_sanity": _generated_sanity(),
        }
        (OUT / "f50_generated_sanity.json").write_text(
            json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, sort_keys=True))
        return
    started = time.perf_counter()
    result = {
        "work_order": work_order,
        "dynamic_feature_names": DYNAMIC_FEATURE_NAMES,
        "seeded_weights": WEIGHTS,
        "prescreen": [] if args.corrective_only else [
            _prescreen("A_CANONICAL_WESTERN_CHESS", args.positions),
            _prescreen("B_CANONICAL_STANDARD_SHOGI", args.positions),
        ],
        "learning_and_arena": [
            _learn_and_arena("A_CANONICAL_WESTERN_CHESS", args.games, args.arena_pairs),
            _learn_and_arena("B_CANONICAL_STANDARD_SHOGI", args.games, args.arena_pairs),
        ],
        "generated_sanity": _generated_sanity(),
        "wall_seconds": time.perf_counter() - started,
    }
    (OUT / "f50_results.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
