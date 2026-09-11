"""Run the bounded F86B quality calibration sample.

This is intentionally a small foreground calibration, not a benchmark or
Heavy job.  The ruleset sample is frozen before the result artifact is built.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.benchmark.agent_ladder import AgentLadder
from generic_chess.benchmark.game_quality import measure_game_quality
from generic_chess.benchmark.minimal_generator import MinimalGeneratedGame, generate_minimal_game
from generic_chess.core.actions import Action
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.session.session import GameSession


SAMPLES = (
    ("G4-A", 4, 860401, 2),
    ("G4-B", 4, 860402, 3),
    ("G5-A", 5, 860501, 3),
)
LADDER_BUDGETS = {
    "very_shallow": (16, 2),
    "low_node": (64, 4),
    "medium_node": (256, 6),
}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _freeze_rulesets(output_dir: Path) -> tuple[tuple[str, MinimalGeneratedGame], ...]:
    games = tuple(
        (sample_id, generate_minimal_game(seed, board_size=board_size, ordinary_count=ordinary_count))
        for sample_id, board_size, seed, ordinary_count in SAMPLES
    )
    _write_json(
        output_dir / "rulesets.json",
        {
            "schema_version": 1,
            "sample": [
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
        },
    )
    return games


def _random_action(session: GameSession, rng: random.Random) -> Action:
    actions = session.legal_actions()
    return actions[rng.randrange(len(actions))]


def _player_action(
    name: str,
    game: MinimalGeneratedGame,
    session: GameSession,
    rng: random.Random,
    players: dict[str, AlphaBetaPlayer],
) -> tuple[Action, dict[str, object]]:
    if name == "random_legal":
        return _random_action(session, rng), {"agent": name, "nodes": 0, "qnodes": 0}
    max_nodes, max_depth = LADDER_BUDGETS[name]
    decision = players[name].choose_action(
        session,
        SearchLimits(max_nodes=max_nodes, max_depth=max_depth, quiescence_max_depth=0),
    )
    action = decision.action
    if action is None:
        action = _random_action(session, rng)
    return action, {
        "agent": name,
        "nodes": decision.nodes,
        "qnodes": decision.qnodes,
        "total_nodes": decision.nodes + decision.qnodes,
        "completed_depth": decision.completed_depth,
        "termination_reason": decision.termination_reason,
    }


def _play_ladder_game(
    game: MinimalGeneratedGame,
    seats: tuple[str, str],
    seed: int,
) -> dict[str, object]:
    session = GameSession(game.compiled)
    rng = random.Random(seed)
    players = {
        name: AlphaBetaPlayer(game.compiled, use_disk_cache=False)
        for name in seats
        if name != "random_legal"
    }
    telemetry: list[dict[str, object]] = []
    while session.result.status.value == "ongoing" and len(session.history) < 32:
        actor = session.state.position.side_to_move
        action, event = _player_action(seats[actor], game, session, rng, players)
        telemetry.append(event)
        session.submit(action)
    winner = session.result.winner
    stronger = seats[1]
    stronger_score = None
    if session.result.status.value != "ongoing":
        stronger_score = 0.5 if winner is None else (1.0 if seats[winner] == stronger else 0.0)
    return {
        "seats": list(seats),
        "seed": seed,
        "plies": len(session.history),
        "status": session.result.status.value,
        "winner": winner,
        "stronger_score": stronger_score,
        "actual_search_nodes": sum(int(event.get("total_nodes", 0)) for event in telemetry),
        "telemetry": telemetry,
    }


def _ladder_results(game: MinimalGeneratedGame) -> dict[str, object]:
    ladder = AgentLadder()
    pair_rows = []
    total_games = 0
    total_nodes = 0
    for pair_index, pair in enumerate(zip(ladder.names, ladder.names[1:])):
        games = [
            _play_ladder_game(game, pair, 860600 + pair_index * 2),
            _play_ladder_game(game, (pair[1], pair[0]), 860601 + pair_index * 2),
        ]
        total_games += len(games)
        total_nodes += sum(int(row["actual_search_nodes"]) for row in games)
        scores = [row["stronger_score"] for row in games if row["stronger_score"] is not None]
        pair_rows.append(
            {
                "weaker": pair[0],
                "stronger": pair[1],
                "game_count": len(games),
                "resolved_game_count": len(scores),
                "stronger_mean_score": sum(scores) / len(scores) if scores else None,
                "games": games,
            }
        )
    paired_scores = {
        (row["weaker"], row["stronger"]): row["stronger_mean_score"]
        for row in pair_rows
        if row["stronger_mean_score"] is not None
    }
    matchup = ladder.evaluate_adjacent_matchups(paired_scores)
    return {
        "ruleset_sample_id": "G4-A",
        "pair_count": len(pair_rows),
        "played_game_count": total_games,
        "actual_search_nodes": total_nodes,
        "pair_results": pair_rows,
        "ladder_summary": matchup,
    }


def run(output_dir: Path) -> dict[str, object]:
    frozen = _freeze_rulesets(output_dir)
    quality = []
    total_quality_games = 0
    total_probe_nodes = 0
    for sample_id, game in frozen:
        profile = measure_game_quality(game, trajectory_count=2, max_ply=32, seed=game.seed + 1000)
        row = {"sample_id": sample_id, **profile.to_dict()}
        quality.append(row)
        total_quality_games += profile.played_game_count
        total_probe_nodes += profile.tactical_probe_nodes
    ladder = _ladder_results(dict(frozen)["G4-A"])
    results = {
        "schema_version": 1,
        "sample_ids": [sample_id for sample_id, _ in frozen],
        "generated_ruleset_count": len(frozen),
        "quality_policy_pair_count": sum(row["paired_game_count"] for row in quality),
        "quality_played_game_count": total_quality_games,
        "tactical_probe_position_count": sum(row["tactical_probe_position_count"] for row in quality),
        "tactical_probe_nodes": total_probe_nodes,
        "ladder": ladder,
        "quality": quality,
        "f85_actual_compute": 0,
        "classification_policy": "UNRESOLVED_WITHOUT_EXPLICIT_CALIBRATED_THRESHOLDS",
    }
    _write_json(output_dir / "results.json", results)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/f86b_quality_calibration"),
    )
    args = parser.parse_args()
    result = run(args.output_dir)
    print(json.dumps({key: result[key] for key in (
        "generated_ruleset_count", "quality_policy_pair_count", "quality_played_game_count",
        "tactical_probe_position_count", "tactical_probe_nodes", "f85_actual_compute",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
