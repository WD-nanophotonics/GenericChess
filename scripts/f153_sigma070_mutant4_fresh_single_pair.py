"""One fresh, evaluator-neutral role-swapped F149 score-race pair."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import f149_shogi_material_score_race_deep_openings as race
from scripts import f153_shogi_material_mutation_root_sensitivity as f153
from scripts import f158_shogi_sigma070_single_pair_diagnostic as bounded_game
from scripts.f144_shogi_material_only_arena_evolution import (
    GEN0_SEED, _ordering_values, _vector_record, gen0_vector,
)

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "c4da9bdf3bd2b739b08a270ccc842dde289a4a0e"
SCHEMA = "F153_SIGMA070_MUTANT4_FRESH_SINGLE_PAIR_V1"
OPENING_SEED = 1_590_101
OPENING_COUNT = 1
EXPECTED_OPENING_ID = "7e04681975c54713539109e629d64d568aebf72547382db2f04faf53a920bda9"
HISTORICAL_OPENING_IDS = {
    "5738e1f589b8096372ce9c369692937123c13a383f70ceb44ec4f6a19a9bfd2b",
    "742b4fc33ad8a8e9e57369f74b7544245622932fe16d99326f82a9163c1b801c",
    "5d4f445657c94a1d4a6ec5acc51ecdd0eaea001bdba8e7e81304d9277392dd6d",
}
EXPECTED_GEN0 = (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
EXPECTED_MUTANT4 = (690, 382, 387, 3636, 498, 1000, 6221, 1298, 3157, 312, 3031, 2508, 966)
EXPECTED_MUTANT4_SHA = "3f015f6631460f6c2a71a8d80898cd7d781d02e9b605639c701408b420e654e9"
ROLE_ORDER = (0, 1)
MAX_GAMES = 2
MAX_CONCURRENT_GAMES = 1
MAX_NODES_PER_MOVE = 1_000
MAX_TOTAL_PLIES_PER_GAME = 128
OPENING_PLIES = 21
MAX_SEARCHED_PLIES_PER_GAME = MAX_TOTAL_PLIES_PER_GAME - OPENING_PLIES
MAX_NODES_PER_GAME = MAX_SEARCHED_PLIES_PER_GAME * MAX_NODES_PER_MOVE
MAX_TOTAL_NODES = MAX_GAMES * MAX_NODES_PER_GAME
MAX_GAME_SECONDS = 420
MAX_INTERNAL_SECONDS = 840
EXTERNAL_HARD_SECONDS = 900


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _vectors() -> tuple[tuple[int, ...], tuple[int, ...]]:
    gen0 = tuple(gen0_vector(GEN0_SEED))
    mutant4 = tuple(f153.mutation_vectors_at_sigma(gen0, 0.70)[4])
    if gen0 != EXPECTED_GEN0 or mutant4 != EXPECTED_MUTANT4:
        raise AssertionError("Gen0 or sigma-.70 mutant_4 vector differs from the Chat order")
    if f153._sha(mutant4) != EXPECTED_MUTANT4_SHA:
        raise AssertionError("sigma-.70 mutant_4 stage-vector hash mismatch")
    return gen0, mutant4


def _fresh_opening(compiled):
    openings = race.opening_corpus(compiled, OPENING_SEED, OPENING_COUNT)
    if len(openings) != 1:
        raise AssertionError("the prescribed seed/count did not yield exactly one opening")
    opening = openings[0]
    if not race.OPENING_MIN_PLIES <= len(opening.actions) <= race.OPENING_MAX_PLIES:
        raise AssertionError("the first generated opening violates the 16-32 ply contract")
    if opening.final_position_key in HISTORICAL_OPENING_IDS:
        raise AssertionError("the first generated opening duplicates a prior diagnostic root")
    if opening.final_position_key != EXPECTED_OPENING_ID:
        raise AssertionError("the prescribed seed no longer generates the recorded first opening")
    return opening


def _classify(games: list[dict]) -> tuple[str, float | None]:
    if len(games) != MAX_GAMES or any(not g.get("completed") or not g.get("valid") for g in games):
        return "FRESH_PAIR_MUTANT4_INCONCLUSIVE", None
    pair_score = sum(1.0 if g["winner"] == g["child_owner"] else 0.0 for g in games) / MAX_GAMES
    if pair_score > 0.5:
        return "FRESH_PAIR_MUTANT4_POSITIVE_SIGNAL", pair_score
    if pair_score < 0.5:
        return "FRESH_PAIR_MUTANT4_NEGATIVE_SIGNAL", pair_score
    return "FRESH_PAIR_MUTANT4_TIED_OR_CANCELLED", pair_score


def run(*, output_dir: Path) -> dict:
    started = time.monotonic()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(["git", "rev-parse", "origin/sandbox"], cwd=ROOT, text=True).strip()
    parent = subprocess.check_output(["git", "rev-parse", "HEAD^"], cwd=ROOT, text=True).strip()
    if head != remote or (head != BASE_SHA and parent != BASE_SHA):
        raise AssertionError("run requires a published checkpoint directly based on the approved SHA")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite fresh-pair output: {output_dir}")
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
        "maximum_internal_wall_seconds": MAX_INTERNAL_SECONDS,
        "external_hard_wall_seconds": EXTERNAL_HARD_SECONDS,
    }
    _atomic_json(output_dir / "result.json", {
        "schema": SCHEMA, "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "classification": "FRESH_PAIR_MUTANT4_INCONCLUSIVE",
        "inconclusive_reason": "run_in_progress_or_external_timeout", "bounds": bounds, "games": [],
    })

    gen0, mutant4 = _vectors()
    compiled = race._compile()
    opening = _fresh_opening(compiled)
    if len(opening.actions) != OPENING_PLIES:
        raise AssertionError("opening ply count differs from the approved exact resource bound")
    ordering = _ordering_values(compiled)
    deadline = started + MAX_INTERNAL_SECONDS
    games = []
    for game_index, owner in enumerate(ROLE_ORDER):
        if time.monotonic() >= deadline:
            break
        raw = bounded_game.play_capped_game(
            compiled, opening, gen0, mutant4, owner, ordering,
            deadline=deadline, game_timeout=MAX_GAME_SECONDS,
        )
        row = {
            "game_index": game_index,
            "opening_id": opening.final_position_key,
            "opening_target_plies": opening.target_plies,
            "opening_plies": len(opening.actions),
            **raw,
            "mutant4_points": raw["scores"][owner],
            "gen0_points": raw["scores"][1 - owner],
            "capture_counts_by_side": raw["capture_points"],
            "check_counts_by_side": raw["check_points"],
        }
        games.append(row)
        _atomic_json(output_dir / f"game-owner-{owner}.json", row)
        _atomic_json(output_dir / "result.json", {
            "schema": SCHEMA, "diagnostic_type": "CAUSAL_DIAGNOSTIC",
            "classification": "FRESH_PAIR_MUTANT4_INCONCLUSIVE",
            "inconclusive_reason": "pair_incomplete_or_second_role_pending",
            "bounds": bounds,
            "opening": {"seed": OPENING_SEED, "count": OPENING_COUNT,
                        "opening_id": opening.final_position_key,
                        "target_plies": opening.target_plies,
                        "actual_plies": len(opening.actions), "evaluator_neutral": True},
            "games": games,
        })
        if not row["completed"] or not row["valid"]:
            break

    classification, pair_score = _classify(games)
    valid_pair = pair_score is not None
    mutant_total = sum(g["mutant4_points"] for g in games)
    gen0_total = sum(g["gen0_points"] for g in games)
    role_deltas = [g["mutant4_points"] - g["gen0_points"] for g in games]
    if len(role_deltas) == 2 and role_deltas[0] * role_deltas[1] > 0:
        role_direction = "agree"
    elif len(role_deltas) == 2 and role_deltas[0] * role_deltas[1] < 0:
        role_direction = "oppose"
    else:
        role_direction = "cancel_or_zero"
    result = {
        "schema": SCHEMA,
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "strength_or_promotion_evidence": False,
        "base_git_sha": BASE_SHA,
        "git_sha": head,
        "unknown": "whether sigma-.70 generation-1 mutant_4 has positive pair-level score-race fitness on one unselected fresh opening",
        "classification": classification,
        "opening": {"seed": OPENING_SEED, "count": OPENING_COUNT,
                    "opening_id": opening.final_position_key,
                    "target_plies": opening.target_plies,
                    "actual_plies": len(opening.actions), "evaluator_neutral": True,
                    "different_from_recorded_prior_openings": True},
        "gen0_values": list(gen0),
        "mutant4_values": list(mutant4),
        "mutant4_stage_vector_sha256": f153._sha(mutant4),
        "mutant_sigma": 0.70,
        "mutant_generation": 1,
        "mutant_index": 4,
        "score_race": {"capture_points": race.CAPTURE_POINTS,
                       "check_points": race.CHECK_POINTS,
                       "threshold": race.SCORE_THRESHOLD,
                       "formal_core_decisive_precedence": True},
        "search": {"nodes_per_move": MAX_NODES_PER_MOVE, "max_depth": 12,
                   "qdepth": [4, 8], "tt_entries": race.TT_MAX_ENTRIES,
                   "fixed_ordering_values": ordering, "tuning": "SearchTuning()",
                   "fresh_player_and_tt_state_each_game": True},
        "bounds": bounds,
        "games": games,
        "valid_pair": valid_pair,
        "pair_score": pair_score,
        "mutant4_total_points": mutant_total,
        "gen0_total_points": gen0_total,
        "aggregate_mutant_point_differential": mutant_total - gen0_total,
        "per_role_point_differentials": [
            {"child_owner": g["child_owner"], "mutant4_minus_gen0": g["mutant4_points"] - g["gen0_points"]}
            for g in games
        ],
        "role_directions": role_direction,
        "threshold_10_reached_by_either_game": any(g["threshold_ply"] is not None for g in games),
        "elapsed_seconds": round(time.monotonic() - started, 6),
    }
    if sum(g["nodes"] for g in games) > MAX_TOTAL_NODES or any(
        g["plies"] > MAX_TOTAL_PLIES_PER_GAME or g["nodes"] > MAX_NODES_PER_GAME
        or g["scored_plies"] > MAX_SEARCHED_PLIES_PER_GAME for g in games
    ):
        raise AssertionError("observed pair exceeded its approved resource envelope")
    _atomic_json(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(output_dir=args.output_dir)
    print(json.dumps({"classification": result["classification"],
                      "games": len(result["games"]), "pair_score": result["pair_score"],
                      "total_nodes": sum(g["nodes"] for g in result["games"])}, sort_keys=True))
    return 0 if result["classification"] != "FRESH_PAIR_MUTANT4_INCONCLUSIVE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
