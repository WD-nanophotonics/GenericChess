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
from generic_chess.core.actions import Action
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
        "early_stop": "stop before starting another game when node or wall cap is reached",
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
    success = completed and all(
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
