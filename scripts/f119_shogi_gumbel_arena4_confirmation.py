"""F119 Arena4 confirmation for the exact F118 completed-Q child."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import statistics
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.learning.gumbel_mcts import SemanticGumbelMCTSV0
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.policy_v1 import SemanticPolicyV1
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import public_action
from generic_chess.session.session import GameSession


FROZEN_CHECKPOINT_ID = "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
PARENT_POLICY_SHA = "2357472be320e9df909136a31a5223ec24e79f998467bb0ef3114b7e3433b955"
F118_CHILD_SHA = "45281f8ccccf557fdbe2edd74fc0822dedbff209c2178125dafab3c883aefdb3"
REGRESSION_SEED_BASE = 1190001
OPENING_SEED = 1190801
ARENA_SEARCH_SEED_BASE = 1190901


def _load(checkpoint_path: Path, parent_report: Path, child_path: Path):
    checkpoint_payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint = LearnableMaterialCheckpoint.from_dict(checkpoint_payload.get("checkpoint", checkpoint_payload))
    report = json.loads(parent_report.read_text(encoding="utf-8"))
    parent = SemanticPolicyV1.from_dict(report["rulesets"]["standard_shogi"]["policy_v1_artifact"])
    if checkpoint.checkpoint_id != FROZEN_CHECKPOINT_ID:
        raise RuntimeError("F119_FROZEN_CHECKPOINT_IDENTITY_MISMATCH")
    if parent.computed_model_sha256 != PARENT_POLICY_SHA:
        raise RuntimeError("F119_PARENT_POLICY_IDENTITY_MISMATCH")
    if not child_path.exists():
        raise RuntimeError("F119_F118_CHILD_ARTIFACT_UNAVAILABLE")
    child = SemanticPolicyV1.from_dict(json.loads(child_path.read_text(encoding="utf-8")))
    if child.computed_model_sha256 != F118_CHILD_SHA:
        raise RuntimeError("F119_F118_CHILD_IDENTITY_MISMATCH")
    return checkpoint, parent, child


def _context():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    return compiled, compile_native_semantic_rules(compiled)


def _ordered_legal(session):
    import json as _json
    from generic_chess.core.actions import action_to_dict
    return sorted(session.legal_actions(), key=lambda action: _json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":")))


def _regression(compiled, native_rules, checkpoint, parent):
    session = GameSession(compiled)
    rows = []
    for index in range(8):
        first = SemanticGumbelMCTSV0(compiled, native_rules, checkpoint=checkpoint, policy=parent).search(session, search_seed=REGRESSION_SEED_BASE + index)
        second = SemanticGumbelMCTSV0(compiled, native_rules, checkpoint=checkpoint, policy=parent).search(session, search_seed=REGRESSION_SEED_BASE + index)
        equal = (first.action, first.root_visits, first.root_q_values, first.root_completed_q, first.improved_policy, first.root_rounds) == (second.action, second.root_visits, second.root_q_values, second.root_completed_q, second.improved_policy, second.root_rounds)
        if not equal or first.simulations != 64 or len(first.root_rounds[-1]["survivors"]) != 1 or first.action not in first.root_actions:
            raise RuntimeError("F119_SEARCH_REGRESSION_FAILED")
        rows.append({"index": index, "search_seed": REGRESSION_SEED_BASE + index, "position_identity": first.root_position_key, "action": first.action, "simulations": first.simulations, "expanded_nodes": first.expanded_nodes, "maximum_tree_depth": first.maximum_tree_depth})
        legal = _ordered_legal(session)
        if not legal:
            session = GameSession(compiled)
        else:
            session.submit(legal[0])
            if session.result.status.value != "ongoing":
                session = GameSession(compiled)
    return {"count": len(rows), "rows": rows}


def _known_identities():
    pattern = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
    names = ("f62", "f75", "f77", "f78", "f79", "f80", "f81", "f107", "f108", "f112", "f113", "f114", "f115", "f116", "f117", "f118")
    found = set()
    for path in ROOT.rglob("*"):
        if not path.is_file() or not any(part.lower().startswith(name) for part in path.parts for name in names):
            continue
        try:
            found.update(pattern.findall(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError):
            pass
    return found


def _opening_corpus(compiled):
    excluded = _known_identities()
    f118_report = ROOT / ".generic_chess_flow" / "f118-shogi-gumbel-clean-replication-arena2" / "report.json"
    if f118_report.exists():
        payload = json.loads(f118_report.read_text(encoding="utf-8"))
        excluded.update(row["position_identity"] for row in payload.get("selfplay_roots", ()))
        excluded.update(item["final_position_key"] for item in payload.get("arena", {}).get("corpus", {}).get("openings", ()))
    for offset in range(256):
        corpus = generate_arena_openings(compiled, count=4, seed=OPENING_SEED + offset, min_plies=2, max_plies=6)
        corpus.validate(compiled)
        keys = [opening.final_position_key for opening in corpus.openings]
        if len(set(keys)) == 4 and not any(key in excluded for key in keys):
            return corpus, offset
    raise RuntimeError("F119_OPENING_DISJOINTNESS_FAILED")


def _entropy(values):
    values = np.asarray(values, dtype=np.float64)
    return -float(np.sum(values * np.log(np.maximum(values, 1e-300))))


def _arena(compiled, native_rules, checkpoint, parent, child):
    corpus, offset = _opening_corpus(compiled)
    games = []
    for game in range(8):
        opening = corpus.openings[game // 2]
        child_owner = game % 2
        session = GameSession(compiled)
        for action in opening.actions:
            session.submit(action)
        metrics = []
        error = None
        for ply in range(512):
            if session.result.status.value != "ongoing":
                break
            side = int(session.state.position.side_to_move)
            policy = child if side == child_owner else parent
            search_seed = ARENA_SEARCH_SEED_BASE + 10000 * game + ply
            started = time.perf_counter()
            try:
                result = SemanticGumbelMCTSV0(compiled, native_rules, checkpoint=checkpoint, policy=policy).search(session, search_seed=search_seed)
                valid_search = result.simulations == 64 and len(result.root_rounds[-1]["survivors"]) == 1 and result.action in result.root_actions and all(math.isfinite(value) for value in result.root_completed_q) and all(value > 0 for value in result.improved_policy)
                if result.declaration_id is not None:
                    session.declare(result.declaration_id)
                    metrics.append({"ply": ply, "search_seed": search_seed, "arm": "child" if side == child_owner else "parent", "simulations": result.simulations, "valid_search": valid_search, "expanded_nodes": result.expanded_nodes, "leaf_evaluations": result.leaf_evaluations, "maximum_tree_depth": result.maximum_tree_depth, "wall_seconds": time.perf_counter() - started, "improved_policy_entropy": _entropy(result.improved_policy), "declaration_encounters": result.declaration_encounters, "rounds": list(result.root_rounds)})
                    break
                if not valid_search:
                    raise RuntimeError("F119_SEARCH_VALIDITY_FAILED")
                session.submit(public_action(native_rules, result.action))
                metrics.append({"ply": ply, "search_seed": search_seed, "arm": "child" if side == child_owner else "parent", "simulations": result.simulations, "valid_search": True, "expanded_nodes": result.expanded_nodes, "leaf_evaluations": result.leaf_evaluations, "maximum_tree_depth": result.maximum_tree_depth, "wall_seconds": time.perf_counter() - started, "improved_policy_entropy": _entropy(result.improved_policy), "declaration_encounters": result.declaration_encounters, "rounds": list(result.root_rounds)})
            except Exception as exc:
                error = str(exc)
                break
        valid = error is None and session.result.status.value != "ongoing" and all(metric["valid_search"] for metric in metrics)
        games.append({"game": game, "opening": opening.index, "child_owner": child_owner, "valid": valid, "error": error, "status": session.result.status.value, "winner": session.result.winner, "plies": len(metrics), "declarations": sum(metric["declaration_encounters"] for metric in metrics), "metrics": metrics})
    valid_games = [game for game in games if game["valid"]]
    if len(valid_games) != 8:
        return {"requested_opening_seed": OPENING_SEED, "selection_offset": offset, "corpus": corpus.to_dict(), "games": games, "valid_game_count": len(valid_games), "classification": "F119_GUMBEL_ARENA4_INVALID"}
    pair_scores = []
    for pair in range(4):
        pair_games = games[2 * pair:2 * pair + 2]
        points = [0.5 if game["winner"] is None else float(game["winner"] == game["child_owner"]) for game in pair_games]
        pair_scores.append(float(np.mean(points)))
    mean = float(np.mean(pair_scores))
    better = sum(score > 0.5 for score in pair_scores)
    worse = sum(score < 0.5 for score in pair_scores)
    return {"requested_opening_seed": OPENING_SEED, "selection_offset": offset, "corpus": corpus.to_dict(), "games": games, "valid_game_count": 8, "pair_scores": pair_scores, "mean_pair_score": mean, "child_better_pairs": better, "child_worse_pairs": worse, "classification": "SHOGI_GUMBEL_COMPLETED_Q_ARENA4_CONFIRMED" if mean > 0.5 and better > worse else "SHOGI_GUMBEL_COMPLETED_Q_ARENA4_REJECTED"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--parent-report", type=Path, required=True)
    parser.add_argument("--child-policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    checkpoint, parent, child = _load(args.checkpoint, args.parent_report, args.child_policy)
    compiled, native_rules = _context()
    regression = _regression(compiled, native_rules, checkpoint, parent)
    arena = _arena(compiled, native_rules, checkpoint, parent, child)
    seed_valid = all(metric["search_seed"] == ARENA_SEARCH_SEED_BASE + 10000 * game["game"] + metric["ply"] for game in arena["games"] for metric in game["metrics"])
    if not seed_valid:
        raise RuntimeError("F119_ARENA_SEED_CONTRACT_VIOLATION")
    report = {"work_order_id": "GENERICCHESS_F119_SHOGI_GUMBEL_COMPLETED_Q_ARENA4_CONFIRMATION", "classification": arena["classification"], "frozen_checkpoint_id": checkpoint.checkpoint_id, "parent_policy_sha256": parent.computed_model_sha256, "child_policy_sha256": child.computed_model_sha256, "regression": regression, "arena_seed_contract": {"base": ARENA_SEARCH_SEED_BASE, "valid": seed_valid}, "arena": arena}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"classification": report["classification"], "mean_pair_score": arena.get("mean_pair_score"), "valid_game_count": arena["valid_game_count"]}, sort_keys=True))


if __name__ == "__main__":
    main()
