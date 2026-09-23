"""Complete only the missing owner-1 game of the prescribed F153 fresh pair."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.session.result import SessionStatus
from scripts import f149_shogi_material_score_race_deep_openings as race
from scripts import f153_sigma070_mutant4_fresh_single_pair as fresh_pair
from scripts import f153_shogi_material_mutation_root_sensitivity as f153
from scripts import f158_shogi_sigma070_single_pair_diagnostic as bounded_game
from scripts.f144_shogi_material_only_arena_evolution import _ordering_values

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "dcf76a95fbe01b563330205646e7d9d2b9a7cfb4"
SCHEMA = "F153_SIGMA070_MUTANT4_COMPLETE_OWNER1_V1"
HISTORICAL_GAME_PATH = ROOT / ".generic_chess_flow/f153-mutant4-fresh-single-pair-output/game-owner-0.json"
HISTORICAL_GAME_SHA256 = "FD56F14A5C266944F2AC47D4C3E1EA8F1C45FA141AEE98A36542BC5D722F9057"
OPENING_ID = "7e04681975c54713539109e629d64d568aebf72547382db2f04faf53a920bda9"
OPENING_SEED = 1_590_101
OPENING_INDEX = 0
OPENING_PLIES = 21
MAX_GAMES_NEW = 1
MAX_CONCURRENT_GAMES = 1
MAX_TOTAL_PLIES = 128
MAX_SEARCHED_PLIES = MAX_TOTAL_PLIES - OPENING_PLIES
MAX_NODES_PER_MOVE = 1_000
MAX_NODES = MAX_SEARCHED_PLIES * MAX_NODES_PER_MOVE
MAX_GAME_SECONDS = 420
ROLE_OWNER = 1


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _load_owner0(path: Path = HISTORICAL_GAME_PATH) -> tuple[dict, dict]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest().upper()
    if digest != HISTORICAL_GAME_SHA256:
        raise AssertionError("saved owner-0 evidence SHA256 mismatch")
    game = json.loads(raw.decode("utf-8"))
    expected = {
        "child_owner": 0,
        "terminal_cause": "repetition",
        "scores": [0, 0],
        "plies": 49,
        "scored_plies": 28,
        "nodes": 28_000,
        "completed": True,
    }
    if any(game.get(key) != value for key, value in expected.items()):
        raise AssertionError("saved owner-0 evidence fields do not match the Chat order")
    if game.get("decisive_reason") != "invalid_equal_score_terminal" or game.get("valid") is not False:
        raise AssertionError("saved owner-0 record is not the expected pre-correction invalid tie")
    winner, reason, valid = race.resolve_terminal(
        SimpleNamespace(status=SessionStatus.REPETITION, winner=None), game["scores"]
    )
    if (winner, reason, valid) != (None, "score_draw", True):
        raise AssertionError("current score-race resolver does not validate the saved 0-0 draw")
    normalized = {
        "child_owner": 0,
        "winner": winner,
        "decisive_reason": reason,
        "valid": valid,
        "scores": list(game["scores"]),
        "mutant4_points": int(game["mutant4_points"]),
        "gen0_points": int(game["gen0_points"]),
        "child_game_score": race.v2.child_game_score({
            "child_owner": 0, "winner": winner, "decisive_reason": reason, "valid": valid,
        }),
        "terminal_cause": game["terminal_cause"],
        "plies": game["plies"],
        "searched_plies": game["scored_plies"],
        "nodes": game["nodes"],
        "source_sha256": digest,
        "search_replayed": False,
    }
    if normalized["child_game_score"] != 0.5:
        raise AssertionError("saved owner-0 draw did not map to a neutral child score")
    return game, normalized


def _first_scoring_event(game: dict, opening_plies: int) -> dict | None:
    for index, action in enumerate(game["actions"], start=1):
        if int(action["points"]) > 0:
            return {
                "scored_ply": index,
                "total_game_ply": opening_plies + index,
                "actor": action["actor"],
                "capture": action["capture"],
                "check": action["check"],
                "points": action["points"],
            }
    return None


def _classify(owner0: dict, owner1: dict) -> tuple[str, float | None]:
    score = race.v2.pair_score([owner0, owner1])
    if score is None:
        return "FRESH_PAIR_MUTANT4_INCONCLUSIVE", None
    if score > 0.5:
        return "FRESH_PAIR_MUTANT4_POSITIVE_SIGNAL", score
    if score < 0.5:
        return "FRESH_PAIR_MUTANT4_NEGATIVE_SIGNAL", score
    return "FRESH_PAIR_MUTANT4_TIED", score


def run(*, output_dir: Path) -> dict:
    started = time.monotonic()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(["git", "rev-parse", "origin/sandbox"], cwd=ROOT, text=True).strip()
    parent = subprocess.check_output(["git", "rev-parse", "HEAD^"], cwd=ROOT, text=True).strip()
    if head != remote or (head != BASE_SHA and parent != BASE_SHA):
        raise AssertionError("owner-1 run requires a published checkpoint based directly on its approved SHA")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite owner-1 output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    bounds = {
        "maximum_new_games": MAX_GAMES_NEW,
        "maximum_concurrent_games": MAX_CONCURRENT_GAMES,
        "maximum_total_plies_including_opening": MAX_TOTAL_PLIES,
        "opening_plies": OPENING_PLIES,
        "maximum_searched_plies": MAX_SEARCHED_PLIES,
        "maximum_nodes_per_move": MAX_NODES_PER_MOVE,
        "maximum_nodes": MAX_NODES,
        "maximum_game_wall_seconds": MAX_GAME_SECONDS,
    }
    _atomic_json(output_dir / "result.json", {
        "schema": SCHEMA, "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "classification": "FRESH_PAIR_MUTANT4_INCONCLUSIVE",
        "inconclusive_reason": "run_in_progress_or_external_timeout", "bounds": bounds,
        "new_games": [],
    })

    prior_raw, owner0 = _load_owner0()
    gen0, mutant4 = fresh_pair._vectors()
    compiled = race._compile()
    opening = fresh_pair._fresh_opening(compiled)
    if opening.index != OPENING_INDEX or len(opening.actions) != OPENING_PLIES:
        raise AssertionError("reconstructed opening does not match the prescribed identity/ply count")
    ordering = _ordering_values(compiled)
    deadline = started + MAX_GAME_SECONDS
    raw_game = bounded_game.play_capped_game(
        compiled, opening, gen0, mutant4, ROLE_OWNER, ordering,
        deadline=deadline, game_timeout=MAX_GAME_SECONDS,
    )
    game1 = {
        "opening_id": opening.final_position_key,
        "opening_seed": OPENING_SEED,
        "opening_index": OPENING_INDEX,
        "opening_plies": OPENING_PLIES,
        **raw_game,
        "mutant4_points": int(raw_game["scores"][ROLE_OWNER]),
        "gen0_points": int(raw_game["scores"][1 - ROLE_OWNER]),
        "capture_counts_by_side": raw_game["capture_points"],
        "check_counts_by_side": raw_game["check_points"],
        "first_scoring_event": _first_scoring_event(raw_game, OPENING_PLIES),
        "child_game_score": race.v2.child_game_score(raw_game),
    }
    _atomic_json(output_dir / "game-owner-1.json", game1)
    classification, pair_score = _classify(owner0, game1)
    mutant_total = owner0["mutant4_points"] + game1["mutant4_points"]
    gen0_total = owner0["gen0_points"] + game1["gen0_points"]
    owner0_delta = owner0["mutant4_points"] - owner0["gen0_points"]
    owner1_delta = game1["mutant4_points"] - game1["gen0_points"]
    result = {
        "schema": SCHEMA,
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "strength_or_promotion_evidence": False,
        "base_git_sha": BASE_SHA,
        "git_sha": head,
        "classification": classification,
        "opening": {"seed": OPENING_SEED, "index": OPENING_INDEX,
                    "opening_id": opening.final_position_key, "plies": OPENING_PLIES,
                    "reused_existing_opening": True, "another_opening_generated": False},
        "identity": {"gen0_values": list(gen0), "mutant4_values": list(mutant4),
                     "mutant4_sigma": 0.70, "mutant4_generation": 1, "mutant4_index": 4,
                     "mutant4_stage_vector_sha256": f153._sha(mutant4)},
        "owner0_historical_replay": owner0,
        "owner0_historical_game_sha256": hashlib.sha256(HISTORICAL_GAME_PATH.read_bytes()).hexdigest().upper(),
        "owner1_game": game1,
        "pair_score": pair_score,
        "mutant4_total_event_points": mutant_total,
        "gen0_total_event_points": gen0_total,
        "aggregate_event_point_differential": mutant_total - gen0_total,
        "per_role_event_point_differential": [
            {"child_owner": 0, "mutant4_minus_gen0": owner0_delta},
            {"child_owner": 1, "mutant4_minus_gen0": owner1_delta},
        ],
        "owner0_child_score": owner0["child_game_score"],
        "owner1_child_score": game1["child_game_score"],
        "threshold_10_reached_in_either_role": bool(
            prior_raw.get("threshold_ply") is not None or game1.get("threshold_ply") is not None
        ),
        "bounds": bounds,
        "elapsed_seconds": round(time.monotonic() - started, 6),
    }
    if game1["plies"] > MAX_TOTAL_PLIES or game1["scored_plies"] > MAX_SEARCHED_PLIES or game1["nodes"] > MAX_NODES:
        raise AssertionError("owner-1 game exceeded the approved resource bounds")
    _atomic_json(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(output_dir=args.output_dir)
    print(json.dumps({"classification": result["classification"],
                      "new_games": 1 if result["owner1_game"].get("started") else 0,
                      "pair_score": result["pair_score"],
                      "nodes": result["owner1_game"]["nodes"]}, sort_keys=True))
    return 0 if result["classification"] != "FRESH_PAIR_MUTANT4_INCONCLUSIVE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
