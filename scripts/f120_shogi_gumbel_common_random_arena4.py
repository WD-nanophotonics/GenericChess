"""F120 common-random-number null-gated Arena4 for the exact F118 child."""
from __future__ import annotations

import argparse
import json
import hashlib
import math
from pathlib import Path
import re
import subprocess
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
from generic_chess.learning.serialization import stable_sha256
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import public_action
from generic_chess.session.session import GameSession


FROZEN_CHECKPOINT_ID = "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
VALUE_COMPACT_MODEL_SHA = "b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6"
PARENT_POLICY_SHA = "2357472be320e9df909136a31a5223ec24e79f998467bb0ef3114b7e3433b955"
F118_CHILD_SHA = "45281f8ccccf557fdbe2edd74fc0822dedbff209c2178125dafab3c883aefdb3"
REGRESSION_SEED_BASE = 1200001
OPENING_SEED = 1200801
ARENA_SEARCH_SEED_BASE = 1200901


def _load(checkpoint_path: Path, parent_report: Path, child_path: Path):
    checkpoint_payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint = LearnableMaterialCheckpoint.from_dict(checkpoint_payload.get("checkpoint", checkpoint_payload))
    parent_payload = json.loads(parent_report.read_text(encoding="utf-8"))
    parent = SemanticPolicyV1.from_dict(parent_payload["rulesets"]["standard_shogi"]["policy_v1_artifact"])
    if checkpoint.checkpoint_id != FROZEN_CHECKPOINT_ID:
        raise RuntimeError("F120_FROZEN_CHECKPOINT_IDENTITY_MISMATCH")
    if stable_sha256(checkpoint.compact_nonlinear) != VALUE_COMPACT_MODEL_SHA:
        raise RuntimeError("F120_VALUE_COMPACT_MODEL_IDENTITY_MISMATCH")
    if parent.computed_model_sha256 != PARENT_POLICY_SHA:
        raise RuntimeError("F120_PARENT_POLICY_IDENTITY_MISMATCH")
    if not child_path.exists():
        raise RuntimeError("F120_F118_CHILD_ARTIFACT_UNAVAILABLE")
    child = SemanticPolicyV1.from_dict(json.loads(child_path.read_text(encoding="utf-8")))
    if child.computed_model_sha256 != F118_CHILD_SHA:
        raise RuntimeError("F120_F118_CHILD_IDENTITY_MISMATCH")
    return checkpoint, parent, child


def _context():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    return compiled, compile_native_semantic_rules(compiled)


def _ordered_legal(session):
    from generic_chess.core.actions import action_to_dict

    return sorted(session.legal_actions(), key=lambda action: json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":")))


def _regression(compiled, native_rules, checkpoint, parent):
    session = GameSession(compiled)
    rows = []
    for index in range(8):
        seed = REGRESSION_SEED_BASE + index
        first = SemanticGumbelMCTSV0(compiled, native_rules, checkpoint=checkpoint, policy=parent).search(session, search_seed=seed)
        second = SemanticGumbelMCTSV0(compiled, native_rules, checkpoint=checkpoint, policy=parent).search(session, search_seed=seed)
        signature = lambda result: (result.action, result.root_gumbels, result.root_visits, result.root_completed_q, result.improved_policy, result.root_rounds)
        if signature(first) != signature(second) or first.simulations != 64 or len(first.root_rounds[-1]["survivors"]) != 1 or first.action not in first.root_actions:
            raise RuntimeError("F120_SEARCH_REGRESSION_FAILED")
        rows.append({"index": index, "search_seed": seed, "position_identity": first.root_position_key, "action": first.action, "simulations": first.simulations, "expanded_nodes": first.expanded_nodes, "maximum_tree_depth": first.maximum_tree_depth})
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
    names = ("f62", "f75", "f77", "f78", "f79", "f80", "f81", "f107", "f108", "f112", "f113", "f114", "f115", "f116", "f117", "f118", "f119")
    found = set()
    for path in ROOT.rglob("*"):
        if not path.is_file() or not any(part.lower().startswith(name) for part in path.parts for name in names):
            continue
        try:
            found.update(pattern.findall(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError):
            pass
    return found


def _collect_corpus_keys(value, found):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"final_position_key", "position_identity"} and isinstance(item, str):
                found.add(item)
            _collect_corpus_keys(item, found)
    elif isinstance(value, list):
        for item in value:
            _collect_corpus_keys(item, found)


def _opening_corpus(compiled):
    excluded = _known_identities()
    for path in (ROOT / ".generic_chess_flow").glob("**/report.json"):
        if not any(token in path.as_posix().lower() for token in ("f115", "f116", "f117", "f118", "f119")):
            continue
        try:
            _collect_corpus_keys(json.loads(path.read_text(encoding="utf-8")), excluded)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass
    for offset in range(256):
        corpus = generate_arena_openings(compiled, count=4, seed=OPENING_SEED + offset, min_plies=2, max_plies=6)
        corpus.validate(compiled)
        keys = [opening.final_position_key for opening in corpus.openings]
        if len(set(keys)) == 4 and not any(key in excluded for key in keys):
            return corpus, offset
    raise RuntimeError("F120_OPENING_DISJOINTNESS_FAILED")


def _entropy(values):
    values = np.asarray(values, dtype=np.float64)
    return -float(np.sum(values * np.log(np.maximum(values, 1e-300))))


def _final_survivor_score(result):
    if not result.root_rounds:
        return None, None
    final = result.root_rounds[-1]
    survivors = list(final.get("survivors", ()))
    scores = list(final.get("improvement_scores_after", ()))
    if len(survivors) != 1:
        return (survivors[0] if survivors else None), None
    return survivors[0], (scores[0] if scores else None)


def _metric(result, ply, pair_index, game_index, arm, search_seed, started):
    final_survivor, final_score = _final_survivor_score(result)
    valid_search = (
        result.declaration_id is None
        and result.simulations == 64
        and bool(result.root_rounds)
        and len(result.root_rounds[-1]["survivors"]) == 1
        and result.action in result.root_actions
        and all(math.isfinite(value) for value in result.root_completed_q)
        and all(math.isfinite(value) and value > 0 for value in result.improved_policy)
    )
    selected_q = None
    if result.action in result.root_actions:
        selected_q = result.root_q_values[result.root_actions.index(result.action)]
    return {
        "pair_index": pair_index,
        "game_index": game_index,
        "ply": ply,
        "arm": arm,
        "search_seed": search_seed,
        "selected_action": result.action,
        "root_actions": list(result.root_actions),
        "root_logits": list(result.root_logits),
        "root_gumbels": list(result.root_gumbels),
        "root_visits": list(result.root_visits),
        "root_q_values": list(result.root_q_values),
        "root_completed_q": list(result.root_completed_q),
        "final_survivor": final_survivor,
        "final_survivor_improvement_score": final_score,
        "selected_empirical_q": selected_q,
        "simulations": result.simulations,
        "valid_search": valid_search,
        "expanded_nodes": result.expanded_nodes,
        "leaf_evaluations": result.leaf_evaluations,
        "maximum_tree_depth": result.maximum_tree_depth,
        "wall_seconds": time.perf_counter() - started,
        "improved_policy_entropy": _entropy(result.improved_policy),
        "declaration_encounters": result.declaration_encounters,
        "rounds": list(result.root_rounds),
    }


def _play(compiled, native_rules, checkpoint, parent, child, opening, pair_index, game_index, child_owner, strength):
    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    metrics = []
    error = None
    for ply in range(512):
        if session.result.status.value != "ongoing":
            break
        side = int(session.state.position.side_to_move)
        use_child = strength and side == child_owner
        policy = child if use_child else parent
        arm = "child" if use_child else "parent"
        search_seed = ARENA_SEARCH_SEED_BASE + 10000 * pair_index + ply
        started = time.perf_counter()
        try:
            result = SemanticGumbelMCTSV0(compiled, native_rules, checkpoint=checkpoint, policy=policy).search(session, search_seed=search_seed)
            metric = _metric(result, ply, pair_index, game_index, arm, search_seed, started)
            metrics.append(metric)
            if result.declaration_id is not None:
                raise RuntimeError("F120_UNSUPPORTED_NEUTRAL_DECLARATION")
            if not metric["valid_search"]:
                raise RuntimeError("F120_SEARCH_VALIDITY_FAILED")
            session.submit(public_action(native_rules, result.action))
        except Exception as exc:
            error = str(exc)
            break
    status = session.result.status.value
    valid = error is None and status != "ongoing" and bool(metrics) and all(metric["valid_search"] for metric in metrics)
    return {
        "pair_index": pair_index,
        "game_index": game_index,
        "opening_index": opening.index,
        "child_owner": child_owner,
        "valid": valid,
        "error": error,
        "status": status,
        "winner": session.result.winner,
        "plies": len(metrics),
        "declarations": sum(metric["declaration_encounters"] for metric in metrics),
        "metrics": metrics,
    }


def _validate_pair_seeds(games):
    for first, second in zip(games[::2], games[1::2]):
        pair_index = first["pair_index"]
        for ply, (left, right) in enumerate(zip(first["metrics"], second["metrics"])):
            expected = ARENA_SEARCH_SEED_BASE + 10000 * pair_index + ply
            if left["ply"] != ply or right["ply"] != ply or left["search_seed"] != expected or right["search_seed"] != expected or left["search_seed"] != right["search_seed"]:
                return False
    return all(metric["search_seed"] == ARENA_SEARCH_SEED_BASE + 10000 * game["pair_index"] + metric["ply"] for game in games for metric in game["metrics"])


def _null_signature(game):
    return {
        "actions": [metric["selected_action"] for metric in game["metrics"]],
        "status": game["status"],
        "winner": game["winner"],
        "plies": game["plies"],
        "search_seeds": [metric["search_seed"] for metric in game["metrics"]],
        "root_gumbels": [metric["root_gumbels"] for metric in game["metrics"]],
        "root_visits": [metric["root_visits"] for metric in game["metrics"]],
        "final_survivors": [metric["final_survivor"] for metric in game["metrics"]],
    }


def _null_pair(compiled, native_rules, checkpoint, parent, opening):
    games = [
        _play(compiled, native_rules, checkpoint, parent, parent, opening, 0, 0, 0, False),
        _play(compiled, native_rules, checkpoint, parent, parent, opening, 0, 1, 1, False),
    ]
    equal = _null_signature(games[0]) == _null_signature(games[1])
    seed_valid = _validate_pair_seeds(games)
    score = _pair_score(games[0], games[1])
    passed = all(game["valid"] for game in games) and equal and seed_valid and score == 0.5
    return {"passed": passed, "exact_equality": equal, "seed_contract_valid": seed_valid, "null_pair_score": score, "games": games}


def _logit_rows(metric):
    return [{"action": action, "logit": logit} for action, logit in zip(metric["root_actions"], metric["root_logits"])]


def _selected_q(metric):
    action = metric["selected_action"]
    try:
        return metric["root_q_values"][metric["root_actions"].index(action)]
    except (ValueError, IndexError):
        return None


def _pair_diagnostics(first, second):
    common = 0
    limit = min(len(first["metrics"]), len(second["metrics"]))
    while common < limit and first["metrics"][common]["selected_action"] == second["metrics"][common]["selected_action"]:
        common += 1
    divergence = common if common < limit else None
    diagnostic = {
        "pair_index": first["pair_index"],
        "common_prefix_length": common,
        "first_divergence_ply": divergence,
        "same_action_at_last_common_state": True if common else None,
    }
    if divergence is None:
        diagnostic["first_divergence"] = None
        return diagnostic
    left = first["metrics"][divergence]
    right = second["metrics"][divergence]
    parent_metric = left if left["arm"] == "parent" else right
    child_metric = left if left["arm"] == "child" else right
    diagnostics = []
    parent_logits = {row["action"]: row["logit"] for row in _logit_rows(parent_metric)}
    child_logits = {row["action"]: row["logit"] for row in _logit_rows(child_metric)}
    for action in sorted(set(parent_logits) | set(child_logits)):
        diagnostics.append({"action": action, "parent_logit": parent_logits.get(action), "child_logit": child_logits.get(action)})
    diagnostic["first_divergence"] = {
        "parent_arm": parent_metric["arm"],
        "child_arm": child_metric["arm"],
        "parent_gumbels": parent_metric["root_gumbels"],
        "child_gumbels": child_metric["root_gumbels"],
        "parent_selected_action": parent_metric["selected_action"],
        "child_selected_action": child_metric["selected_action"],
        "parent_selected_empirical_q": _selected_q(parent_metric),
        "child_selected_empirical_q": _selected_q(child_metric),
        "parent_final_survivor": parent_metric["final_survivor"],
        "child_final_survivor": child_metric["final_survivor"],
        "parent_final_survivor_improvement_score": parent_metric["final_survivor_improvement_score"],
        "child_final_survivor_improvement_score": child_metric["final_survivor_improvement_score"],
        "legal_action_logits": diagnostics,
    }
    return diagnostic


def _pair_score(first, second):
    points = [0.5 if game["winner"] is None else float(game["winner"] == game["child_owner"]) for game in (first, second)]
    return float(np.mean(points))


def _summary_stats(metrics, key):
    values = [float(metric[key]) for metric in metrics]
    return {"count": len(values), "min": min(values), "median": float(np.median(values)), "max": max(values), "sum": float(np.sum(values))} if values else {"count": 0}


def _strength_arena(compiled, native_rules, checkpoint, parent, child, corpus):
    games = []
    for game_index in range(8):
        games.append(_play(compiled, native_rules, checkpoint, parent, child, corpus.openings[game_index // 2], game_index // 2, game_index, game_index % 2, True))
    seed_valid = _validate_pair_seeds(games)
    valid_games = [game for game in games if game["valid"]]
    pair_scores = [_pair_score(games[2 * pair], games[2 * pair + 1]) for pair in range(4)]
    diagnostics = [_pair_diagnostics(games[2 * pair], games[2 * pair + 1]) for pair in range(4)]
    metrics = [metric for game in games for metric in game["metrics"]]
    wdl = {"wins": 0, "draws": 0, "losses": 0}
    for game in games:
        if game["winner"] is None:
            wdl["draws"] += 1
        elif game["winner"] == game["child_owner"]:
            wdl["wins"] += 1
        else:
            wdl["losses"] += 1
    mean = float(np.mean(pair_scores))
    better = sum(score > 0.5 for score in pair_scores)
    worse = sum(score < 0.5 for score in pair_scores)
    valid = len(valid_games) == 8 and seed_valid
    classification = "SHOGI_GUMBEL_COMPLETED_Q_CRN_ARENA4_INVALID" if not valid else ("SHOGI_GUMBEL_COMPLETED_Q_CRN_ARENA4_CONFIRMED" if mean > 0.5 and better > worse else "SHOGI_GUMBEL_COMPLETED_Q_CRN_ARENA4_REJECTED")
    return {
        "games": games,
        "valid_game_count": len(valid_games),
        "pair_scores": pair_scores,
        "mean_pair_score": mean,
        "child_better_pairs": better,
        "child_tied_pairs": sum(score == 0.5 for score in pair_scores),
        "child_worse_pairs": worse,
        "wdl": wdl,
        "crn_seed_contract_valid": seed_valid,
        "pair_diagnostics": diagnostics,
        "wall_seconds_by_arm": {"parent": _summary_stats([m for m in metrics if m["arm"] == "parent"], "wall_seconds"), "child": _summary_stats([m for m in metrics if m["arm"] == "child"], "wall_seconds")},
        "expanded_nodes": _summary_stats(metrics, "expanded_nodes"),
        "leaf_evaluations": _summary_stats(metrics, "leaf_evaluations"),
        "maximum_tree_depth": _summary_stats(metrics, "maximum_tree_depth"),
        "improved_policy_entropy": _summary_stats(metrics, "improved_policy_entropy"),
        "declaration_count": sum(game["declarations"] for game in games),
        "no_contest_count": sum(game["winner"] is None for game in games),
        "classification": classification,
    }


def _implementation_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNAVAILABLE"


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
    corpus, offset = _opening_corpus(compiled)
    null_pair = _null_pair(compiled, native_rules, checkpoint, parent, corpus.openings[0])
    report = {
        "work_order_id": "GENERICCHESS_F120_SHOGI_GUMBEL_COMMON_RANDOM_ARENA4",
        "implementation_sha": _implementation_sha(),
        "frozen_checkpoint_id": checkpoint.checkpoint_id,
        "value_compact_model_sha256": VALUE_COMPACT_MODEL_SHA,
        "parent_policy_sha256": parent.computed_model_sha256,
        "child_policy_sha256": child.computed_model_sha256,
        "requested_opening_seed": OPENING_SEED,
        "opening_selection_offset": offset,
        "opening_corpus": corpus.to_dict(),
        "regression": regression,
        "null_pair": null_pair,
    }
    if not null_pair["passed"]:
        report["classification"] = "F120_COMMON_RANDOM_NULL_PAIR_FAILED"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"classification": report["classification"], "null_pair_score": null_pair["null_pair_score"]}, sort_keys=True))
        return 2
    arena = _strength_arena(compiled, native_rules, checkpoint, parent, child, corpus)
    report["arena"] = arena
    report["classification"] = arena["classification"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"classification": report["classification"], "mean_pair_score": arena["mean_pair_score"], "valid_game_count": arena["valid_game_count"], "null_pair_passed": null_pair["passed"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
