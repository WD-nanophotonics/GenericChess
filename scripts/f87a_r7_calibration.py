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


def _random_action(session: GameSession, rng: random.Random) -> Action:
    actions = session.legal_actions()
    return actions[rng.randrange(len(actions))]


def _play_game(
    game: MinimalGeneratedGame,
    seats: tuple[str, str],
    seed: int,
    node_budget: int,
    deadline: float,
) -> tuple[dict[str, Any], int, str | None]:
    session = GameSession(game.compiled)
    rng = random.Random(seed)
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
            action = _random_action(session, rng)
            event = {"policy": policy, "nodes": 0, "termination_reason": "random"}
        else:
            max_nodes, max_depth = POLICIES[policy]
            decision = players[policy].choose_action(
                session,
                SearchLimits(max_nodes=max_nodes, max_depth=max_depth, quiescence_max_depth=0),
            )
            action = decision.action or _random_action(session, rng)
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


def _score(rows: list[dict[str, Any]], stronger: str) -> float | None:
    scores = []
    for row in rows:
        if not row["resolved"]:
            continue
        if row["winner"] is None:
            scores.append(0.5)
        else:
            scores.append(1.0 if row["seats"][row["winner"]] == stronger else 0.0)
    return sum(scores) / len(scores) if scores else None


def run(output_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + WALL_CAP_SECONDS
    games = _freeze_samples(output_dir)
    rows = []
    total_nodes = 0
    stop_reason = None
    for sample_id, game in games:
        for matchup_index, (weaker, stronger) in enumerate(MATCHUPS):
            if total_nodes >= NODE_CAP or time.monotonic() >= deadline:
                stop_reason = "EARLY_STOP_NODE_CAP" if total_nodes >= NODE_CAP else "EARLY_STOP_WALL_CAP"
                break
            for swapped in (False, True):
                seats = (weaker, stronger) if not swapped else (stronger, weaker)
                row, nodes, game_stop = _play_game(
                    game, seats, 870700 + len(rows), NODE_CAP - total_nodes, deadline
                )
                rows.append({"sample_id": sample_id, "matchup": [weaker, stronger], **row})
                total_nodes += nodes
                if game_stop:
                    stop_reason = game_stop
                    break
            if stop_reason:
                break
        if stop_reason:
            break
    matchup_scores = {
        f"{weaker}>{stronger}": _score(
            [row for row in rows if row["matchup"] == [weaker, stronger]], stronger
        )
        for weaker, stronger in MATCHUPS
    }
    completed = stop_reason is None and len(rows) == len(games) * len(MATCHUPS) * 2
    success = completed and all(score is not None and score > 0.5 for score in matchup_scores.values())
    result = {
        "schema_version": 1,
        "experiment": "GENERICCHESS-F87A-R7-CALIBRATION",
        "status": "RESULT_COMPLETE" if completed else "EARLY_STOP",
        "baseline_sha": BASELINE_SHA,
        "sample_ids": [sample_id for sample_id, _ in games],
        "rows": rows,
        "played_game_count": len(rows),
        "expected_game_count": len(games) * len(MATCHUPS) * 2,
        "actual_search_nodes": total_nodes,
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
