"""Bounded second-opening score-race screen for the four Gen1 leaders."""

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

from scripts import f149_shogi_material_score_race_deep_openings as race
from scripts import f153_shogi_material_mutation_root_sensitivity as f153
from scripts import f153_sigma070_gen1_single_opening_population_screen as first_screen
from scripts import f158_shogi_sigma070_single_pair_diagnostic as bounded_game
from scripts.f144_shogi_material_only_arena_evolution import (
    GEN0_SEED, _ordering_values, gen0_vector,
)

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "5d6789e52431679a5e1c543f0f4e0efa85efd33d"
FIRST_SCREEN_SHA = BASE_SHA
FIRST_SCREEN_RESULT_SHA256 = "7612E6EAF440051126F1B21FA63227AFA8688189AFBFC1C431EBFF1EB6DBFD1B"
SCHEMA = "F153_SIGMA070_GEN1_SECOND_OPENING_CANDIDATE_SCREEN_V1"
OPENING_SEED = 1_590_301
OPENING_COUNT = 1
OPENING_ID = "7a426930f39a4c1d267dbbf3bb861ffa91c3fad3e7c9d1ff1e9698913a2a46ef"
OPENING_PLIES = 23
PREVIOUS_OPENING_IDS = first_screen.PREVIOUS_OPENING_IDS | {
    first_screen.OPENING_ID,
}
GEN0_VALUES = (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
CANDIDATE_INDICES = (0, 1, 4, 5)
FIRST_PAIR_SCORES = {0: 0.75, 1: 0.75, 4: 0.75, 5: 0.75}
ROLE_ORDER = (0, 1)
MAX_PAIRS = len(CANDIDATE_INDICES)
MAX_GAMES = MAX_PAIRS * len(ROLE_ORDER)
MAX_CONCURRENT_GAMES = 1
MAX_TOTAL_PLIES_PER_GAME = 128
MAX_NODES_PER_MOVE = 1_000
MAX_GAME_SECONDS = 420
MAX_INTERNAL_SECONDS = MAX_GAMES * MAX_GAME_SECONDS
EXTERNAL_HARD_SECONDS = 3_600
MAX_DEPTH = 12
QDEPTH = (4, 8)
TT_ENTRIES = 250_000


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _vectors() -> tuple[tuple[int, ...], dict[int, tuple[int, ...]]]:
    gen0 = tuple(gen0_vector(GEN0_SEED))
    if gen0 != GEN0_VALUES:
        raise AssertionError("Gen0 differs from the Chat order")
    all_mutants = tuple(tuple(row) for row in f153.mutation_vectors_at_sigma(gen0, 0.70))
    if all_mutants != first_screen.EXPECTED_MUTANTS:
        raise AssertionError("sigma-.70 Gen1 vectors differ from the first screen")
    selected = {index: all_mutants[index] for index in CANDIDATE_INDICES}
    for index, vector in selected.items():
        if f153._sha(vector) != first_screen.EXPECTED_MUTANT_HASHES[index]:
            raise AssertionError(f"mutant {index} sequence hash differs from the Chat order")
    return gen0, selected


def _verify_first_screen(result: dict) -> None:
    if result.get("git_sha") != FIRST_SCREEN_SHA:
        raise AssertionError("first-opening evidence has the wrong published source SHA")
    opening = result.get("opening", {})
    if (opening.get("seed"), opening.get("opening_id")) != (
        first_screen.OPENING_SEED, first_screen.OPENING_ID,
    ):
        raise AssertionError("first-opening evidence does not match the pinned screen")
    if result.get("games_attempted") != 12 or result.get("games_completed_valid") != 12:
        raise AssertionError("first-opening evidence is not a complete valid 12-game screen")
    if len(result.get("pairs", [])) != 6:
        raise AssertionError("first-opening evidence does not contain all six pairs")
    scores = {
        int(pair["mutant_index"]): pair["pair_score"]
        for pair in result.get("pairs", [])
        if pair.get("valid") is True
    }
    expected_scores = {0: 0.75, 1: 0.75, 2: 0.5, 3: 0.5, 4: 0.75, 5: 0.75}
    if scores != expected_scores:
        raise AssertionError("first-opening pair scores differ from the pinned Chat evidence")
    if not set(CANDIDATE_INDICES).issubset(scores) or any(
        scores[index] != FIRST_PAIR_SCORES[index] for index in CANDIDATE_INDICES
    ):
        raise AssertionError("a second-opening candidate is not a first-opening leader")


def _decode_first_screen(source_bytes: bytes) -> tuple[dict, str]:
    source_sha = hashlib.sha256(source_bytes).hexdigest().upper()
    if source_sha != FIRST_SCREEN_RESULT_SHA256:
        raise AssertionError("first-opening result bytes differ from the pinned evidence digest")
    return json.loads(source_bytes.decode("utf-8")), source_sha


def resource_envelope(opening_plies: int = OPENING_PLIES,
                      opening_id: str = OPENING_ID) -> dict:
    if not race.OPENING_MIN_PLIES <= opening_plies <= race.OPENING_MAX_PLIES:
        raise AssertionError("opening is outside F149's 16-32 ply contract")
    searched_plies = MAX_TOTAL_PLIES_PER_GAME - opening_plies
    nodes_per_game = searched_plies * MAX_NODES_PER_MOVE
    return {
        "schema": "generic-chess-resource-envelope-v1",
        "envelope_id": "f153-sigma070-gen1-second-opening-candidate-v1",
        "logical_cpu_count": 2,
        "intended_cpu_lanes": 1,
        "expected_wall_minutes": None,
        "hard_wall_minutes": EXTERNAL_HARD_SECONDS // 60,
        "expected_cpu_hours": None,
        "hard_cpu_hours": 1,
        "arena_pairs": MAX_PAIRS,
        "maximum_games": MAX_GAMES,
        "maximum_nodes": MAX_GAMES * nodes_per_game,
        "maximum_plies": MAX_GAMES * MAX_TOTAL_PLIES_PER_GAME,
        "maximum_concurrent_games": MAX_CONCURRENT_GAMES,
        "stage_count": 1,
        "nodes_per_move": MAX_NODES_PER_MOVE,
        "max_depth": MAX_DEPTH,
        "qdepth": list(QDEPTH),
        "tt_entries": TT_ENTRIES,
        "opening_seed": OPENING_SEED,
        "opening_count": OPENING_COUNT,
        "opening_id": opening_id,
        "opening_plies": opening_plies,
        "maximum_total_plies_per_game_including_opening": MAX_TOTAL_PLIES_PER_GAME,
        "maximum_searched_plies_per_game": searched_plies,
        "maximum_nodes_per_game": nodes_per_game,
        "maximum_game_wall_seconds": MAX_GAME_SECONDS,
        "maximum_internal_wall_seconds": MAX_INTERNAL_SECONDS,
        "external_hard_wall_seconds": EXTERNAL_HARD_SECONDS,
        "purpose": (
            "Exactly one role-swapped pair for each first-opening leader mutant "
            "0,1,4,5 on one fresh evaluator-neutral opening; no replacement opening, "
            "replay, Gen2, promotion, or full-game strength claim"
        ),
    }


def _opening(compiled):
    openings = race.opening_corpus(compiled, OPENING_SEED, OPENING_COUNT)
    if len(openings) != OPENING_COUNT:
        raise AssertionError("seed/count did not yield exactly one opening")
    opening = openings[0]
    if not race.OPENING_MIN_PLIES <= len(opening.actions) <= race.OPENING_MAX_PLIES:
        raise AssertionError("opening violates F149's 16-32 ply contract")
    if opening.final_position_key in PREVIOUS_OPENING_IDS:
        raise AssertionError("opening duplicates a previously used diagnostic root")
    if (opening.index != 0 or opening.final_position_key != OPENING_ID
            or len(opening.actions) != OPENING_PLIES):
        raise AssertionError("seed no longer yields the pinned first valid opening")
    return opening


def _run_metadata(opening, ordering: dict[str, int]) -> dict:
    _, mutants = _vectors()
    return {
        "opening": {
            "seed": OPENING_SEED,
            "count": OPENING_COUNT,
            "opening_id": opening.final_position_key,
            "opening_seed": opening.opening_seed,
            "index": opening.index,
            "target_plies": opening.target_plies,
            "plies": len(opening.actions),
            "evaluator_neutral": True,
            "first_generated_opening_used_unconditionally": True,
            "actions": [race.v2.action_to_dict(action) for action in opening.actions],
        },
        "gen0_values": list(GEN0_VALUES),
        "vectors": [
            {"mutant_index": index, "values": list(vector),
             "sequence_sha256": first_screen.EXPECTED_MUTANT_HASHES[index],
             "first_opening_pair_score": FIRST_PAIR_SCORES[index]}
            for index, vector in mutants.items()
        ],
        "score_race": {
            "capture_points": race.CAPTURE_POINTS,
            "check_points": race.CHECK_POINTS,
            "capture_plus_check_points": 2,
            "threshold": race.SCORE_THRESHOLD,
            "formal_core_decisive_precedence": True,
            "unequal_nondecisive_terminal": "score_tiebreak",
            "equal_nondecisive_terminal": "valid score_draw",
            "child_game_score": {"win": 1.0, "draw": 0.5, "loss": 0.0},
            "pair_score": "mean of the two distinct-role child-game scores",
        },
        "search": {
            "material_only": True,
            "fixed_ordering_values": ordering,
            "nodes_per_move": MAX_NODES_PER_MOVE,
            "max_depth": MAX_DEPTH,
            "qdepth": list(QDEPTH),
            "tt_entries": TT_ENTRIES,
            "tuning": "SearchTuning()",
            "fresh_player_and_tt_per_game": True,
        },
        "strength_or_promotion_evidence": False,
    }


def _pair_record(mutant_index: int, games: list[dict]) -> dict:
    owners = {game.get("child_owner") for game in games}
    if len(games) != 2 or owners != {0, 1}:
        score = None
    else:
        score = race.v2.pair_score(games)
    differentials = [
        {"child_owner": game["child_owner"],
         "mutant_minus_gen0": game["mutant_points"] - game["gen0_points"]}
        for game in games
    ]
    return {
        "mutant_index": mutant_index,
        "vector": list(first_screen.EXPECTED_MUTANTS[mutant_index]),
        "vector_sha256": first_screen.EXPECTED_MUTANT_HASHES[mutant_index],
        "valid": score is not None and all(g.get("valid") and g.get("completed") for g in games),
        "pair_score": score,
        "games": games,
        "aggregate_event_point_differential": sum(x["mutant_minus_gen0"] for x in differentials),
        "per_role_event_point_differential": differentials,
        "threshold_10_reached": any(g.get("threshold_ply") is not None for g in games),
    }


def _rank_candidates(pairs: list[dict]) -> list[dict]:
    ranked = []
    for pair in pairs:
        if not pair.get("valid") or pair.get("pair_score") is None:
            continue
        index = int(pair["mutant_index"])
        first = FIRST_PAIR_SCORES[index]
        second = float(pair["pair_score"])
        mean = (first + second) / 2.0
        eligible = second > 0.5 and mean > 0.5
        ranked.append({
            "mutant_index": index,
            "first_opening_pair_score": first,
            "second_opening_pair_score": second,
            "two_opening_mean_pair_score": mean,
            "openings_above_0_5": int(first > 0.5) + int(second > 0.5),
            "eligible": eligible,
            "vector": list(first_screen.EXPECTED_MUTANTS[index]),
            "sequence_sha256": first_screen.EXPECTED_MUTANT_HASHES[index],
        })
    return sorted(
        ranked,
        key=lambda row: (
            -row["two_opening_mean_pair_score"],
            -row["openings_above_0_5"],
            row["mutant_index"],
        ),
    )


def _result_classification(pairs: list[dict]) -> tuple[str, dict | None]:
    if len(pairs) != MAX_PAIRS or any(not pair.get("valid") for pair in pairs):
        return "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE", None
    ranked = _rank_candidates(pairs)
    eligible = [row for row in ranked if row["eligible"]]
    if not eligible:
        return "SIGMA070_GEN1_SECOND_OPENING_NO_POSITIVE_CANDIDATE", None
    return "SIGMA070_GEN1_SECOND_OPENING_CANDIDATE_SELECTED", eligible[0]


def _resource_bound_violations(game: dict, envelope: dict) -> list[dict]:
    checks = (
        ("plies", "maximum_total_plies_per_game_including_opening"),
        ("scored_plies", "maximum_searched_plies_per_game"),
        ("nodes", "maximum_nodes_per_game"),
        ("elapsed_seconds", "maximum_game_wall_seconds"),
    )
    violations = []
    for metric, limit_key in checks:
        observed = game[metric]
        limit = envelope[limit_key]
        if observed > limit:
            violations.append({
                "metric": metric,
                "observed": observed,
                "approved_limit": limit,
            })
    return violations


def _game_stop_reason(game: dict, violations: list[dict]) -> str | None:
    prefix = f"mutant_{game['mutant_index']}_owner_{game['child_owner']}"
    if violations:
        if game.get("inconclusive_reason") == "wall_clock_cap":
            suffix = "_".join(item["metric"] for item in violations)
            return f"{prefix}_wall_clock_cap_resource_bound_{suffix}"
        suffix = "_".join(item["metric"] for item in violations)
        return f"{prefix}_resource_envelope_violation_{suffix}"
    if not game.get("completed") or not game.get("valid"):
        cause = game.get("inconclusive_reason") or "incomplete_or_invalid"
        return f"{prefix}_{cause}"
    return None


def run(*, output_dir: Path) -> dict:
    started = time.monotonic()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(["git", "rev-parse", "origin/sandbox"], cwd=ROOT, text=True).strip()
    parent = subprocess.check_output(["git", "rev-parse", "HEAD^"], cwd=ROOT, text=True).strip()
    if head != remote or (head != BASE_SHA and parent != BASE_SHA):
        raise AssertionError("candidate screen requires a published checkpoint based on the Chat SHA")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite candidate-screen output: {output_dir}")
    source_path = ROOT / ".generic_chess_flow/f153-sigma070-gen1-single-opening-population-output/result.json"
    source_bytes = source_path.read_bytes()
    source, source_sha = _decode_first_screen(source_bytes)
    _verify_first_screen(source)
    output_dir.mkdir(parents=True, exist_ok=True)

    compiled = race._compile()
    gen0, mutants = _vectors()
    opening = _opening(compiled)
    envelope = resource_envelope(len(opening.actions), opening.final_position_key)
    ordering = _ordering_values(compiled)
    metadata = _run_metadata(opening, ordering)
    deadline = started + MAX_INTERNAL_SECONDS
    pairs: list[dict] = []
    stop_reason = None
    _atomic_json(output_dir / "resource-envelope.json", envelope)
    _atomic_json(output_dir / "result.json", {
        "schema": SCHEMA,
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "classification": "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE",
        "incomplete_reason": "run_in_progress_or_external_timeout",
        "base_git_sha": BASE_SHA,
        "git_sha": head,
        **metadata,
        "resource_envelope": envelope,
        "first_screen_source_sha": source["git_sha"],
        "first_screen_result_sha256": source_sha,
        "first_screen_pair_scores": {str(k): v for k, v in FIRST_PAIR_SCORES.items()},
        "candidate_eligibility": "second_opening_pair_score > 0.5 and two_opening_mean_pair_score > 0.5",
        "candidate_indices": list(CANDIDATE_INDICES),
        "pairs": [],
    })

    for mutant_index in CANDIDATE_INDICES:
        role_games = []
        mutant = mutants[mutant_index]
        for owner in ROLE_ORDER:
            if time.monotonic() >= deadline:
                stop_reason = "internal_wall_clock_cap"
                break
            raw = bounded_game.play_capped_game(
                compiled, opening, gen0, mutant, owner, ordering,
                deadline=deadline, game_timeout=MAX_GAME_SECONDS,
            )
            game = {
                "mutant_index": mutant_index,
                "child_owner": owner,
                "opening_id": opening.final_position_key,
                "opening_plies": len(opening.actions),
                **raw,
                "mutant_points": int(raw["scores"][owner]),
                "gen0_points": int(raw["scores"][1 - owner]),
                "mutant_capture_events": int(raw["capture_points"][owner]),
                "gen0_capture_events": int(raw["capture_points"][1 - owner]),
                "mutant_check_events": int(raw["check_points"][owner]),
                "gen0_check_events": int(raw["check_points"][1 - owner]),
                "child_game_score": race.v2.child_game_score(raw),
                "end_category": first_screen._game_end_category(raw),
            }
            violations = _resource_bound_violations(game, envelope)
            game["resource_envelope_compliant"] = not violations
            game["resource_bound_violations"] = violations
            if violations:
                game["valid"] = False
                game["child_game_score"] = None
            _atomic_json(output_dir / f"mutant-{mutant_index}-owner-{owner}.json", game)
            role_games.append(game)
            stop_reason = _game_stop_reason(game, violations)
            if stop_reason:
                break
        pair = _pair_record(mutant_index, role_games)
        pairs.append(pair)
        _atomic_json(output_dir / f"mutant-{mutant_index}-pair.json", pair)
        if stop_reason:
            break
        _atomic_json(output_dir / "result.json", {
            "schema": SCHEMA,
            "diagnostic_type": "CAUSAL_DIAGNOSTIC",
            "classification": "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE",
            "incomplete_reason": "screen_in_progress",
            "base_git_sha": BASE_SHA,
            "git_sha": head,
            **metadata,
            "resource_envelope": envelope,
            "first_screen_source_sha": source["git_sha"],
            "first_screen_result_sha256": source_sha,
            "first_screen_pair_scores": {str(k): v for k, v in FIRST_PAIR_SCORES.items()},
            "candidate_eligibility": "second_opening_pair_score > 0.5 and two_opening_mean_pair_score > 0.5",
            "candidate_indices": list(CANDIDATE_INDICES),
            "pairs": pairs,
        })

    classification, candidate = _result_classification(pairs)
    games = [game for pair in pairs for game in pair["games"]]
    total_nodes = sum(game["nodes"] for game in games)
    global_violations = []
    if len(games) > MAX_GAMES:
        global_violations.append({
            "metric": "games_attempted",
            "observed": len(games),
            "approved_limit": MAX_GAMES,
        })
    if total_nodes > envelope["maximum_nodes"]:
        global_violations.append({
            "metric": "total_nodes",
            "observed": total_nodes,
            "approved_limit": envelope["maximum_nodes"],
        })
    if global_violations:
        classification, candidate = "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE", None
        stop_reason = stop_reason or "screen_global_resource_envelope_violation"
    result = {
        "schema": SCHEMA,
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "strength_or_promotion_evidence": False,
        "base_git_sha": BASE_SHA,
        "git_sha": head,
        "classification": classification,
        "incomplete_reason": stop_reason or (
            "one_or_more_pairs_incomplete_or_invalid"
            if classification == "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE"
            else None
        ),
        **metadata,
        "resource_envelope": envelope,
        "resource_bound_violations": global_violations,
        "first_screen_source_sha": source["git_sha"],
        "first_screen_result_sha256": source_sha,
        "first_screen_pair_scores": {str(k): v for k, v in FIRST_PAIR_SCORES.items()},
        "candidate_eligibility": "second_opening_pair_score > 0.5 and two_opening_mean_pair_score > 0.5",
        "candidate_indices": list(CANDIDATE_INDICES),
        "pairs": pairs,
        "ranked_candidates": _rank_candidates(pairs),
        "selected_candidate": candidate,
        "games_attempted": len(games),
        "games_completed_valid": sum(bool(game["completed"] and game["valid"]) for game in games),
        "total_nodes": total_nodes,
        "elapsed_seconds": round(time.monotonic() - started, 6),
    }
    _atomic_json(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(output_dir=args.output_dir)
    print(json.dumps({"classification": result["classification"],
                      "candidate": result["selected_candidate"],
                      "pairs": len(result["pairs"]),
                      "games": result["games_attempted"],
                      "total_nodes": result["total_nodes"]}, sort_keys=True))
    return 0 if result["classification"] != "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
