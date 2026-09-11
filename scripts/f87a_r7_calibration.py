"""F87A-R7 cheap calibration for short-horizon policy-improvement signals."""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path
from typing import Any

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.benchmark.minimal_generator import MinimalGeneratedGame, generate_minimal_game
from generic_chess.core.actions import Action, action_to_dict
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.session.session import GameSession


BASELINE_SHA = "7cf67307e66abe79f4cac92b5ddcf7985ac07365"
ARTIFACT_DIR = Path("artifacts/f87a_r7_calibration")
SAMPLES = (
    ("R7-A", 4, 870401, 2),
    ("R7-B", 5, 870501, 3),
)
POLICIES = {
    "random_legal": None,
    "low_node": (64, 4),
    "medium_node": (256, 6),
}
MATCHUPS = (("random_legal", "low_node"), ("low_node", "medium_node"))
PAIR_COUNT = 1
MAX_PLY = 24
NODE_CAP = 100_000
WALL_CAP_SECONDS = 600
T1_DIAGNOSTIC_MAX_ROOTS = 4
T1_DIAGNOSTIC_NODE_CAP = 4_096
T1_DIAGNOSTIC_WALL_CAP_SECONDS = 10
T1_REFERENCE_NODE_BUDGET = 128
T1_REFERENCE_MAX_DEPTH = 5


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _freeze_samples(output_dir: Path) -> tuple[tuple[str, MinimalGeneratedGame], ...]:
    games = tuple(
        (sample_id, generate_minimal_game(seed, board_size=board_size, ordinary_count=ordinary_count))
        for sample_id, board_size, seed, ordinary_count in SAMPLES
    )
    _write_json(output_dir / "manifest.json", {
        "schema_version": 1,
        "experiment": "GENERICCHESS-F87A-R7-CALIBRATION",
        "status": "PREP_FROZEN",
        "baseline_sha": BASELINE_SHA,
        "samples": [
            {
                "sample_id": sample_id,
                "board_size": game.board_size,
                "seed": game.seed,
                "ordinary_count": game.ordinary_count,
                "ruleset_fingerprint": game.ruleset_fingerprint,
                "ruleset": ruleset_to_dict(game.ruleset),
            }
            for sample_id, game in games
        ],
        "policies": list(POLICIES),
        "matchups": [list(pair) for pair in MATCHUPS],
        "pair_count": PAIR_COUNT,
        "max_ply": MAX_PLY,
        "node_cap": NODE_CAP,
        "wall_cap_seconds": WALL_CAP_SECONDS,
        "external_engine_used": False,
        "cap_semantics": "coarse_stop_before_starting_next_ply_or_game",
        "early_stop": "stop before starting another ply or game when node or wall cap is reached",
        "route_split": {
            "success": "proceed to a small reproducibility-controlled weight-update calibration",
            "failure": "stop update route and return to T1 action-spectrum/regret diagnostics",
        },
    })
    return games


def _random_action(session: GameSession, tape: list[int], cursor: list[int]) -> Action:
    actions = session.legal_actions()
    index = tape[cursor[0] % len(tape)] % len(actions)
    cursor[0] += 1
    return actions[index]


def _action_key(action: Action | None) -> str | None:
    if action is None:
        return None
    return json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))


def _session_at_history(game: MinimalGeneratedGame, history: tuple[Action, ...]) -> GameSession:
    session = GameSession(game.compiled)
    for action in history:
        session.submit(action)
    return session


def _reference_action_evaluation(
    game: MinimalGeneratedGame,
    history: tuple[Action, ...],
    action: Action,
    remaining_nodes: int,
) -> tuple[dict[str, Any], int]:
    child = _session_at_history(game, history)
    child.submit(action)
    if child.result.status.value != "ongoing":
        return {
            "value": None,
            "nodes": 0,
            "completed_depth": 0,
            "termination_reason": "terminal_after_candidate",
        }, 0
    decision = AlphaBetaPlayer(game.compiled, use_disk_cache=False).choose_action(
        child,
        SearchLimits(
            max_nodes=min(T1_REFERENCE_NODE_BUDGET, remaining_nodes),
            max_depth=T1_REFERENCE_MAX_DEPTH,
            quiescence_max_depth=0,
        ),
    )
    consumed = decision.nodes + decision.qnodes
    return {
        "value": -decision.score,
        "nodes": consumed,
        "completed_depth": decision.completed_depth,
        "termination_reason": decision.termination_reason,
    }, consumed


def _t1_gate_passes(diagnostic: dict[str, Any]) -> bool:
    return (
        diagnostic.get("status") == "COMPLETE"
        and diagnostic.get("next_step") == "SHORT_SEAT_SWAPPED_VALIDATION"
    )


def _t1_action_spectrum_regret(games: tuple[tuple[str, MinimalGeneratedGame], ...]) -> dict[str, Any]:
    """Run a tiny, pre-bounded root-spectrum probe before paired games."""
    started = time.monotonic()
    deadline = started + T1_DIAGNOSTIC_WALL_CAP_SECONDS
    rows: list[dict[str, Any]] = []
    nodes = 0
    stop_reason = None
    for sample_id, game in games:
        session = GameSession(game.compiled)
        for _ in range(2):
            if len(rows) >= T1_DIAGNOSTIC_MAX_ROOTS:
                break
            if time.monotonic() >= deadline:
                stop_reason = "EARLY_STOP_WALL_CAP"
                break
            history = tuple(record.action for record in session.history)
            remaining_nodes = T1_DIAGNOSTIC_NODE_CAP - nodes
            if remaining_nodes <= 0:
                stop_reason = "EARLY_STOP_NODE_CAP"
                break
            low = AlphaBetaPlayer(game.compiled, use_disk_cache=False).choose_action(
                session,
                SearchLimits(max_nodes=min(64, remaining_nodes), max_depth=4, quiescence_max_depth=0),
            )
            nodes += low.nodes + low.qnodes
            if nodes >= T1_DIAGNOSTIC_NODE_CAP:
                stop_reason = "EARLY_STOP_NODE_CAP"
                break
            remaining_nodes = T1_DIAGNOSTIC_NODE_CAP - nodes
            medium = AlphaBetaPlayer(game.compiled, use_disk_cache=False).choose_action(
                session,
                SearchLimits(max_nodes=min(256, remaining_nodes), max_depth=6, quiescence_max_depth=0),
            )
            nodes += medium.nodes + medium.qnodes
            if nodes >= T1_DIAGNOSTIC_NODE_CAP:
                stop_reason = "EARLY_STOP_NODE_CAP"
                break
            low_key = _action_key(low.action)
            medium_key = _action_key(medium.action)
            reference_evaluations: dict[str, dict[str, Any]] = {}
            candidates = (("low", low.action, low_key), ("medium", medium.action, medium_key))
            for label, action, key in candidates:
                if action is None or key in reference_evaluations:
                    continue
                remaining_nodes = T1_DIAGNOSTIC_NODE_CAP - nodes
                if remaining_nodes <= 0:
                    stop_reason = "EARLY_STOP_NODE_CAP"
                    break
                evaluation, consumed = _reference_action_evaluation(
                    game, history, action, remaining_nodes
                )
                nodes += consumed
                reference_evaluations[key] = evaluation
                if nodes >= T1_DIAGNOSTIC_NODE_CAP:
                    stop_reason = "EARLY_STOP_NODE_CAP"
                    break
            if stop_reason:
                break
            low_reference = reference_evaluations.get(low_key) if low_key else None
            medium_reference = reference_evaluations.get(medium_key) if medium_key else None
            low_action_value = None if low_reference is None else low_reference["value"]
            medium_action_value = None if medium_reference is None else medium_reference["value"]
            regret_proxy = (
                max(0.0, float(medium_action_value - low_action_value))
                if low_action_value is not None and medium_action_value is not None
                else None
            )
            rows.append({
                "sample_id": sample_id,
                "ply": len(history),
                "legal_action_count": len(session.legal_actions()),
                "low_action": low_key,
                "medium_action": medium_key,
                "action_disagreement": low_key != medium_key,
                "regret_proxy": regret_proxy,
                "low_nodes": low.nodes + low.qnodes,
                "medium_nodes": medium.nodes + medium.qnodes,
                "low_completed_depth": low.completed_depth,
                "medium_completed_depth": medium.completed_depth,
                "low_termination_reason": low.termination_reason,
                "medium_termination_reason": medium.termination_reason,
                "reference_node_budget": T1_REFERENCE_NODE_BUDGET,
                "reference_max_depth": T1_REFERENCE_MAX_DEPTH,
                "reference_evaluations": reference_evaluations,
            })
            actions = session.legal_actions()
            if not actions:
                break
            session.submit(actions[0])
        if stop_reason or len(rows) >= T1_DIAGNOSTIC_MAX_ROOTS:
            break
    if nodes > T1_DIAGNOSTIC_NODE_CAP:
        stop_reason = "EARLY_STOP_NODE_CAP"
    complete = stop_reason is None and len(rows) == T1_DIAGNOSTIC_MAX_ROOTS
    disagreements = sum(row["action_disagreement"] for row in rows)
    regret_values = [row["regret_proxy"] for row in rows if row["regret_proxy"] is not None]
    next_step = "SHORT_SEAT_SWAPPED_VALIDATION" if complete else "NO_INTERVENTION_DATA"
    return {
        "status": "COMPLETE" if complete else "DEFER_CENSORED",
        "root_count": len(rows),
        "expected_root_count": T1_DIAGNOSTIC_MAX_ROOTS,
        "rows": rows,
        "search_nodes": nodes,
        "node_cap": T1_DIAGNOSTIC_NODE_CAP,
        "wall_seconds": time.monotonic() - started,
        "wall_cap_seconds": T1_DIAGNOSTIC_WALL_CAP_SECONDS,
        "stop_reason": stop_reason,
        "action_disagreement_count": disagreements,
        "mean_regret_proxy": (
            sum(regret_values) / len(regret_values) if regret_values else None
        ),
        "decision_rule": "complete_T1_probe_then_validate_with_short_seat_swapped_pairs",
        "next_step": next_step,
    }


def _play_game(
    game: MinimalGeneratedGame,
    seats: tuple[str, str],
    seed: int,
    random_tape: list[int],
    node_budget: int,
    deadline: float,
) -> tuple[dict[str, Any], int, str | None]:
    session = GameSession(game.compiled)
    tape_cursor = [0]
    players = {
        name: AlphaBetaPlayer(game.compiled, use_disk_cache=False)
        for name in seats if POLICIES[name] is not None
    }
    telemetry = []
    nodes = 0
    stop_reason = None
    while session.result.status.value == "ongoing" and len(session.history) < MAX_PLY:
        if time.monotonic() >= deadline:
            stop_reason = "EARLY_STOP_WALL_CAP"
            break
        actor = session.state.position.side_to_move
        policy = seats[actor]
        if policy == "random_legal":
            action = _random_action(session, random_tape, tape_cursor)
            event = {"policy": policy, "nodes": 0, "termination_reason": "random"}
        else:
            max_nodes, max_depth = POLICIES[policy]
            remaining_nodes = node_budget - nodes
            if remaining_nodes <= 0:
                stop_reason = "EARLY_STOP_NODE_CAP"
                break
            decision = players[policy].choose_action(
                session,
                SearchLimits(max_nodes=min(max_nodes, remaining_nodes), max_depth=max_depth, quiescence_max_depth=0),
            )
            action = decision.action or _random_action(session, random_tape, tape_cursor)
            event = {
                "policy": policy,
                "nodes": decision.nodes,
                "qnodes": decision.qnodes,
                "total_nodes": decision.nodes + decision.qnodes,
                "completed_depth": decision.completed_depth,
                "termination_reason": decision.termination_reason,
            }
        telemetry.append(event)
        nodes += int(event.get("total_nodes", 0))
        session.submit(action)
        if nodes >= node_budget:
            stop_reason = "EARLY_STOP_NODE_CAP"
            break
    status = session.result.status.value
    return {
        "seats": list(seats),
        "seed": seed,
        "plies": len(session.history),
        "status": status,
        "winner": session.result.winner,
        "resolved": status != "ongoing",
        "telemetry": telemetry,
        "search_nodes": nodes,
        "stop_reason": stop_reason,
    }, nodes, stop_reason


def _pair_summary(rows: list[dict[str, Any]], stronger: str) -> dict[str, Any]:
    resolved = [row for row in rows if row["resolved"]]
    censored = [row for row in rows if not row["resolved"]]
    if len(rows) != 2 or censored:
        return {
            "paired_score": None,
            "pair_resolved": False,
            "resolved_game_count": len(resolved),
            "censored_game_count": len(censored),
            "status": "DEFER_CENSORED",
        }
    scores = []
    for row in resolved:
        if row["winner"] is None:
            scores.append(0.5)
        else:
            scores.append(1.0 if row["seats"][row["winner"]] == stronger else 0.0)
    return {
        "paired_score": sum(scores) / len(scores),
        "pair_resolved": True,
        "resolved_game_count": 2,
        "censored_game_count": 0,
        "status": "RESOLVED",
    }


def run(output_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + WALL_CAP_SECONDS
    games = _freeze_samples(output_dir)
    t1_diagnostic = _t1_action_spectrum_regret(games)
    rows = []
    pair_summaries = []
    total_nodes = 0
    stop_reason = None
    for sample_index, (sample_id, game) in enumerate(games):
        for matchup_index, (weaker, stronger) in enumerate(MATCHUPS):
            if total_nodes >= NODE_CAP or time.monotonic() >= deadline:
                stop_reason = "EARLY_STOP_NODE_CAP" if total_nodes >= NODE_CAP else "EARLY_STOP_WALL_CAP"
                break
            pair_seed = 870700 + sample_index * 100 + matchup_index * 10
            random_source = random.Random(pair_seed)
            random_tape = [random_source.getrandbits(64) for _ in range(MAX_PLY)]
            pair_rows = []
            for swapped in (False, True):
                seats = (weaker, stronger) if not swapped else (stronger, weaker)
                row, nodes, game_stop = _play_game(
                    game, seats, pair_seed, random_tape, NODE_CAP - total_nodes, deadline
                )
                row = {"sample_id": sample_id, "matchup": [weaker, stronger], **row}
                rows.append(row)
                pair_rows.append(row)
                total_nodes += nodes
                if game_stop:
                    stop_reason = game_stop
                    break
            if stop_reason:
                break
            pair_summaries.append({
                "sample_id": sample_id,
                "matchup": [weaker, stronger],
                "stronger_policy": stronger,
                **_pair_summary(pair_rows, stronger),
            })
        if stop_reason:
            break
    matchup_scores = {}
    for weaker, stronger in MATCHUPS:
        pairs = [row for row in pair_summaries if row["matchup"] == [weaker, stronger]]
        valid_scores = [row["paired_score"] for row in pairs if row["pair_resolved"]]
        key = f"{stronger}_score_vs_{weaker}"
        matchup_scores[key] = {
            "paired_score": sum(valid_scores) / len(valid_scores) if len(valid_scores) == len(pairs) and pairs else None,
            "sample_pair_count": len(pairs),
            "resolved_pair_count": sum(row["pair_resolved"] for row in pairs),
            "censored_pair_count": sum(not row["pair_resolved"] for row in pairs),
            "status": "RESOLVED" if len(pairs) == len(games) and all(row["pair_resolved"] for row in pairs) else "DEFER_CENSORED",
        }
    completed = stop_reason is None and len(rows) == len(games) * len(MATCHUPS) * 2
    success = _t1_gate_passes(t1_diagnostic) and completed and all(
        summary["status"] == "RESOLVED"
        and summary["paired_score"] is not None
        and summary["paired_score"] > 0.5
        for summary in matchup_scores.values()
    )
    result = {
        "schema_version": 1,
        "experiment": "GENERICCHESS-F87A-R7-CALIBRATION",
        "status": "RESULT_COMPLETE" if completed else "EARLY_STOP",
        "baseline_sha": BASELINE_SHA,
        "sample_ids": [sample_id for sample_id, _ in games],
        "rows": rows,
        "pair_summaries": pair_summaries,
        "played_game_count": len(rows),
        "expected_game_count": len(games) * len(MATCHUPS) * 2,
        "actual_search_nodes": total_nodes,
        "resolved_game_count": sum(row["resolved"] for row in rows),
        "censored_game_count": sum(not row["resolved"] for row in rows),
        "resolved_pair_count": sum(row["pair_resolved"] for row in pair_summaries),
        "censored_pair_count": sum(not row["pair_resolved"] for row in pair_summaries),
        "node_cap": NODE_CAP,
        "wall_seconds": time.monotonic() - started,
        "wall_cap_seconds": WALL_CAP_SECONDS,
        "stop_reason": stop_reason,
        "matchup_scores": matchup_scores,
        "route": "PROCEED_WEIGHT_UPDATE_CALIBRATION" if success else "RETURN_T1_ACTION_SPECTRUM_REGRET",
        "success": success,
        "external_engine_used": False,
        "cap_semantics": "coarse_stop_before_starting_next_ply_or_game",
        "t1_diagnostic": t1_diagnostic,
        "t1_gate_passed": _t1_gate_passes(t1_diagnostic),
    }
    _write_json(output_dir / "results.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ARTIFACT_DIR)
    args = parser.parse_args()
    result = run(args.output_dir)
    print(json.dumps({key: result[key] for key in (
        "status", "played_game_count", "expected_game_count", "actual_search_nodes",
        "stop_reason", "matchup_scores", "route", "success",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
