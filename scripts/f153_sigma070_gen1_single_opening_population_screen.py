"""One common fresh opening, role-swapped score-race pairs for six sigma-.70 mutants."""

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
BASE_SHA = "f864ebd74105c81a9a970b9b612e111684896e1a"
SCHEMA = "F153_SIGMA070_GEN1_SINGLE_OPENING_POPULATION_SCREEN_V1"
OPENING_SEED = 1_590_201
OPENING_COUNT = 1
OPENING_ID = "5af7d590672eb94fffc329ae6de806754e505e7f64be31d8470eb4799ca290a8"
OPENING_PLIES = 16
PREVIOUS_OPENING_IDS = {
    "5738e1f589b8096372ce9c369692937123c13a383f70ceb44ec4f6a19a9bfd2b",
    "742b4fc33ad8a8e9e57369f74b7544245622932fe16d99326f82a9163c1b801c",
    "5d4f445657c94a1d4a6ec5acc51ecdd0eaea001bdba8e7e81304d9277392dd6d",
    "7e04681975c54713539109e629d64d568aebf72547382db2f04faf53a920bda9",
}
EXPECTED_GEN0 = (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
EXPECTED_MUTANTS = (
    (357, 1387, 901, 7289, 200, 839, 5411, 716, 2785, 5058, 1423, 1000, 171),
    (278, 183, 298, 4495, 153, 935, 5721, 1528, 1000, 1023, 2247, 1905, 520),
    (331, 612, 484, 2265, 74, 1840, 4687, 538, 3038, 2435, 6153, 1000, 591),
    (226, 1000, 1635, 901, 152, 1141, 1859, 341, 2619, 1207, 1541, 725, 66),
    (690, 382, 387, 3636, 498, 1000, 6221, 1298, 3157, 312, 3031, 2508, 966),
    (307, 175, 798, 1526, 173, 1000, 4495, 321, 3281, 2754, 2718, 2292, 394),
)
EXPECTED_MUTANT_HASHES = (
    "dd8b5a0857c9b5a62fcb11bc95a6b91f7ada01cdc3592148d8f9b4a6fcf7da1e",
    "1511f7e07edeb9aec183b1d426e06242b0434da99588a43f309e37167eada08d",
    "815a996108039d5f557a4ebcd3c342862455dd47c952bd3e50dc043d18538cb6",
    "3a6c9304da363644bd24d89b2583c990d6b3f01e7a33a62d4281237b983e2edb",
    "3f015f6631460f6c2a71a8d80898cd7d781d02e9b605639c701408b420e654e9",
    "34412f0ec465578cdb3578fecf1e3381e893573e6807c8855a3d3ae41d29819c",
)
MUTANT_COUNT = 6
ROLE_ORDER = (0, 1)
MAX_GAMES = MUTANT_COUNT * len(ROLE_ORDER)
MAX_CONCURRENT_GAMES = 1
MAX_TOTAL_PLIES_PER_GAME = 128
MAX_SEARCHED_PLIES_PER_GAME = MAX_TOTAL_PLIES_PER_GAME - OPENING_PLIES
MAX_NODES_PER_MOVE = 1_000
MAX_NODES_PER_GAME = MAX_SEARCHED_PLIES_PER_GAME * MAX_NODES_PER_MOVE
MAX_TOTAL_NODES = MAX_GAMES * MAX_NODES_PER_GAME
MAX_GAME_SECONDS = 420
MAX_INTERNAL_SECONDS = MAX_GAMES * MAX_GAME_SECONDS
EXTERNAL_HARD_SECONDS = 90 * 60


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _vectors() -> tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]:
    gen0 = tuple(gen0_vector(GEN0_SEED))
    mutants = tuple(tuple(row) for row in f153.mutation_vectors_at_sigma(gen0, 0.70))
    if gen0 != EXPECTED_GEN0 or mutants != EXPECTED_MUTANTS:
        raise AssertionError("Gen0 or sigma-.70 generation-1 vector differs from the Chat order")
    actual_hashes = tuple(f153._sha(row) for row in mutants)
    if actual_hashes != EXPECTED_MUTANT_HASHES:
        raise AssertionError("F153 sequence-hash identities differ from the Chat order")
    return gen0, mutants


def _opening(compiled):
    openings = race.opening_corpus(compiled, OPENING_SEED, OPENING_COUNT)
    if len(openings) != 1:
        raise AssertionError("the prescribed seed/count did not yield exactly one opening")
    opening = openings[0]
    if not race.OPENING_MIN_PLIES <= len(opening.actions) <= race.OPENING_MAX_PLIES:
        raise AssertionError("the first opening is outside the existing 16-32 ply contract")
    if opening.final_position_key in PREVIOUS_OPENING_IDS:
        raise AssertionError("the first opening duplicates a previously used diagnostic root")
    if opening.index != 0 or opening.final_position_key != OPENING_ID or len(opening.actions) != OPENING_PLIES:
        raise AssertionError("the prescribed seed no longer yields the recorded first opening")
    return opening


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


def _pair_record(mutant_index: int, games: list[dict]) -> dict:
    score = race.v2.pair_score(games)
    points_by_role = [
        {"child_owner": game["child_owner"],
         "mutant_minus_gen0": game["mutant4_points"] - game["gen0_points"]}
        for game in games
    ]
    return {
        "mutant_index": mutant_index,
        "vector": list(EXPECTED_MUTANTS[mutant_index]),
        "vector_sha256": EXPECTED_MUTANT_HASHES[mutant_index],
        "valid": score is not None,
        "pair_score": score,
        "games": games,
        "mutant4_total_event_points": sum(g["mutant4_points"] for g in games),
        "gen0_total_event_points": sum(g["gen0_points"] for g in games),
        "aggregate_event_point_differential": sum(x["mutant_minus_gen0"] for x in points_by_role),
        "per_role_event_point_differential": points_by_role,
        "threshold_10_reached": any(g["threshold_ply"] is not None for g in games),
    }


def _game_end_category(game: dict) -> str:
    if game["terminal_cause"] == "max_plies":
        return "safety_cap"
    if game["decisive_reason"] == "score_draw":
        return "score_draw"
    if game["decisive_reason"] == "score_tiebreak":
        return "score_tiebreak"
    if game["decisive_reason"] == "score_threshold":
        return "threshold"
    if game["decisive_reason"] in {"checkmate", "perpetual_check", "declaration", "resignation"}:
        return "core_decisive"
    return "other_or_incomplete"


def _population_summary(pairs: list[dict]) -> dict:
    valid_pairs = [pair for pair in pairs if pair["valid"]]
    scores = [pair["pair_score"] for pair in valid_pairs]
    differentials = [pair["aggregate_event_point_differential"] for pair in valid_pairs]
    games = [game for pair in pairs for game in pair["games"]]
    if len(pairs) != MUTANT_COUNT or len(valid_pairs) != MUTANT_COUNT:
        classification = "SIGMA070_GEN1_FRESH_PAIR_SCREEN_INCONCLUSIVE"
    elif any(score != 0.5 for score in scores):
        classification = "SIGMA070_GEN1_FRESH_PAIR_DISCRIMINATION_FOUND"
    else:
        classification = "SIGMA070_GEN1_FRESH_PAIR_ALL_TIED"
    return {
        "classification": classification,
        "pair_score_counts": {
            "below_0_5": sum(score < 0.5 for score in scores),
            "exactly_0_5": sum(score == 0.5 for score in scores),
            "above_0_5": sum(score > 0.5 for score in scores),
        },
        "mutant_event_differential_counts": {
            "positive": sum(delta > 0 for delta in differentials),
            "zero": sum(delta == 0 for delta in differentials),
            "negative": sum(delta < 0 for delta in differentials),
        },
        "game_end_category_counts": {
            category: sum(_game_end_category(game) == category for game in games)
            for category in ("score_draw", "score_tiebreak", "threshold", "core_decisive", "safety_cap")
        },
        "total_capture_events": sum(sum(game["capture_points"]) for game in games),
        "total_check_events": sum(sum(game["check_points"]) for game in games),
        "total_nodes": sum(game["nodes"] for game in games),
        "games_completed_valid": sum(bool(game["completed"] and game["valid"]) for game in games),
        "games_attempted": len(games),
    }


def run(*, output_dir: Path) -> dict:
    started = time.monotonic()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(["git", "rev-parse", "origin/sandbox"], cwd=ROOT, text=True).strip()
    parent = subprocess.check_output(["git", "rev-parse", "HEAD^"], cwd=ROOT, text=True).strip()
    if head != remote or (head != BASE_SHA and parent != BASE_SHA):
        raise AssertionError("population screen requires a published checkpoint based on approved SHA")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite population-screen output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    bounds = {
        "maximum_mutants": MUTANT_COUNT,
        "maximum_pairs": MUTANT_COUNT,
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
        "schema": SCHEMA,
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "classification": "SIGMA070_GEN1_FRESH_PAIR_SCREEN_INCONCLUSIVE",
        "inconclusive_reason": "run_in_progress_or_external_timeout",
        "bounds": bounds,
        "pairs": [],
    })

    gen0, mutants = _vectors()
    compiled = race._compile()
    opening = _opening(compiled)
    if len(opening.actions) != OPENING_PLIES:
        raise AssertionError("opening ply count differs from the approved resource envelope")
    ordering = _ordering_values(compiled)
    deadline = started + MAX_INTERNAL_SECONDS
    pairs: list[dict] = []
    all_games: list[dict] = []
    stopped_early = None
    for mutant_index, mutant in enumerate(mutants):
        pair_games = []
        for owner in ROLE_ORDER:
            if time.monotonic() >= deadline:
                stopped_early = "internal_wall_clock_cap"
                break
            raw = bounded_game.play_capped_game(
                compiled, opening, gen0, mutant, owner, ordering,
                deadline=deadline, game_timeout=MAX_GAME_SECONDS,
            )
            game = {
                "mutant_index": mutant_index,
                "child_owner": owner,
                "opening_id": opening.final_position_key,
                "opening_plies": OPENING_PLIES,
                **raw,
                "mutant4_points": int(raw["scores"][owner]),
                "gen0_points": int(raw["scores"][1 - owner]),
                "first_scoring_event": _first_scoring_event(raw, OPENING_PLIES),
                "child_game_score": race.v2.child_game_score(raw),
                "end_category": _game_end_category(raw),
            }
            if game["plies"] > MAX_TOTAL_PLIES_PER_GAME or game["scored_plies"] > MAX_SEARCHED_PLIES_PER_GAME or game["nodes"] > MAX_NODES_PER_GAME:
                raise AssertionError("observed game exceeded its approved static resource bound")
            pair_games.append(game)
            all_games.append(game)
            _atomic_json(output_dir / f"mutant-{mutant_index}-owner-{owner}.json", game)
            if not game["completed"] or not game["valid"]:
                stopped_early = f"mutant_{mutant_index}_owner_{owner}_incomplete_or_invalid"
                break
        pair = _pair_record(mutant_index, pair_games)
        pairs.append(pair)
        _atomic_json(output_dir / f"mutant-{mutant_index}-pair.json", pair)
        _atomic_json(output_dir / "result.json", {
            "schema": SCHEMA,
            "diagnostic_type": "CAUSAL_DIAGNOSTIC",
            "classification": "SIGMA070_GEN1_FRESH_PAIR_SCREEN_INCONCLUSIVE",
            "inconclusive_reason": stopped_early or "screen_in_progress",
            "base_git_sha": BASE_SHA,
            "git_sha": head,
            "opening": {"seed": OPENING_SEED, "count": OPENING_COUNT,
                        "opening_id": opening.final_position_key,
                        "target_plies": opening.target_plies,
                        "plies": len(opening.actions), "evaluator_neutral": True},
            "vectors": [{"mutant_index": index, "values": list(vector),
                         "sequence_sha256": EXPECTED_MUTANT_HASHES[index]}
                        for index, vector in enumerate(mutants)],
            "bounds": bounds,
            "pairs": pairs,
            "population": _population_summary(pairs),
        })
        if stopped_early:
            break

    summary = _population_summary(pairs)
    result = {
        "schema": SCHEMA,
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "strength_or_promotion_evidence": False,
        "base_git_sha": BASE_SHA,
        "git_sha": head,
        "opening": {"seed": OPENING_SEED, "count": OPENING_COUNT,
                    "opening_id": opening.final_position_key,
                    "target_plies": opening.target_plies,
                    "plies": len(opening.actions), "evaluator_neutral": True,
                    "first_generated_opening_used_unconditionally": True},
        "gen0_values": list(gen0),
        "vectors": [{"mutant_index": index, "values": list(vector),
                     "sequence_sha256": EXPECTED_MUTANT_HASHES[index]}
                    for index, vector in enumerate(mutants)],
        "score_race": {"capture_points": race.CAPTURE_POINTS,
                       "check_points": race.CHECK_POINTS,
                       "threshold": race.SCORE_THRESHOLD,
                       "formal_core_decisive_precedence": True,
                       "equal_score_terminal": "valid score_draw",
                       "child_game_score": {"win": 1.0, "draw": 0.5, "loss": 0.0}},
        "search": {"material_only": True, "fixed_ordering_values": ordering,
                   "nodes_per_move": MAX_NODES_PER_MOVE, "max_depth": 12,
                   "qdepth": [4, 8], "tt_entries": race.TT_MAX_ENTRIES,
                   "tuning": "SearchTuning()", "fresh_player_and_tt_per_game": True},
        "bounds": bounds,
        "pairs": pairs,
        "incomplete_reason": stopped_early or (
            "one_or_more_pairs_incomplete_or_invalid"
            if summary["classification"] == "SIGMA070_GEN1_FRESH_PAIR_SCREEN_INCONCLUSIVE"
            else None
        ),
        **summary,
        "elapsed_seconds": round(time.monotonic() - started, 6),
    }
    total_nodes = sum(game["nodes"] for game in all_games)
    if total_nodes > MAX_TOTAL_NODES or len(all_games) > MAX_GAMES:
        raise AssertionError("screen exceeded its approved global resource bounds")
    _atomic_json(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(output_dir=args.output_dir)
    print(json.dumps({"classification": result["classification"],
                      "pairs": len(result["pairs"]),
                      "games": result["games_attempted"],
                      "total_nodes": result["total_nodes"]}, sort_keys=True))
    return 0 if result["classification"] != "SIGMA070_GEN1_FRESH_PAIR_SCREEN_INCONCLUSIVE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
