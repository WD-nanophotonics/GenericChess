"""F158: strictly bounded, single-pair sigma-.70 Shogi causal diagnostic."""

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
from scripts import f149_shogi_material_score_race_deep_openings as race
from scripts import f153_shogi_material_mutation_root_sensitivity as f153
from scripts.f144_shogi_material_only_arena_evolution import (
    GEN0_SEED,
    TYPE_IDS,
    _ordering_values,
    _player,
    _sha,
    _vector_record,
    gen0_vector,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "F158_SHOGI_SIGMA070_SINGLE_PAIR_CAUSAL_DIAGNOSTIC_V1"
OPENING_SEED = 1_580_101
OPENING_COUNT = 1
MUTANT_INDEX = 0
GENERATION = 1
SIGMA = 0.70
MAX_GAMES = 2
MAX_CONCURRENT_GAMES = 1
MAX_NODES_PER_MOVE = 1_000
MAX_TOTAL_PLIES_PER_GAME = 128  # includes the neutral opening plies
MAX_TOTAL_NODES = 224_000  # 2 * (128 - minimum 16 opening plies) * 1,000
MAX_WALL_SECONDS = 14 * 60  # reserve one minute for the Heavy hard-stop and final write
MAX_GAME_SECONDS = 7 * 60
ROLE_ORDER = (0, 1)
HISTORICAL_OPENING_IDS = {
    "5738e1f589b8096372ce9c369692937123c13a383f70ceb44ec4f6a19a9bfd2b",
    "742b4fc33ad8a8e9e57369f74b7544245622932fe16d99326f82a9163c1b801c",
    "b046dec8bd8675adfbbc6dc1c0d439ffbd878c8b08a433ab84abb200b119160b",
}
PRIOR_ROOT_DIVERGENCE = {
    "source": "F153 sigma .70 stage (position_limit=12), mutant_0",
    "opening_id": "742b4fc33ad8a8e9e57369f74b7544245622932fe16d99326f82a9163c1b801c",
    "opening_source": "F151 seed 1510101; not reused by this diagnostic",
}


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temp, path)


def play_capped_game(compiled, opening, gen0, mutant, child_owner, ordering_values, *,
                     deadline: float, game_timeout: float) -> dict:
    """Play one role assignment with hard per-game ply, node, and wall limits."""
    game_started = time.monotonic()
    game_deadline = min(deadline, game_started + game_timeout)
    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    players = (
        _player(compiled, mutant if child_owner == 0 else gen0, ordering_values),
        _player(compiled, mutant if child_owner == 1 else gen0, ordering_values),
    )
    scores, captures, checks, actions = [0, 0], [0, 0], [0, 0], []
    winner, reason, cause, threshold_ply = None, "", "ongoing", None
    nodes_used = 0
    incomplete_reason = None

    while session.result.status is SessionStatus.ONGOING:
        if time.monotonic() >= game_deadline:
            incomplete_reason = "wall_clock_cap"
            break
        if len(session.history) >= MAX_TOTAL_PLIES_PER_GAME:
            break
        mover = session.state.position.side_to_move
        decision = players[mover].choose_action(session, race._limits(MAX_NODES_PER_MOVE))
        if time.monotonic() >= game_deadline:
            incomplete_reason = "wall_clock_cap"
            break
        move_nodes = int(decision.nodes) + int(decision.qnodes)
        if move_nodes > MAX_NODES_PER_MOVE or nodes_used + move_nodes > MAX_TOTAL_NODES // MAX_GAMES:
            incomplete_reason = "node_cap"
            break
        nodes_used += move_nodes
        if decision.declaration is not None:
            session.declare(decision.declaration)
            result = session.result
            cause = result.status.value
            if race._core_winner(result):
                winner, reason = result.winner, result.status.value
            break
        if decision.action is None or decision.action not in session.legal_actions():
            raise RuntimeError("AlphaBeta returned no legal action")
        before = session.state.position
        after = session.submit(decision.action)
        event = race.score_event(before, decision.action, after.position, mover, compiled)
        scores[mover] += event["points"]
        captures[mover] += event["capture"]
        checks[mover] += event["check"]
        actions.append({"actor": mover, "action": race.v2.action_to_dict(decision.action), **event, "scores": list(scores)})
        result = session.result
        if race._core_winner(result):
            winner, reason, cause = result.winner, result.status.value, result.status.value
            break
        threshold_winner, threshold_reason, threshold_valid = race.resolve_threshold(scores, mover)
        if threshold_valid:
            winner, reason, cause = threshold_winner, threshold_reason, "score_threshold"
            threshold_ply = len(session.history)
            break

    result = session.result
    plies = len(session.history)
    if incomplete_reason is None and winner is None and not reason:
        cause = result.status.value if result.status is not SessionStatus.ONGOING else "max_plies"
        winner, reason, valid = race.resolve_terminal(result, scores)
    else:
        valid = winner is not None and reason in {
            "score_threshold", "score_tiebreak", "checkmate", "perpetual_check",
            "declaration", "resignation",
        }
    completed = incomplete_reason is None
    return {
        "started": True,
        "child_owner": child_owner,
        "winner": winner,
        "result": reason if valid else "inconclusive" if incomplete_reason else "invalid_nondecisive_terminal",
        "decisive_reason": reason,
        "terminal_cause": cause,
        "threshold_ply": threshold_ply,
        "plies": plies,
        "opening_plies": len(opening.actions),
        "scored_plies": plies - len(opening.actions),
        "scores": list(scores),
        "capture_points": captures,
        "check_points": checks,
        "total_points": sum(scores),
        "nodes": nodes_used,
        "elapsed_seconds": round(time.monotonic() - game_started, 6),
        "completed": completed,
        "inconclusive_reason": incomplete_reason,
        "valid": bool(valid and completed),
        "actions": actions,
    }


def run(*, output_dir: Path) -> dict:
    started = time.monotonic()
    deadline = started + MAX_WALL_SECONDS
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite diagnostic output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    bounds = {
        "max_games": MAX_GAMES,
        "games_started": 0,
        "max_concurrent_games": MAX_CONCURRENT_GAMES,
        "actual_concurrent_games": 1,
        "max_total_plies_per_game_including_opening": MAX_TOTAL_PLIES_PER_GAME,
        "max_total_plies_all_games": MAX_GAMES * MAX_TOTAL_PLIES_PER_GAME,
        "max_nodes_per_move": MAX_NODES_PER_MOVE,
        "max_total_nodes_all_games": MAX_TOTAL_NODES,
        "hard_wall_seconds": MAX_WALL_SECONDS,
        "internal_wall_reserve_seconds": 60,
        "max_game_seconds": MAX_GAME_SECONDS,
    }
    # Persist an inconclusive sentinel before compilation so an external Heavy
    # hard-stop never leaves an apparently successful or unclassified run.
    _atomic_json(output_dir / "result.json", {
        "schema": SCHEMA,
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "classification": "CAUSAL_DIAGNOSTIC_INCONCLUSIVE",
        "inconclusive_reason": "run_in_progress_or_external_wall_timeout",
        "strength_or_promotion_evidence": False,
        "bounds": bounds,
        "games": [],
    })
    compiled = race._compile()
    ordering_values = _ordering_values(compiled)
    gen0 = tuple(gen0_vector(GEN0_SEED))
    mutant = f153.mutation_vectors_at_sigma(gen0, SIGMA)[MUTANT_INDEX]
    opening_pool = race.opening_corpus(compiled, OPENING_SEED, OPENING_COUNT)
    if len(opening_pool) != 1:
        raise RuntimeError("diagnostic must use exactly one fresh opening")
    opening = opening_pool[0]
    if not race.OPENING_MIN_PLIES <= len(opening.actions) <= race.OPENING_MAX_PLIES:
        raise RuntimeError("fresh opening violates the 16–32 ply contract")
    if opening.final_position_key in HISTORICAL_OPENING_IDS:
        raise RuntimeError("fresh opening duplicates a previously used diagnostic opening")

    games = []
    for game_index, child_owner in enumerate(ROLE_ORDER):
        if time.monotonic() >= deadline:
            game = {
                "started": False, "child_owner": child_owner, "completed": False, "valid": False,
                "result": "inconclusive", "inconclusive_reason": "overall_wall_clock_cap",
                "elapsed_seconds": 0.0, "plies": len(opening.actions), "opening_plies": len(opening.actions),
                "scored_plies": 0, "nodes": 0, "scores": [0, 0], "actions": [],
            }
        else:
            game = play_capped_game(
                compiled, opening, gen0, mutant, child_owner, ordering_values,
                deadline=deadline, game_timeout=MAX_GAME_SECONDS,
            )
        game_row = {
            "game_index": game_index,
            "opening_id": opening.final_position_key,
            "opening_target_plies": opening.target_plies,
            "opening_actual_plies": len(opening.actions),
            **game,
        }
        games.append(game_row)
        bounds["games_started"] = sum(bool(row.get("started")) for row in games)
        # Each completed or timed-out game is durable before the next role is attempted.
        _atomic_json(output_dir / f"game-{game_index + 1}.json", game_row)
        _atomic_json(output_dir / "result.json", {
            "schema": SCHEMA,
            "diagnostic_type": "CAUSAL_DIAGNOSTIC",
            "classification": "CAUSAL_DIAGNOSTIC_INCONCLUSIVE",
            "inconclusive_reason": "pair_incomplete_or_external_wall_timeout",
            "strength_or_promotion_evidence": False,
            "bounds": bounds,
            "opening": {
                "seed": OPENING_SEED,
                "opening_id": opening.final_position_key,
                "target_plies": opening.target_plies,
                "actual_plies": len(opening.actions),
                "evaluator_neutral": True,
            },
            "mutant": {"generation": GENERATION, "index": MUTANT_INDEX, "sigma": SIGMA, **_vector_record(mutant)},
            "games": games,
        })
        if not game["completed"]:
            break

    valid_pair = len(games) == MAX_GAMES and all(game["valid"] for game in games)
    pair_scores = [
        1.0 if game["winner"] == game["child_owner"] else 0.0
        for game in games if game["valid"]
    ]
    pair_score = sum(pair_scores) / 2.0 if valid_pair else None
    if not valid_pair:
        classification = "CAUSAL_DIAGNOSTIC_INCONCLUSIVE"
    elif pair_score == 0.5:
        classification = "CAUSAL_DIAGNOSTIC_PAIR_TIED"
    else:
        classification = "CAUSAL_DIAGNOSTIC_NON_TIED_PAIR_SIGNAL"

    result = {
        "schema": SCHEMA,
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "classification": classification,
        "strength_or_promotion_evidence": False,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "type_ids": list(TYPE_IDS),
        "unknown": "whether one known-divergent sigma-.70 material mutant produces a short score-race signal, and actual per-game runtime",
        "bounds": bounds,
        "score_race": {
            "source": "F149 fixed score race",
            "threshold": race.SCORE_THRESHOLD,
            "capture_points": race.CAPTURE_POINTS,
            "check_points": race.CHECK_POINTS,
            "formal_core_winner_precedence": True,
            "safety_max_plies": MAX_TOTAL_PLIES_PER_GAME,
        },
        "opening": {
            "seed": OPENING_SEED,
            "count": 1,
            "opening_id": opening.final_position_key,
            "target_plies": opening.target_plies,
            "actual_plies": len(opening.actions),
            "evaluator_neutral": True,
            "fresh_identity_checked_against_prior_probes": True,
        },
        "mutant": {
            "generation": GENERATION,
            "index": MUTANT_INDEX,
            "sigma": SIGMA,
            **_vector_record(mutant),
            "prior_root_action_divergence": PRIOR_ROOT_DIVERGENCE,
        },
        "gen0": {"seed": GEN0_SEED, **_vector_record(gen0)},
        "search": {
            "max_nodes_per_move": MAX_NODES_PER_MOVE,
            "max_depth": 12,
            "qdepth": [4, 8],
            "tt_max_entries": race.TT_MAX_ENTRIES,
            "fixed_ordering_values": ordering_values,
            "fixed_ordering_sha256": _sha(ordering_values),
            "tuning": "SearchTuning()",
        },
        "games": games,
        "valid_pair": valid_pair,
        "pair_score": pair_score,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    }
    _atomic_json(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(output_dir=args.output_dir)
    print(json.dumps({"classification": result["classification"], "games": result["bounds"]["games_started"], "pair_score": result["pair_score"]}, sort_keys=True))
    return 0 if result["classification"] != "CAUSAL_DIAGNOSTIC_INCONCLUSIVE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
