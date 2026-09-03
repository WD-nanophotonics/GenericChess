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
    arena_started = time.perf_counter()
    arena = run_arena(
        compiled, native, parent, child,
        ArenaConfig(pairs=arena_pairs, nodes_per_move=300, max_depth=6,
                    tt_megabytes=8, opening_seed=480708,
                    opening_count=arena_pairs, min_plies=2, max_plies=6,
                    workers=min(4, arena_pairs)),
    )
    return {
        "label": label,
        "training_seconds": training_seconds,
        "arena_seconds": time.perf_counter() - arena_started,
        "trajectories": len(trajectories),
        "training_positions": td.positions_seen,
        "td_mean_abs_error": td.mean_abs_td_error,
        "dynamic_weights_before": parent.dynamic_weights,
        "dynamic_weights_after": child.dynamic_weights,
        "dynamic_weight_delta": {
            name: child.dynamic_weights.get(name, 0.0) - parent.dynamic_weights.get(name, 0.0)
            for name in DYNAMIC_FEATURE_NAMES
        },
        "arena": {
            "pair_count": arena.pair_count,
            "wins": arena.game_wins,
            "draws": arena.game_draws,
            "losses": arena.game_losses,
            "mean_pair_score": arena.mean_pair_score,
            "bootstrap_low": arena.bootstrap_low,
            "bootstrap_high": arena.bootstrap_high,
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
    parser.add_argument("--arena-pairs", type=int, default=2)
    parser.add_argument("--sanity-only", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.sanity_only:
        result = {
            "work_order": "GENERICCHESS-F50-GENERIC-LEARNABLE-EVALUATOR-EXPANSION",
            "generated_sanity": _generated_sanity(),
        }
        (OUT / "f50_generated_sanity.json").write_text(
            json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, sort_keys=True))
        return
    started = time.perf_counter()
    result = {
        "work_order": "GENERICCHESS-F50-GENERIC-LEARNABLE-EVALUATOR-EXPANSION",
        "dynamic_feature_names": DYNAMIC_FEATURE_NAMES,
        "seeded_weights": WEIGHTS,
        "prescreen": [
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
