"""One-opening paired diagnostic for the tied sigma-.70 Gen1 mutant_4."""

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
from scripts import f153_shogi_material_mutation_root_sensitivity as mutations
from scripts import f158_shogi_sigma070_single_pair_diagnostic as bounded_game
from scripts.f144_shogi_material_only_arena_evolution import GEN0_SEED, _ordering_values, gen0_vector
from scripts.f153_sigma070_gen1_second_opening_candidate_screen import (
    _game_stop_reason,
    _resource_bound_violations,
)
from scripts.f153_sigma070_gen1_single_opening_population_screen import _game_end_category

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / ".generic_chess_flow/f153-sigma070-gen1-tiebreak-mutant4-weak-opening-output"
BASE_SHA = "6fb2d63e24fc2d286ee36610945b49691bca266a"
SCHEMA = "F153_SIGMA070_GEN1_TIEBREAK_MUTANT4_WEAK_OPENING_DIAGNOSTIC_V1"
GEN0_VALUES = (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
MUTANT_INDEX = 4
MUTANT_VALUES = (690, 382, 387, 3636, 498, 1000, 6221, 1298, 3157, 312, 3031, 2508, 966)
MUTANT_SEQUENCE_SHA256 = "3f015f6631460f6c2a71a8d80898cd7d781d02e9b605639c701408b420e654e9"
OPENING = {
    "seed": 1_590_402,
    "opening_id": "55c88a8fe6da49131e9af2eb53bc533b85a0e90e74454c93b1106f5f245cf29e",
    "plies": 22,
    "target_plies": 22,
}
PRIOR_MUTANT1_PAIR_SCORE = 0.25
ROLE_ORDER = (0, 1)
MAX_GAMES = 2
MAX_TOTAL_PLIES_PER_GAME = 128
MAX_SEARCHED_PLIES = 106
MAX_NODES_PER_GAME = 106_000
MAX_TOTAL_NODES = 212_000
MAX_NODES_PER_MOVE = 1_000
MAX_GAME_SECONDS = 480
MAX_INTERNAL_SECONDS = 1_100
EXTERNAL_HARD_SECONDS = 1_200
MAX_DEPTH = 12
QDEPTH = (4, 8)
TT_ENTRIES = 250_000
CLASSIFICATIONS = {
    "improves": "GEN1_TIEBREAK_MUTANT4_WEAK_OPENING_IMPROVES",
    "equals": "GEN1_TIEBREAK_MUTANT4_WEAK_OPENING_EQUALS",
    "not_improved": "GEN1_TIEBREAK_MUTANT4_WEAK_OPENING_NOT_IMPROVED",
    "inconclusive": "GEN1_TIEBREAK_MUTANT4_WEAK_OPENING_INCONCLUSIVE",
}


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def resource_envelope() -> dict:
    return {
        "schema": "generic-chess-resource-envelope-v1",
        "envelope_id": "f153-sigma070-gen1-tiebreak-alternate-v2",
        "logical_cpu_count": 2,
        "intended_cpu_lanes": 1,
        "expected_wall_minutes": None,
        "hard_wall_minutes": 20,
        "expected_cpu_hours": None,
        "hard_cpu_hours": 1,
        "arena_pairs": 1,
        "maximum_games": MAX_GAMES,
        "maximum_nodes": MAX_TOTAL_NODES,
        "maximum_plies": MAX_GAMES * MAX_TOTAL_PLIES_PER_GAME,
        "maximum_concurrent_games": 1,
        "stage_count": 1,
        "nodes_per_move": MAX_NODES_PER_MOVE,
        "max_depth": MAX_DEPTH,
        "qdepth": list(QDEPTH),
        "tt_entries": TT_ENTRIES,
        "opening_seed": OPENING["seed"],
        "opening_count": 1,
        "opening_id": OPENING["opening_id"],
        "opening_plies": OPENING["plies"],
        "opening_seeds": [OPENING["seed"]],
        "opening_ids": [OPENING["opening_id"]],
        "opening_plies_by_seed": {str(OPENING["seed"]): OPENING["plies"]},
        "searched_plies_by_seed": {str(OPENING["seed"]): MAX_SEARCHED_PLIES},
        "maximum_total_plies_per_game_including_opening": MAX_TOTAL_PLIES_PER_GAME,
        "maximum_searched_plies_per_game": MAX_SEARCHED_PLIES,
        "maximum_nodes_per_game": MAX_NODES_PER_GAME,
        "maximum_game_wall_seconds": MAX_GAME_SECONDS,
        "maximum_internal_wall_seconds": MAX_INTERNAL_SECONDS,
        "external_hard_wall_seconds": EXTERNAL_HARD_SECONDS,
        "purpose": (
            "One role-swapped mutant_4 versus Gen0 pair on the already-pinned seed-1590402 opening, "
            "as a one-opening causal diagnostic only; no replacement opening, candidate selection, "
            "Gen2, promotion, or full Standard Shogi validation."
        ),
    }


def _candidate() -> tuple[tuple[int, ...], tuple[int, ...]]:
    gen0 = tuple(gen0_vector(GEN0_SEED))
    if gen0 != GEN0_VALUES:
        raise AssertionError("Gen0 differs from the amended Chat order")
    vectors = tuple(tuple(row) for row in mutations.mutation_vectors_at_sigma(gen0, 0.70))
    if len(vectors) <= MUTANT_INDEX or vectors[MUTANT_INDEX] != MUTANT_VALUES:
        raise AssertionError("mutant_4 differs from the amended Chat order")
    digest = mutations._sha(vectors[MUTANT_INDEX])
    if digest != MUTANT_SEQUENCE_SHA256:
        raise AssertionError("mutant_4 sequence SHA256 differs")
    return gen0, vectors[MUTANT_INDEX]


def _generate_opening(compiled):
    openings = race.opening_corpus(compiled, OPENING["seed"], 1)
    if len(openings) != 1:
        raise AssertionError("pinned seed did not return exactly one opening")
    opening = openings[0]
    if (opening.index != 0 or len(opening.actions) != OPENING["plies"]
            or opening.target_plies != OPENING["target_plies"]
            or opening.final_position_key != OPENING["opening_id"]):
        raise AssertionError("regenerated opening differs from the one pinned by Chat")
    return opening


def _classify(pair_score: float | None) -> str:
    if pair_score is None:
        return CLASSIFICATIONS["inconclusive"]
    if pair_score > PRIOR_MUTANT1_PAIR_SCORE:
        return CLASSIFICATIONS["improves"]
    if pair_score == PRIOR_MUTANT1_PAIR_SCORE:
        return CLASSIFICATIONS["equals"]
    return CLASSIFICATIONS["not_improved"]


def _base_result(head: str, envelope: dict) -> dict:
    return {
        "schema": SCHEMA,
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "classification": CLASSIFICATIONS["inconclusive"],
        "strength_or_promotion_evidence": False,
        "base_git_sha": BASE_SHA,
        "git_sha": head,
        "unknown": "whether tied mutant_4 scores above mutant_1 on mutant_1's weakest previously observed promotion opening",
        "candidate": {
            "name": "mutant_4",
            "index": MUTANT_INDEX,
            "values": list(MUTANT_VALUES),
            "sequence_sha256": MUTANT_SEQUENCE_SHA256,
        },
        "gen0_values": list(GEN0_VALUES),
        "prior_mutant_1_pair_score_on_opening": PRIOR_MUTANT1_PAIR_SCORE,
        "opening": {
            **OPENING,
            "index": 0,
            "reused_existing_pinned_opening": True,
            "replacement_allowed": False,
        },
        "score_race": {
            "capture_points": 1,
            "check_points": 1,
            "capture_plus_check_points": 2,
            "threshold": 10,
            "formal_core_decisive_precedence": True,
            "unequal_nondecisive_terminal": "score_tiebreak",
            "equal_nondecisive_terminal": "valid score_draw",
            "game_score": {"win": 1.0, "draw": 0.5, "loss": 0.0},
            "pair_score": "mean of mutant_4 game scores for candidate owners 0 and 1",
        },
        "search": {
            "material_only": True,
            "fixed_rule_derived_ordering": True,
            "nodes_per_move": MAX_NODES_PER_MOVE,
            "max_depth": MAX_DEPTH,
            "qdepth": list(QDEPTH),
            "tt_entries": TT_ENTRIES,
            "tuning": "SearchTuning()",
            "fresh_player_and_tt_per_game": True,
        },
        "resource_envelope": envelope,
        "games": [],
        "games_attempted": 0,
        "games_completed_valid": 0,
        "total_nodes": 0,
        "pair_score": None,
        "incomplete_reason": "diagnostic_in_progress",
    }


def _pair_record(games: list[dict]) -> dict:
    valid = (
        len(games) == MAX_GAMES
        and {game.get("candidate_owner") for game in games} == {0, 1}
        and all(game.get("completed") is True and game.get("valid") is True
                and game.get("resource_envelope_compliant") is True for game in games)
    )
    scores = [game.get("candidate_game_score") for game in games]
    score = sum(scores) / MAX_GAMES if valid and all(value is not None for value in scores) else None
    differentials = [game.get("candidate_minus_gen0_event_points") for game in games]
    return {
        "valid": valid,
        "pair_score": score,
        "prior_mutant_1_pair_score": PRIOR_MUTANT1_PAIR_SCORE,
        "pair_score_difference_vs_mutant_1": None if score is None else score - PRIOR_MUTANT1_PAIR_SCORE,
        "aggregate_mutant_minus_gen0_event_points": sum(x for x in differentials if x is not None),
        "games": games,
    }


def run(*, output_dir: Path) -> dict:
    started = time.monotonic()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(["git", "rev-parse", "origin/sandbox"], cwd=ROOT, text=True).strip()
    parent = subprocess.check_output(["git", "rev-parse", "HEAD^"], cwd=ROOT, text=True).strip()
    if head != remote or parent != BASE_SHA:
        raise AssertionError("diagnostic requires a published checkpoint based directly on amended Chat SHA")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite diagnostic evidence: {output_dir}")
    gen0, mutant = _candidate()
    compiled = race._compile()
    envelope = resource_envelope()
    output_dir.mkdir(parents=True, exist_ok=True)
    _atomic_json(output_dir / "resource-envelope.json", envelope)
    result = _base_result(head, envelope)
    _atomic_json(output_dir / "result.json", result)
    try:
        opening = _generate_opening(compiled)
    except Exception as exc:
        result["incomplete_reason"] = f"pinned_opening_unusable:{type(exc).__name__}:{exc}"
        _atomic_json(output_dir / "result.json", result)
        return result

    ordering = _ordering_values(compiled)
    deadline = started + MAX_INTERNAL_SECONDS
    games = []
    stop_reason = None
    prior_node_cap = bounded_game.MAX_TOTAL_NODES
    bounded_game.MAX_TOTAL_NODES = MAX_NODES_PER_GAME * MAX_GAMES
    try:
        for candidate_owner in ROLE_ORDER:
            if time.monotonic() >= deadline:
                stop_reason = f"owner_{candidate_owner}_internal_wall_clock_cap_before_start"
                break
            raw = bounded_game.play_capped_game(
                compiled, opening, gen0, mutant, candidate_owner, ordering,
                deadline=deadline, game_timeout=MAX_GAME_SECONDS,
            )
            game = {
                **raw,
                "mutant_index": MUTANT_INDEX,
                "candidate_owner": candidate_owner,
                "gen0_owner": 1 - candidate_owner,
                "opening_seed": OPENING["seed"],
                "opening_id": OPENING["opening_id"],
                "candidate_points": int(raw["scores"][candidate_owner]),
                "gen0_points": int(raw["scores"][1 - candidate_owner]),
                "candidate_capture_events": int(raw["capture_points"][candidate_owner]),
                "gen0_capture_events": int(raw["capture_points"][1 - candidate_owner]),
                "candidate_check_events": int(raw["check_points"][candidate_owner]),
                "gen0_check_events": int(raw["check_points"][1 - candidate_owner]),
                "candidate_minus_gen0_event_points": int(raw["scores"][candidate_owner]) - int(raw["scores"][1 - candidate_owner]),
                "terminal_category": _game_end_category(raw),
                "candidate_game_score": race.v2.child_game_score(raw),
                "resource_envelope_compliant": None,
                "resource_bound_violations": None,
            }
            game_path = output_dir / f"seed-{OPENING['seed']}-candidate-owner-{candidate_owner}.json"
            # Make every returned raw game durable before any resource assessment.
            _atomic_json(game_path, game)
            violations = _resource_bound_violations(game, envelope)
            game["resource_envelope_compliant"] = not violations
            game["resource_bound_violations"] = violations
            if violations:
                game["valid"] = False
                game["candidate_game_score"] = None
            _atomic_json(game_path, game)
            games.append(game)
            stop_reason = _game_stop_reason(game, violations)
            if stop_reason:
                stop_reason = f"owner_{candidate_owner}_{stop_reason}"
            result.update({
                "games": games,
                "games_attempted": len(games),
                "games_completed_valid": sum(g.get("completed") is True and g.get("valid") is True for g in games),
                "total_nodes": sum(g.get("nodes", 0) for g in games),
                "pair": _pair_record(games),
                "incomplete_reason": stop_reason or "diagnostic_in_progress",
            })
            _atomic_json(output_dir / "result.json", result)
            if stop_reason:
                break
    finally:
        bounded_game.MAX_TOTAL_NODES = prior_node_cap

    pair = _pair_record(games)
    pair_score = pair["pair_score"]
    total_nodes = sum(game.get("nodes", 0) for game in games)
    global_violations = []
    if len(games) > MAX_GAMES:
        global_violations.append({"metric": "games_attempted", "observed": len(games), "approved_limit": MAX_GAMES})
    if total_nodes > MAX_TOTAL_NODES:
        global_violations.append({"metric": "total_nodes", "observed": total_nodes, "approved_limit": MAX_TOTAL_NODES})
    if global_violations:
        pair_score = None
        stop_reason = stop_reason or "global_resource_envelope_violation"
    result.update({
        "games": games,
        "pair": pair,
        "pair_score": pair_score,
        "classification": _classify(pair_score),
        "games_attempted": len(games),
        "games_completed_valid": sum(g.get("completed") is True and g.get("valid") is True for g in games),
        "total_nodes": total_nodes,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "resource_bound_violations": global_violations,
        "incomplete_reason": stop_reason if pair_score is None else None,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    })
    _atomic_json(output_dir / "result.json", result)
    _atomic_json(output_dir / "pair.json", pair)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(output_dir=args.output_dir)
    print(json.dumps({
        "classification": result["classification"],
        "games": result["games_attempted"],
        "pair_score": result.get("pair_score"),
        "difference_vs_mutant_1": result.get("pair", {}).get("pair_score_difference_vs_mutant_1"),
    }, sort_keys=True))
    return int(result["classification"] == CLASSIFICATIONS["inconclusive"])


if __name__ == "__main__":
    raise SystemExit(main())
