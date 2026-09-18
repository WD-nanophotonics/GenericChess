"""F121 neutral-declaration-corrected common-random-number Arena4."""
from __future__ import annotations

import argparse
import json
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
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import available_declarations, public_action
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.session.session import GameSession


FROZEN_CHECKPOINT_ID = "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
VALUE_COMPACT_MODEL_SHA = "b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6"
PARENT_POLICY_SHA = "2357472be320e9df909136a31a5223ec24e79f998467bb0ef3114b7e3433b955"
F118_CHILD_SHA = "45281f8ccccf557fdbe2edd74fc0822dedbff209c2178125dafab3c883aefdb3"
REGRESSION_SEED_BASE = 1210001
OPENING_SEED = 1210801
ARENA_SEARCH_SEED_BASE = 1210901


def _load(checkpoint_path: Path, parent_report: Path, child_path: Path):
    raw = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint = LearnableMaterialCheckpoint.from_dict(raw.get("checkpoint", raw))
    report = json.loads(parent_report.read_text(encoding="utf-8"))
    parent = SemanticPolicyV1.from_dict(report["rulesets"]["standard_shogi"]["policy_v1_artifact"])
    if checkpoint.checkpoint_id != FROZEN_CHECKPOINT_ID:
        raise RuntimeError("F121_FROZEN_CHECKPOINT_IDENTITY_MISMATCH")
    if stable_sha256(checkpoint.compact_nonlinear) != VALUE_COMPACT_MODEL_SHA:
        raise RuntimeError("F121_VALUE_COMPACT_MODEL_IDENTITY_MISMATCH")
    if parent.computed_model_sha256 != PARENT_POLICY_SHA:
        raise RuntimeError("F121_PARENT_POLICY_IDENTITY_MISMATCH")
    child = SemanticPolicyV1.from_dict(json.loads(child_path.read_text(encoding="utf-8")))
    if child.computed_model_sha256 != F118_CHILD_SHA:
        raise RuntimeError("F121_F118_CHILD_IDENTITY_MISMATCH")
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
        signature = lambda result: (result.action, result.declaration_id, result.root_gumbels, result.root_visits, result.root_completed_q, result.neutral_declaration_available, result.neutral_declaration_selected, result.root_rounds)
        if signature(first) != signature(second) or (first.declaration_id is None and first.simulations != 64):
            raise RuntimeError("F121_SEARCH_REGRESSION_FAILED")
        rows.append({"index": index, "search_seed": seed, "position_identity": first.root_position_key, "action": first.action, "declaration_id": first.declaration_id, "simulations": first.simulations, "expanded_nodes": first.expanded_nodes, "maximum_tree_depth": first.maximum_tree_depth})
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
    names = ("f62", "f75", "f77", "f78", "f79", "f80", "f81", "f107", "f108", "f112", "f113", "f114", "f115", "f116", "f117", "f118", "f119", "f120", "f121")
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
        if not any(token in path.as_posix().lower() for token in ("f115", "f116", "f117", "f118", "f119", "f120")):
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
    raise RuntimeError("F121_OPENING_DISJOINTNESS_FAILED")


def _entropy(values):
    values = np.asarray(values, dtype=np.float64)
    return -float(np.sum(values * np.log(np.maximum(values, 1e-300))))


def _authoritative_declaration(native_rules, session, declaration_id):
    position = pack_semantic_search_position(session.compiled, native_rules, session)
    matches = [item for item in available_declarations(native_rules, position) if item.declaration_id == declaration_id]
    return matches[0] if matches else None


def _metric(result, ply, pair_index, game_index, arm, search_seed, started, declaration):
    survivor = None
    survivor_score = None
    if result.root_rounds:
        final = result.root_rounds[-1]
        survivors = list(final.get("survivors", ()))
        scores = list(final.get("improvement_scores_after", ()))
        survivor = survivors[0] if survivors else None
        survivor_score = scores[0] if scores else None
    selected_q = None
    if result.action in result.root_actions:
        selected_q = result.root_q_values[result.root_actions.index(result.action)]
    board_valid = result.simulations == 64 and bool(result.root_rounds) and len(result.root_rounds[-1]["survivors"]) == 1 and result.action in result.root_actions and all(math.isfinite(value) for value in result.root_completed_q) and all(math.isfinite(value) and value > 0 for value in result.improved_policy)
    declaration_valid = declaration is not None and result.declaration_id == declaration.declaration_id and result.neutral_declaration_selected and result.root_survivor_q_before_declaration_choice is not None and result.root_survivor_q_before_declaration_choice <= 0.0
    winning_valid = declaration is not None and declaration.outcome == "WIN" and result.winning_declaration_id == declaration.declaration_id and result.declaration_id == declaration.declaration_id
    return {
        "pair_index": pair_index,
        "game_index": game_index,
        "ply": ply,
        "arm": arm,
        "search_seed": search_seed,
        "selected_action": result.action,
        "selected_declaration_id": result.declaration_id,
        "selected_declaration_outcome": declaration.outcome if declaration is not None else None,
        "root_actions": list(result.root_actions),
        "root_logits": list(result.root_logits),
        "root_gumbels": list(result.root_gumbels),
        "root_visits": list(result.root_visits),
        "root_q_values": list(result.root_q_values),
        "root_completed_q": list(result.root_completed_q),
        "final_survivor": survivor,
        "final_survivor_improvement_score": survivor_score,
        "root_survivor_q_before_declaration_choice": result.root_survivor_q_before_declaration_choice,
        "neutral_declaration_id": result.neutral_declaration_id,
        "neutral_declaration_available": result.neutral_declaration_available,
        "neutral_declaration_selected": result.neutral_declaration_selected,
        "neutral_declarations_encountered": result.neutral_declaration_encounters,
        "neutral_declarations_selected": result.neutral_declarations_selected,
        "neutral_declarations_declined": result.neutral_declarations_declined,
        "winning_declaration_id": result.winning_declaration_id,
        "simulations": result.simulations,
        "valid_search": board_valid or declaration_valid or winning_valid,
        "expanded_nodes": result.expanded_nodes,
        "leaf_evaluations": result.leaf_evaluations,
        "maximum_tree_depth": result.maximum_tree_depth,
        "wall_seconds": time.perf_counter() - started,
        "improved_policy_entropy": _entropy(result.improved_policy) if result.improved_policy else 0.0,
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
        seed = ARENA_SEARCH_SEED_BASE + 10000 * pair_index + ply
        started = time.perf_counter()
        try:
            result = SemanticGumbelMCTSV0(compiled, native_rules, checkpoint=checkpoint, policy=policy).search(session, search_seed=seed)
            declaration = _authoritative_declaration(native_rules, session, result.declaration_id) if result.declaration_id is not None else None
            metric = _metric(result, ply, pair_index, game_index, arm, seed, started, declaration)
            metrics.append(metric)
            if not metric["valid_search"]:
                raise RuntimeError("F121_SEARCH_VALIDITY_FAILED")
            if result.declaration_id is not None:
                session.declare(result.declaration_id)
                break
            session.submit(public_action(native_rules, result.action))
        except Exception as exc:
            error = str(exc)
            break
    status = session.result.status.value
    valid = error is None and status != "ongoing" and bool(metrics) and all(metric["valid_search"] for metric in metrics)
    return {"pair_index": pair_index, "game_index": game_index, "opening_index": opening.index, "child_owner": child_owner, "valid": valid, "error": error, "status": status, "winner": session.result.winner, "declaration_id": session.result.declaration_id, "declaration_outcome": session.result.declaration_outcome, "plies": len(metrics), "declarations": sum(metric["declaration_encounters"] for metric in metrics), "metrics": metrics}


def _seed_valid(games):
    for game in games:
        for metric in game["metrics"]:
            if metric["search_seed"] != ARENA_SEARCH_SEED_BASE + 10000 * game["pair_index"] + metric["ply"]:
                return False
    for first, second in zip(games[::2], games[1::2]):
        for left, right in zip(first["metrics"], second["metrics"]):
            if left["search_seed"] != right["search_seed"]:
                return False
    return True


def _null_signature(game):
    return {"decisions": [(metric["selected_action"], metric["selected_declaration_id"]) for metric in game["metrics"]], "status": game["status"], "winner": game["winner"], "plies": game["plies"], "search_seeds": [metric["search_seed"] for metric in game["metrics"]], "root_gumbels": [metric["root_gumbels"] for metric in game["metrics"]], "root_visits": [metric["root_visits"] for metric in game["metrics"]], "survivors": [metric["final_survivor"] for metric in game["metrics"]], "neutral": [(metric["neutral_declaration_available"], metric["neutral_declaration_selected"], metric["neutral_declaration_id"]) for metric in game["metrics"]]}


def _pair_score(first, second):
    return float(np.mean([0.5 if game["winner"] is None else float(game["winner"] == game["child_owner"]) for game in (first, second)]))


def _diagnostic(first, second):
    common = 0
    limit = min(len(first["metrics"]), len(second["metrics"]))
    while common < limit and (first["metrics"][common]["selected_action"], first["metrics"][common]["selected_declaration_id"]) == (second["metrics"][common]["selected_action"], second["metrics"][common]["selected_declaration_id"]):
        common += 1
    if common == limit:
        return {"pair_index": first["pair_index"], "common_prefix_length": common, "first_divergence_ply": None}
    left = first["metrics"][common]
    right = second["metrics"][common]
    parent_metric = left if left["arm"] == "parent" else right
    child_metric = left if left["arm"] == "child" else right
    return {"pair_index": first["pair_index"], "common_prefix_length": common, "first_divergence_ply": common, "common_random_seed": left["search_seed"], "parent_selected_action": parent_metric["selected_action"], "child_selected_action": child_metric["selected_action"], "parent_selected_declaration_id": parent_metric["selected_declaration_id"], "child_selected_declaration_id": child_metric["selected_declaration_id"], "parent_root_gumbels": parent_metric["root_gumbels"], "child_root_gumbels": child_metric["root_gumbels"], "parent_logits": dict(zip(parent_metric["root_actions"], parent_metric["root_logits"])), "child_logits": dict(zip(child_metric["root_actions"], child_metric["root_logits"])), "parent_neutral_declaration_available": parent_metric["neutral_declaration_available"], "child_neutral_declaration_available": child_metric["neutral_declaration_available"], "parent_selected_empirical_q": parent_metric["root_q_values"][parent_metric["root_actions"].index(parent_metric["selected_action"])] if parent_metric["selected_action"] in parent_metric["root_actions"] else None, "child_selected_empirical_q": child_metric["root_q_values"][child_metric["root_actions"].index(child_metric["selected_action"])] if child_metric["selected_action"] in child_metric["root_actions"] else None, "parent_final_survivor_q": parent_metric["root_survivor_q_before_declaration_choice"], "child_final_survivor_q": child_metric["root_survivor_q_before_declaration_choice"], "parent_final_improvement_score": parent_metric["final_survivor_improvement_score"], "child_final_improvement_score": child_metric["final_survivor_improvement_score"]}


def _replay_gate(compiled, native_rules):
    report_path = ROOT / ".generic_chess_flow" / "f120-shogi-gumbel-common-random-arena4" / "report.json"
    if not report_path.exists():
        return {"status": "SKIPPED_F120_REPORT_UNAVAILABLE"}
    report = json.loads(report_path.read_text(encoding="utf-8"))
    game = report.get("arena", {}).get("games", [])[5]
    corpus = generate_arena_openings(compiled, count=4, seed=1200801, min_plies=2, max_plies=6)
    session = GameSession(compiled)
    for action in corpus.openings[2].actions:
        session.submit(action)
    for metric in game.get("metrics", []):
        session.submit(public_action(native_rules, metric["selected_action"]))
    position = pack_semantic_search_position(compiled, native_rules, session)
    declarations = available_declarations(native_rules, position)
    return {"status": "SKIPPED_INTERNAL_STATE_NOT_RECONSTRUCTIBLE", "replayed_root_ply": len(game.get("metrics", [])), "root_declarations": [item.declaration_id for item in declarations], "reason": "F120 telemetry does not serialize internal tree states; the replayed root has no declaration, so the failure was inside the searched tree."}


def _stats(metrics, key):
    values = [float(metric[key]) for metric in metrics]
    return {"count": len(values), "min": min(values), "median": float(np.median(values)), "max": max(values), "sum": float(np.sum(values))} if values else {"count": 0}


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
    replay = _replay_gate(compiled, native_rules)
    corpus, offset = _opening_corpus(compiled)
    null_games = [_play(compiled, native_rules, checkpoint, parent, parent, corpus.openings[0], 0, 0, 0, False), _play(compiled, native_rules, checkpoint, parent, parent, corpus.openings[0], 0, 1, 1, False)]
    null = {"games": null_games, "exact_equality": _null_signature(null_games[0]) == _null_signature(null_games[1]), "seed_contract_valid": _seed_valid(null_games), "null_pair_score": _pair_score(null_games[0], null_games[1])}
    null["passed"] = all(game["valid"] for game in null_games) and null["exact_equality"] and null["seed_contract_valid"] and null["null_pair_score"] == 0.5
    report = {"work_order_id": "GENERICCHESS_F121_GUMBEL_NEUTRAL_DECLARATION_CRN_ARENA4", "implementation_sha": _implementation_sha(), "frozen_checkpoint_id": checkpoint.checkpoint_id, "value_compact_model_sha256": VALUE_COMPACT_MODEL_SHA, "parent_policy_sha256": parent.computed_model_sha256, "child_policy_sha256": child.computed_model_sha256, "requested_opening_seed": OPENING_SEED, "opening_selection_offset": offset, "opening_corpus": corpus.to_dict(), "regression": regression, "f120_replay_gate": replay, "null_pair": null}
    if not null["passed"]:
        report["classification"] = "F121_COMMON_RANDOM_NULL_PAIR_FAILED"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"classification": report["classification"], "null_pair_score": null["null_pair_score"]}, sort_keys=True))
        return 2
    games = [_play(compiled, native_rules, checkpoint, parent, child, corpus.openings[index // 2], index // 2, index, index % 2, True) for index in range(8)]
    pair_scores = [_pair_score(games[2 * index], games[2 * index + 1]) for index in range(4)]
    metrics = [metric for game in games for metric in game["metrics"]]
    seed_valid = _seed_valid(games)
    valid_games = sum(game["valid"] for game in games)
    better = sum(score > 0.5 for score in pair_scores)
    worse = sum(score < 0.5 for score in pair_scores)
    wdl = {"wins": sum(game["winner"] is not None and game["winner"] == game["child_owner"] for game in games), "draws": sum(game["winner"] is None for game in games), "losses": sum(game["winner"] is not None and game["winner"] != game["child_owner"] for game in games)}
    arena = {"games": games, "valid_game_count": valid_games, "pair_scores": pair_scores, "mean_pair_score": float(np.mean(pair_scores)), "child_better_pairs": better, "child_tied_pairs": sum(score == 0.5 for score in pair_scores), "child_worse_pairs": worse, "wdl": wdl, "crn_seed_contract_valid": seed_valid, "pair_diagnostics": [_diagnostic(games[2 * index], games[2 * index + 1]) for index in range(4)], "wall_seconds_by_arm": {"parent": _stats([m for m in metrics if m["arm"] == "parent"], "wall_seconds"), "child": _stats([m for m in metrics if m["arm"] == "child"], "wall_seconds")}, "expanded_nodes": _stats(metrics, "expanded_nodes"), "leaf_evaluations": _stats(metrics, "leaf_evaluations"), "maximum_tree_depth": _stats(metrics, "maximum_tree_depth"), "improved_policy_entropy": _stats(metrics, "improved_policy_entropy"), "declaration_count": sum(game["declarations"] for game in games), "neutral_declarations_selected": sum(metric["neutral_declaration_selected"] for metric in metrics), "neutral_declarations_declined": sum(metric["neutral_declarations_declined"] for metric in metrics)}
    if valid_games != 8 or not seed_valid:
        classification = "F121_GUMBEL_NEUTRAL_DECLARATION_ARENA4_INVALID"
    elif arena["mean_pair_score"] > 0.5 and better > worse:
        classification = "SHOGI_GUMBEL_COMPLETED_Q_NEUTRAL_DECL_CRN_ARENA4_CONFIRMED"
    else:
        classification = "SHOGI_GUMBEL_COMPLETED_Q_NEUTRAL_DECL_CRN_ARENA4_REJECTED"
    arena["classification"] = classification
    report["arena"] = arena
    report["classification"] = classification
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"classification": classification, "mean_pair_score": arena["mean_pair_score"], "valid_game_count": valid_games, "null_pair_passed": null["passed"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
