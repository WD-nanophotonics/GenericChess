"""F113 Shogi Policy-v1 deferred-legality parity, cost, and Arena2 gate."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import re
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.core.identity import position_identity_key
from generic_chess.learning.arena import ArenaConfig, run_arena
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.policy import semantic_state_feature_vector
from generic_chess.learning.policy_v1 import SemanticPolicyV1, action_v1_components
from generic_chess.native import _module
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.mirror import pack_semantic_action
from generic_chess.native.semantic import public_action
from generic_chess.native.semantic import dynamic_features
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.session.session import GameSession


CHECKPOINT_ID = "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
POLICY_SHA = "2357472be320e9df909136a31a5223ec24e79f998467bb0ef3114b7e3433b955"
ROOT_COUNT = 24
FIXED_NODES = 2_000


def _load_inputs(args):
    report = json.loads(args.policy_report.read_text(encoding="utf-8"))
    policy = SemanticPolicyV1.from_dict(
        report["rulesets"]["standard_shogi"]["policy_v1_artifact"]
    )
    if policy.computed_model_sha256 != POLICY_SHA:
        raise RuntimeError("POLICY_V1_IDENTITY_MISMATCH")
    payload = json.loads(args.checkpoint.read_text(encoding="utf-8"))
    checkpoint = LearnableMaterialCheckpoint.from_dict(
        payload.get("checkpoint", payload)
    )
    if checkpoint.checkpoint_id != CHECKPOINT_ID:
        raise RuntimeError("FROZEN_CHECKPOINT_IDENTITY_MISMATCH")
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    native_rules = compile_native_semantic_rules(compiled)
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    return compiled, native_rules, checkpoint, policy, bundle["rows"][:ROOT_COUNT]


def _session_for(compiled, row):
    session = GameSession(compiled)
    for item in row["history"]:
        session.submit(action_from_dict(item))
    return session


def _fixed_search(compiled, native_rules, checkpoint, policy, row, deferred):
    session = _session_for(compiled, row)
    engine = SemanticSearchEngine(
        compiled,
        native_rules,
        checkpoint=checkpoint,
        policy=policy,
        policy_deferred_legality=deferred,
        tt_megabytes=8,
    )
    started = time.perf_counter()
    result = engine.search(
        session,
        SearchLimits(max_depth=12, max_nodes=FIXED_NODES, quiescence_max_depth=0),
    )
    wall = time.perf_counter() - started
    return {
        "root_identity": row["root_identity"],
        "score": int(result.score),
        "best_action": None if result.action is None else action_to_dict(result.action),
        "principal_variation": [action_to_dict(action) for action in result.principal_variation],
        "nodes": int(result.nodes),
        "completed_depth": int(result.completed_depth),
        "wall_seconds": wall,
        "policy_nodes": int(result.policy_nodes),
        "policy_state_inferences": int(result.policy_state_inferences),
        "policy_action_embeddings": int(result.policy_action_embeddings),
        "policy_actions_scored": int(result.policy_actions_scored),
        "policy_elapsed_seconds": float(result.policy_elapsed_seconds),
        "policy_deferred_legality": bool(result.policy_deferred_legality),
        "policy_preorder_checked_transitions": int(result.policy_preorder_checked_transitions),
        "policy_traversal_checked_attempts": int(result.policy_traversal_checked_attempts),
        "policy_traversal_illegal_skips": int(result.policy_traversal_illegal_skips),
        "legal_action": result.action is not None,
    }


def _parity_rows(eager, deferred):
    rows = []
    for before, after in zip(eager, deferred):
        equal = all(before[key] == after[key] for key in (
            "score", "best_action", "principal_variation", "nodes", "completed_depth"
        ))
        rows.append({
            "root_identity": before["root_identity"],
            "equal": equal,
            "eager": before,
            "deferred": after,
        })
    return rows


def _invariant_positions(compiled, rows, count=100):
    sessions = []
    seen = set()
    for row in rows:
        session = _session_for(compiled, row)
        while session.result.status.value == "ongoing" and len(sessions) < count:
            identity = position_identity_key(session.state.position, compiled)
            if identity not in seen:
                sessions.append(session)
                seen.add(identity)
            legal = sorted(session.legal_actions(), key=lambda action: json.dumps(
                action_to_dict(action), sort_keys=True, separators=(",", ":")
            ))
            if not legal:
                break
            session = _copy_session(compiled, session, legal[0])
        if len(sessions) >= count:
            break
    return sessions[:count]


def _copy_session(compiled, session, action):
    clone = GameSession(compiled)
    for record in session.history:
        clone.submit(record.action)
    clone.submit(action)
    return clone


def _ordered_subset_invariant(compiled, native_rules, policy, sessions):
    rows = []
    for session in sessions:
        position_capsule = pack_semantic_search_position(compiled, native_rules, session)
        candidates = tuple(int(raw) for raw in _module().semantic_candidate_actions(
            native_rules.capsule, position_capsule
        ))
        position = session.state.position
        state = semantic_state_feature_vector(
            position, compiled, dynamic_features(native_rules, position_capsule)
        )
        actions = [public_action(native_rules, raw) for raw in candidates]
        bases = []
        categories = []
        for action in actions:
            base, category = action_v1_components(compiled, position, action)
            bases.append(base)
            categories.append(category)
        category_arrays = tuple(
            np.asarray([category[index] for category in categories], dtype=np.int64)
            for index in range(4)
        )
        order = policy.ordered_actions(
            state, np.asarray(bases), category_arrays, native_identities=candidates
        )
        scores = policy.logits(state, np.asarray(bases), category_arrays)
        legal = []
        for index, raw in enumerate(candidates):
            try:
                _module().semantic_make_checked(native_rules.capsule, position_capsule, raw)
            except Exception:
                continue
            legal.append(index)
        eager = tuple(candidates[index] for index in order if index in set(legal))
        deferred = tuple(candidates[index] for index in order if index in set(legal))
        rows.append({
            "position_identity": position_identity_key(position, compiled),
            "candidate_count": len(candidates),
            "legal_count": len(legal),
            "eager_order": list(eager),
            "deferred_projected_order": list(deferred),
            "equal": eager == deferred,
            "score_min": float(np.min(scores)) if len(scores) else None,
            "score_max": float(np.max(scores)) if len(scores) else None,
        })
    return rows


def _known_strength_identities():
    names = ("f75", "f77", "f78", "f79", "f80", "f81", "f107", "f108", "f109", "f112")
    pattern = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
    identities = set()
    for path in ROOT.joinpath(".generic_chess_flow").rglob("*"):
        if not path.is_file() or not any(path.name.lower().startswith(name) or any(
            part.lower().startswith(name) for part in path.parts
        ) for name in names):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        identities.update(pattern.findall(text))
    return identities


def _arena_payload(arena):
    games = []
    metrics = []
    for pair in arena.pairs:
        for game in (pair.game_child_owner0, pair.game_child_owner1):
            games.append({
                "pair": game.pair,
                "opening_id": game.opening_id,
                "child_owner": game.child_owner,
                "result": game.result,
                "winner": game.winner,
                "plies": game.plies,
            })
            metrics.extend(game.search_metrics)
    search_wall = [float(row["search_wall_seconds"]) for row in metrics]
    policy_time = [float(row.get("policy_elapsed_seconds", 0.0)) for row in metrics]
    return {
        "pair_scores": list(arena.pair_scores),
        "mean_pair_score": arena.mean_pair_score,
        "child_better_pairs": arena.child_better_pairs,
        "tied_pairs": arena.tied_pairs,
        "child_worse_pairs": arena.child_worse_pairs,
        "game_wins": arena.game_wins,
        "game_draws": arena.game_draws,
        "game_losses": arena.game_losses,
        "valid": arena.pair_count == 2 and len(games) == 4 and all(
            game["result"] != "no_contest" for game in games
        ),
        "games": games,
        "search_wall_seconds": {
            "mean": float(np.mean(search_wall)) if search_wall else 0.0,
            "median": float(np.median(search_wall)) if search_wall else 0.0,
            "p95": float(np.percentile(search_wall, 95)) if search_wall else 0.0,
            "max": max(search_wall, default=0.0),
        },
        "policy_elapsed_seconds": sum(policy_time),
        "telemetry": {
            key: sum(int(row.get(key, 0)) for row in metrics)
            for key in (
                "nodes", "completed_depth", "policy_nodes", "policy_state_inferences",
                "policy_actions_scored", "policy_action_embeddings",
                "policy_preorder_checked_transitions",
                "policy_traversal_checked_attempts", "policy_traversal_illegal_skips",
            )
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--policy-report", type=Path, required=True)
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    compiled, native_rules, checkpoint, policy, rows = _load_inputs(args)

    sessions = _invariant_positions(compiled, rows)
    invariant = _ordered_subset_invariant(compiled, native_rules, policy, sessions)
    if len(invariant) < 100 or not all(row["equal"] for row in invariant):
        raise RuntimeError("POLICY_V1_DEFERRED_LEGALITY_ORDER_PARITY_FAILED")

    eager = [_fixed_search(compiled, native_rules, checkpoint, policy, row, False) for row in rows]
    deferred = [_fixed_search(compiled, native_rules, checkpoint, policy, row, True) for row in rows]
    parity = _parity_rows(eager, deferred)
    if not all(row["equal"] for row in parity):
        classification = "POLICY_V1_DEFERRED_LEGALITY_SEMANTIC_PARITY_FAILED"
        output = {
            "work_order_id": "GENERICCHESS_F113_SHOGI_POLICY_V1_DEFERRED_LEGALITY_ARENA2",
            "frozen_checkpoint_id": checkpoint.checkpoint_id,
            "policy_model_sha256": policy.model_sha256,
            "legal_subset_order_parity": {"positions": len(invariant), "mismatches": 0},
            "fixed_node_parity": {"passed": False, "rows": parity},
            "classification": classification,
        }
        args.output.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"classification": classification}, sort_keys=True))
        return

    eager_wall = sum(row["wall_seconds"] for row in eager)
    deferred_wall = sum(row["wall_seconds"] for row in deferred)
    eager_policy = sum(row["policy_elapsed_seconds"] for row in eager)
    deferred_policy = sum(row["policy_elapsed_seconds"] for row in deferred)
    performance = {
        "eager": {"total_wall_seconds": eager_wall, "policy_elapsed_seconds": eager_policy, "rows": eager},
        "deferred": {"total_wall_seconds": deferred_wall, "policy_elapsed_seconds": deferred_policy, "rows": deferred},
        "policy_time_ratio": deferred_policy / eager_policy if eager_policy else None,
        "total_wall_ratio": deferred_wall / eager_wall if eager_wall else None,
        "eager_policy_microseconds_per_node": 1e6 * eager_policy / sum(row["policy_nodes"] for row in eager),
        "deferred_policy_microseconds_per_node": 1e6 * deferred_policy / sum(row["policy_nodes"] for row in deferred),
    }
    if not (deferred_policy < eager_policy and deferred_wall < eager_wall):
        classification = "POLICY_V1_DEFERRED_LEGALITY_COST_REDUCTION_NOT_ESTABLISHED"
        output = {
            "work_order_id": "GENERICCHESS_F113_SHOGI_POLICY_V1_DEFERRED_LEGALITY_ARENA2",
            "frozen_checkpoint_id": checkpoint.checkpoint_id,
            "policy_model_sha256": policy.model_sha256,
            "legal_subset_order_parity": {"positions": len(invariant), "mismatches": 0, "rows": invariant},
            "fixed_node_parity": {"passed": True, "rows": parity},
            "performance": performance,
            "classification": classification,
        }
        args.output.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"classification": classification}, sort_keys=True))
        return

    openings = generate_arena_openings(compiled, count=2, seed=1130801, min_plies=2, max_plies=6)
    known = _known_strength_identities()
    opening_ids = [opening.final_position_key for opening in openings.openings]
    if len(set(opening_ids)) != 2 or set(opening_ids) & known:
        raise RuntimeError("F113_OPENING_DISJOINTNESS_FAILED")
    opening_artifact = args.output.with_name(args.output.stem + "-openings.json")
    opening_artifact.write_text(json.dumps(openings.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    arena_config = ArenaConfig(
        pairs=2, nodes_per_move=1_000_000, max_depth=12, tt_megabytes=8,
        opening_seed=1130801, opening_count=2, min_plies=2, max_plies=6,
        workers=1, move_time_seconds=1.0, root_window_pruning=True,
    )
    arena = run_arena(
        compiled, native_rules, checkpoint, checkpoint, arena_config,
        openings=openings, capture_search_metrics=True, policy=policy,
        policy_deferred_legality=True,
    )
    arena_payload = _arena_payload(arena)
    classification = (
        "SHOGI_POLICY_V1_DEFERRED_LEGALITY_ARENA2_SURVIVES"
        if arena_payload["valid"] and arena.mean_pair_score > 0.5
        and arena.child_better_pairs > arena.child_worse_pairs
        else "SHOGI_POLICY_V1_DEFERRED_LEGALITY_ARENA2_REJECTED"
    )
    output = {
        "work_order_id": "GENERICCHESS_F113_SHOGI_POLICY_V1_DEFERRED_LEGALITY_ARENA2",
        "frozen_checkpoint_id": checkpoint.checkpoint_id,
        "policy_model_sha256": policy.model_sha256,
        "legal_subset_order_parity": {"positions": len(invariant), "mismatches": 0, "rows": invariant},
        "fixed_node_parity": {"passed": True, "rows": parity},
        "performance": performance,
        "arena_config": asdict(arena_config),
        "fresh_openings": openings.to_dict(),
        "arena": arena_payload,
        "classification": classification,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"classification": classification, "mean_pair_score": arena.mean_pair_score}, sort_keys=True))


if __name__ == "__main__":
    main()
