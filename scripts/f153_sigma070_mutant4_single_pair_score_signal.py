"""One hard-bounded role-swapped score-race pair for F153 sigma-.70 mutant_4."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.session.result import SessionStatus
from generic_chess.session.session import GameSession
from generic_chess.core.identity import position_identity_key
from scripts import f149_shogi_material_score_race_deep_openings as race
from scripts import f153_shogi_material_mutation_root_sensitivity as f153
from scripts import f158_shogi_sigma070_single_pair_diagnostic as f158
from scripts.f144_shogi_material_only_arena_evolution import GEN0_SEED, _ordering_values, _vector_record, gen0_vector

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "ff1197fc05acdaf9604dc7ab606dc16e3811a9fe"
F153_SOURCE_SHA256 = "F70CD249F2B68086BE670F6839704891CC21234EBA285E405AEC24969BA4EB55"
EXPECTED_RULES_SHA = "3f015f6631460f6c2a71a8d80898cd7d781d02e9b605639c701408b420e654e9"
EXPECTED_GEN0 = (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
EXPECTED_CHILD = (690, 382, 387, 3636, 498, 1000, 6221, 1298, 3157, 312, 3031, 2508, 966)
F151_SEED = 1_510_101
OPENING_INDEX = 0
OPENING_ID = "5738e1f589b8096372ce9c369692937123c13a383f70ceb44ec4f6a19a9bfd2b"
OPENING_PLIES = 30
CHILD_OWNER_ORDER = (0, 1)
MAX_GAMES = 2
MAX_CONCURRENT_GAMES = 1
MAX_TOTAL_PLIES_PER_GAME = 128
MAX_SEARCHED_PLIES_PER_GAME = MAX_TOTAL_PLIES_PER_GAME - OPENING_PLIES
MAX_NODES_PER_MOVE = 1_000
MAX_NODES_PER_GAME = MAX_SEARCHED_PLIES_PER_GAME * MAX_NODES_PER_MOVE
MAX_TOTAL_NODES = MAX_GAMES * MAX_NODES_PER_GAME
MAX_GAME_SECONDS = 7 * 60
MAX_WALL_SECONDS = 14 * 60
EXTERNAL_HARD_WALL_SECONDS = 15 * 60
ROLE_HORIZONS = (8, 16, 32, 64)
ROOT_GEN0_ACTION_KEY = '{"actor_type_id":"B","from":[5,5],"geometry_id":"g0","kind":"semantic_board","pattern_id":"legacy_000","promotion_target_id":null,"to":[4,4]}'
ROOT_MUTANT_ACTION_KEY = '{"actor_type_id":"B","from":[5,5],"geometry_id":"g1","kind":"semantic_board","pattern_id":"legacy_003","promotion_target_id":null,"to":[4,6]}'


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temp, path)


def _verify_identity(*, f153_result_path: Path, probe_result_path: Path) -> tuple[tuple[int, ...], tuple[int, ...], dict]:
    gen0 = tuple(gen0_vector(GEN0_SEED))
    child = tuple(f153.mutation_vectors_at_sigma(gen0, .70)[4])
    if gen0 != EXPECTED_GEN0 or child != EXPECTED_CHILD:
        raise AssertionError("material vector values do not match the corrected Chat order")
    if f153._sha(child) != EXPECTED_RULES_SHA:
        raise AssertionError("F153 sigma-.70 vector hash mismatch")

    raw = f153_result_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest().upper()
    if digest != F153_SOURCE_SHA256:
        raise AssertionError(f"unexpected F153 source evidence hash: {digest}")
    source = json.loads(raw.decode("utf-8"))
    if source.get("schema") != "F153_SHOGI_MATERIAL_MUTATION_ROOT_SENSITIVITY_V1":
        raise AssertionError("unexpected F153 source schema")
    stage = next((row for row in source["stages"] if row["sigma"] == .70 and row["position_limit"] == 12), None)
    if stage is None:
        raise AssertionError("F153 sigma-.70 stage is missing")
    rows = [row for row in stage["root_rows"] if
            row["position"].get("source") == "F151" and
            int(row["position"].get("seed", -1)) == F151_SEED and
            int(row["position"].get("opening_index", -1)) == OPENING_INDEX and
            row["position"].get("opening_id") == OPENING_ID]
    if len(rows) != 1:
        raise AssertionError("expected exactly one matching F153 root-A row")
    recorded = {row["label"]: row for row in rows[0]["root_searches"]}
    if recorded.get("Gen0", {}).get("vector_sha256") != f153._sha(gen0):
        raise AssertionError("F153 root-A Gen0 identity mismatch")
    if recorded.get("mutant_4", {}).get("vector_sha256") != EXPECTED_RULES_SHA:
        raise AssertionError("F153 root-A mutant_4 stage hash mismatch")
    if not recorded["mutant_4"].get("action_differs_from_gen0"):
        raise AssertionError("F153 root-A divergence is absent")
    if (recorded["Gen0"]["search"]["best_action_key"] != ROOT_GEN0_ACTION_KEY or
            recorded["mutant_4"]["search"]["best_action_key"] != ROOT_MUTANT_ACTION_KEY):
        raise AssertionError("F153 root-A action keys differ from the approved contrast")

    probe_raw = probe_result_path.read_bytes()
    probe_result = json.loads(probe_raw.decode("utf-8"))
    if probe_result.get("schema") != "F153_DIVERGENT_ROOT_SCORE_EVENT_PROBE_V1":
        raise AssertionError("unexpected F153 probe result schema")
    if probe_result.get("source_f153_result_sha256", "").upper() != F153_SOURCE_SHA256:
        raise AssertionError("published F153 probe references different source evidence")
    matches = [row for row in probe_result["contrasts"] if
               row["root"].get("opening_index") == OPENING_INDEX and
               row["root"].get("opening_id") == OPENING_ID and
               row.get("mutant") == "mutant_4"]
    if len(matches) != 1 or matches[0]["vectors"].get("mutant_sha256") != EXPECTED_RULES_SHA:
        raise AssertionError("published F153 event probe does not bind the approved child vector")
    return gen0, child, {"source_sha256": digest, "root_record": recorded,
                         "probe_sha256": hashlib.sha256(probe_raw).hexdigest()}


def _classify_pair(games: list[dict]) -> dict:
    if len(games) != MAX_GAMES or any(not game.get("completed") or not game.get("valid")
                                      or not game.get("first_root_action_reproduced") for game in games):
        classification = "MUTANT4_SINGLE_PAIR_INCONCLUSIVE"
    else:
        differentials = [game["mutant_points"] - game["gen0_points"] for game in games]
        total = sum(differentials)
        if total < 0:
            classification = "MUTANT4_SCORE_SIGNAL_REVERSES"
        elif total == 0 or (min(differentials) < 0 < max(differentials)):
            classification = "MUTANT4_SCORE_SIGNAL_ROLE_DEPENDENT_OR_CANCELLED"
        elif total > 0 and min(differentials) >= 0:
            classification = "MUTANT4_SCORE_SIGNAL_PERSISTS_AT_PAIR_LEVEL"
        else:
            classification = "MUTANT4_SCORE_SIGNAL_ROLE_DEPENDENT_OR_CANCELLED"
    valid = len(games) == MAX_GAMES and all(game.get("valid") for game in games)
    pair_score = None if not valid else sum(
        1.0 if game["winner"] == game["child_owner"] else 0.0 for game in games
    ) / MAX_GAMES
    child_points = sum(int(game.get("mutant_points", 0)) for game in games)
    gen0_points = sum(int(game.get("gen0_points", 0)) for game in games)
    return {
        "classification": classification,
        "valid_pair": valid,
        "pair_score": pair_score,
        "mutant4_total_points": child_points,
        "gen0_total_points": gen0_points,
        "aggregate_mutant_point_differential": child_points - gen0_points,
        "per_role_point_differentials": [
            {"child_owner": game["child_owner"], "mutant_minus_gen0": game.get("mutant_points", 0) - game.get("gen0_points", 0)}
            for game in games
        ],
        "threshold_10_reached_by_either_game": any(game.get("threshold_ply") is not None for game in games),
    }


def _play_one_game(compiled, opening, gen0, child, ordering, child_owner: int, *, deadline: float,
                   output_dir: Path) -> dict:
    game_started = time.monotonic()
    game_deadline = min(deadline, game_started + MAX_GAME_SECONDS)
    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    if len(session.history) != OPENING_PLIES or str(position_identity_key(session.state.position, compiled)) != OPENING_ID:
        raise AssertionError("reconstructed opening root identity mismatch")

    players = (
        f158._player(compiled, child if child_owner == 0 else gen0, ordering),
        f158._player(compiled, child if child_owner == 1 else gen0, ordering),
    )
    score = [0, 0]
    captures = [0, 0]
    checks = [0, 0]
    actions = []
    nodes = 0
    first_scoring_event = None
    first_root_action_reproduced = False
    first_root_action_key = None
    first_root_decision = None
    winner, reason, terminal_cause, threshold_ply = None, "", "ongoing", None
    incomplete_reason = None
    horizons = {}
    root_mover = session.state.position.side_to_move
    expected_first_key = ROOT_MUTANT_ACTION_KEY if child_owner == root_mover else ROOT_GEN0_ACTION_KEY
    if root_mover != 0:
        raise AssertionError("approved F151 index-0 opening no longer has expected side-to-move")

    while session.result.status is SessionStatus.ONGOING:
        if time.monotonic() >= game_deadline:
            incomplete_reason = "game_wall_cap"
            break
        if len(session.history) >= MAX_TOTAL_PLIES_PER_GAME:
            break
        if len(actions) >= MAX_SEARCHED_PLIES_PER_GAME:
            incomplete_reason = "searched_ply_cap"
            break
        if nodes >= MAX_NODES_PER_GAME:
            incomplete_reason = "game_node_cap"
            break
        mover = session.state.position.side_to_move
        decision = players[mover].choose_action(session, race._limits(MAX_NODES_PER_MOVE))
        decision_nodes = int(decision.nodes) + int(decision.qnodes)
        if decision_nodes > MAX_NODES_PER_MOVE or nodes + decision_nodes > MAX_NODES_PER_GAME:
            incomplete_reason = "node_cap"
            break
        nodes += decision_nodes
        if time.monotonic() > game_deadline:
            incomplete_reason = "game_wall_cap"
            break
        if decision.declaration is not None:
            session.declare(decision.declaration)
            terminal_cause = session.result.status.value
            if race._core_winner(session.result):
                winner, reason = session.result.winner, session.result.status.value
            break
        if decision.action is None or decision.action not in session.legal_actions():
            incomplete_reason = "no_legal_search_action"
            break
        action_dict = race.v2.action_to_dict(decision.action)
        action_key = json.dumps(action_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if not actions:
            first_root_action_key = action_key
            first_root_decision = {
                "action": action_dict,
                "action_key": action_key,
                "evaluator_controls_mover": mover == child_owner,
                "nodes": int(decision.nodes),
                "qnodes": int(decision.qnodes),
                "completed_depth": int(decision.completed_depth),
                "termination_reason": decision.termination_reason,
            }
            first_root_action_reproduced = action_key == expected_first_key
            if not first_root_action_reproduced:
                incomplete_reason = "root_action_reproduction_mismatch"
                break
        before = session.state.position
        after = session.submit(decision.action)
        event = race.score_event(before, decision.action, after.position, mover, compiled)
        score[mover] += int(event["points"])
        captures[mover] += int(event["capture"])
        checks[mover] += int(event["check"])
        scored_ply = len(actions) + 1
        action_row = {
            "scored_ply": scored_ply,
            "total_game_ply": OPENING_PLIES + scored_ply,
            "actor": mover,
            "action": action_dict,
            "action_key": action_key,
            "evaluator_controls_mover": mover == child_owner,
            **event,
            "scores_after_ply": list(score),
            "decision": {
                "nodes": int(decision.nodes), "qnodes": int(decision.qnodes),
                "completed_depth": int(decision.completed_depth),
                "termination_reason": decision.termination_reason,
            },
        }
        actions.append(action_row)
        if int(event["points"]) > 0 and first_scoring_event is None:
            first_scoring_event = {
                "scored_ply": scored_ply, "total_game_ply": OPENING_PLIES + scored_ply,
                "actor": mover, "event": {key: event[key] for key in ("capture", "check", "points")},
                "category": _event_category(event),
            }
        if scored_ply in ROLE_HORIZONS:
            horizons[str(scored_ply)] = list(score)

        if race._core_winner(session.result):
            winner, reason, terminal_cause = session.result.winner, session.result.status.value, session.result.status.value
            break
        threshold_winner, threshold_reason, threshold_valid = race.resolve_threshold(score, mover)
        if threshold_valid:
            winner, reason, terminal_cause, threshold_ply = threshold_winner, threshold_reason, "score_threshold", OPENING_PLIES + scored_ply
            break

    total_plies = len(session.history)
    completed = incomplete_reason is None
    if completed and winner is None and not reason:
        terminal_cause = session.result.status.value if session.result.status is not SessionStatus.ONGOING else "ply_cap"
        winner, reason, valid_terminal = race.resolve_terminal(session.result, score)
    else:
        valid_terminal = winner is not None and reason in {
            "score_threshold", "score_tiebreak", "checkmate", "perpetual_check", "declaration", "resignation",
        }
    valid = bool(completed and valid_terminal)
    result = {
        "game_index": child_owner,
        "child_owner": child_owner,
        "winner": winner,
        "result": reason if valid else "inconclusive" if incomplete_reason else "invalid_nondecisive_terminal",
        "decisive_reason": reason,
        "terminal_cause": terminal_cause,
        "threshold_ply": threshold_ply,
        "opening_id": opening.final_position_key,
        "opening_plies": len(opening.actions),
        "total_plies": total_plies,
        "searched_plies": len(actions),
        "nodes": nodes,
        "scores_by_side": list(score),
        "mutant_points": score[child_owner],
        "gen0_points": score[1 - child_owner],
        "capture_counts_by_side": captures,
        "check_counts_by_side": checks,
        "first_scoring_event": first_scoring_event,
        "first_root_mover": root_mover,
        "first_root_evaluator": "mutant_4" if root_mover == child_owner else "Gen0",
        "first_root_action_key": first_root_action_key,
        "first_root_action_expected_key": expected_first_key,
        "first_root_action_reproduced": first_root_action_reproduced,
        "first_root_decision": first_root_decision,
        "score_snapshots_after_searched_plies": horizons,
        "completed": completed,
        "valid": valid,
        "incomplete_reason": incomplete_reason,
        "elapsed_seconds": round(time.monotonic() - game_started, 6),
        "actions": actions,
    }
    result["score_snapshots_after_searched_plies"]["final"] = list(score)
    _atomic_json(output_dir / f"game-owner-{child_owner}.json", result)
    return result


def _event_category(event: dict) -> str:
    if event["capture"] and event["check"]:
        return "capture_plus_check"
    if event["capture"]:
        return "capture_only"
    if event["check"]:
        return "check_only"
    return "zero"


def run(*, output_dir: Path, f153_result_path: Path, probe_result_path: Path) -> dict:
    started = time.monotonic()
    deadline = started + MAX_WALL_SECONDS
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(["git", "rev-parse", "origin/sandbox"], cwd=ROOT, text=True).strip()
    parent = subprocess.check_output(["git", "rev-parse", "HEAD^"], cwd=ROOT, text=True).strip()
    if head != remote or (head != BASE_SHA and parent != BASE_SHA):
        raise AssertionError("pair run must use a published checkpoint directly based on the approved SHA")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite pair output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    bounds = {
        "maximum_games": MAX_GAMES,
        "maximum_concurrent_games": MAX_CONCURRENT_GAMES,
        "maximum_total_plies_per_game_including_opening": MAX_TOTAL_PLIES_PER_GAME,
        "opening_plies": OPENING_PLIES,
        "maximum_searched_plies_per_game": MAX_SEARCHED_PLIES_PER_GAME,
        "maximum_nodes_per_move": MAX_NODES_PER_MOVE,
        "maximum_nodes_per_game": MAX_NODES_PER_GAME,
        "maximum_total_nodes": MAX_TOTAL_NODES,
        "maximum_game_wall_seconds": MAX_GAME_SECONDS,
        "maximum_internal_wall_seconds": MAX_WALL_SECONDS,
        "external_hard_wall_seconds": EXTERNAL_HARD_WALL_SECONDS,
    }
    if MAX_TOTAL_PLIES_PER_GAME * MAX_GAMES != 256 or MAX_TOTAL_NODES != 196_000:
        raise AssertionError("declared upper bounds no longer match the approved envelope")
    _atomic_json(output_dir / "result.json", {
        "schema": "F153_SIGMA070_MUTANT4_SINGLE_PAIR_SCORE_SIGNAL_V1",
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "classification": "MUTANT4_SINGLE_PAIR_INCONCLUSIVE",
        "incomplete_reason": "run_in_progress_or_external_timeout",
        "bounds": bounds,
        "games": [],
    })
    gen0, child, evidence = _verify_identity(f153_result_path=f153_result_path,
                                              probe_result_path=probe_result_path)
    compiled = race._compile()
    openings = race.opening_corpus(compiled, F151_SEED, 32)
    matches = [opening for opening in openings if opening.index == OPENING_INDEX]
    if len(matches) != 1:
        raise AssertionError("F151 opening index 0 could not be reconstructed uniquely")
    opening = matches[0]
    if opening.final_position_key != OPENING_ID or len(opening.actions) != OPENING_PLIES:
        raise AssertionError("approved F151 opening identity/ply mismatch")
    ordering = _ordering_values(compiled)
    games = []
    game0 = _play_one_game(compiled, opening, gen0, child, ordering, 0,
                           deadline=deadline, output_dir=output_dir)
    games.append(game0)
    _atomic_json(output_dir / "result.json", {
        "schema": "F153_SIGMA070_MUTANT4_SINGLE_PAIR_SCORE_SIGNAL_V1",
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "classification": "MUTANT4_SINGLE_PAIR_INCONCLUSIVE",
        "incomplete_reason": "pair_incomplete_or_second_role_pending",
        "bounds": bounds,
        "identity": evidence,
        "opening": {"seed": F151_SEED, "index": OPENING_INDEX, "opening_id": opening.final_position_key,
                    "plies": len(opening.actions)},
        "games": games,
    })
    if game0["completed"] and game0["valid"] and game0["first_root_action_reproduced"] and time.monotonic() < deadline:
        game1 = _play_one_game(compiled, opening, gen0, child, ordering, 1,
                               deadline=deadline, output_dir=output_dir)
        games.append(game1)
    summary = _classify_pair(games)
    total_nodes = sum(game["nodes"] for game in games)
    if total_nodes > MAX_TOTAL_NODES or any(game["total_plies"] > MAX_TOTAL_PLIES_PER_GAME
                                           or game["searched_plies"] > MAX_SEARCHED_PLIES_PER_GAME
                                           or game["nodes"] > MAX_NODES_PER_GAME for game in games):
        raise AssertionError("observed run exceeded an approved static bound")
    result = {
        "schema": "F153_SIGMA070_MUTANT4_SINGLE_PAIR_SCORE_SIGNAL_V1",
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "strength_or_promotion_evidence": False,
        "base_git_sha": BASE_SHA,
        "git_sha": head,
        "source_result_hashes": evidence,
        "identity": {
            "gen0_values": list(gen0),
            "mutant4_values": list(child),
            "mutant_sigma": .70,
            "mutant_generation": 1,
            "mutant_index": 4,
            "mutant_f153_stage_vector_sha256": f153._sha(child),
            "mutant_f144_mapping_sha256": _vector_record(child)["sha256"],
        },
        "score_race": {
            "capture_points": race.CAPTURE_POINTS,
            "check_points": race.CHECK_POINTS,
            "threshold": race.SCORE_THRESHOLD,
            "formal_core_decisive_precedence": True,
        },
        "search": {
            "nodes_per_move": MAX_NODES_PER_MOVE,
            "max_depth": 12,
            "qdepth": [4, 8],
            "tt_max_entries": race.TT_MAX_ENTRIES,
            "fixed_ordering_values": ordering,
            "tuning": "SearchTuning()",
            "fresh_player_search_state_each_game": True,
        },
        "opening": {"source": "F151", "seed": F151_SEED, "index": OPENING_INDEX,
                    "opening_id": opening.final_position_key, "plies": len(opening.actions)},
        "bounds": bounds,
        "games": games,
        **summary,
        "elapsed_seconds": round(time.monotonic() - started, 6),
    }
    _atomic_json(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--f153-result", type=Path, required=True)
    parser.add_argument("--probe-result", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(output_dir=args.output_dir, f153_result_path=args.f153_result,
                 probe_result_path=args.probe_result)
    print(json.dumps({"classification": result["classification"], "games": len(result["games"]),
                      "pair_score": result["pair_score"], "total_nodes": sum(g["nodes"] for g in result["games"])}, sort_keys=True))
    return 0 if result["classification"] != "MUTANT4_SINGLE_PAIR_INCONCLUSIVE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
