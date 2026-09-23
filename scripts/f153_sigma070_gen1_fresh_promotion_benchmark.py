"""Fresh-opening score-race benchmark for the selected sigma-.70 Gen1 candidate."""

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
from scripts import f153_shogi_material_mutation_root_sensitivity as mutations
from scripts import f158_shogi_sigma070_single_pair_diagnostic as bounded_game
from scripts.f144_shogi_material_only_arena_evolution import (
    GEN0_SEED,
    _ordering_values,
    gen0_vector,
)
from scripts.f153_sigma070_gen1_second_opening_candidate_screen import (
    _resource_bound_violations,
    _game_stop_reason,
)
from scripts.f153_sigma070_gen1_single_opening_population_screen import _game_end_category

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / ".generic_chess_flow/f153-sigma070-gen1-fresh-promotion-output"
BASE_SHA = "ac3688389b8e9f90b8ccfc8a6fd0cec4faec3308"
SCHEMA = "F153_SIGMA070_GEN1_FRESH_PROMOTION_BENCHMARK_V1"
GEN0_VALUES = (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
GEN1_VECTOR = (278, 183, 298, 4495, 153, 935, 5721, 1528, 1000, 1023, 2247, 1905, 520)
GEN1_SEQUENCE_SHA256 = "1511f7e07edeb9aec183b1d426e06242b0434da99588a43f309e37167eada08d"
OPENINGS = (
    {"seed": 1_590_401, "opening_id": "aa1404a624da9ab33da03b018d55c1446e5c8d87fa5f9d32cc1b7f6955a6e6c9", "plies": 25, "target_plies": 25},
    {"seed": 1_590_402, "opening_id": "55c88a8fe6da49131e9af2eb53bc533b85a0e90e74454c93b1106f5f245cf29e", "plies": 22, "target_plies": 22},
    {"seed": 1_590_403, "opening_id": "7aed7c89773a348adf45e5cdf1803289190af2140b44415fe78f61c2970023ca", "plies": 28, "target_plies": 28},
    {"seed": 1_590_404, "opening_id": "8c47ed2f29aca51e607df59766dd05d57d6ddb521cb0569e8a7180ba2c287753", "plies": 16, "target_plies": 16},
)
PREVIOUS_OPENING_IDS = {
    "5738e1f589b8096372ce9c369692937123c13a383f70ceb44ec4f6a19a9bfd2b",
    "742b4fc33ad8a8e9e57369f74b7544245622932fe16d99326f82a9163c1b801c",
    "5d4f445657c94a1d4a6ec5acc51ecdd0eaea001bdba8e7e81304d9277392dd6d",
    "7e04681975c54713539109e629d64d568aebf72547382db2f04faf53a920bda9",
    "5af7d590672eb94fffc329ae6de806754e505e7f64be31d8470eb4799ca290a8",
    "7a426930f39a4c1d267dbbf3bb861ffa91c3fad3e7c9d1ff1e9698913a2a46ef",
}
ROLE_ORDER = (0, 1)
MAX_PAIRS = len(OPENINGS)
MAX_GAMES = MAX_PAIRS * len(ROLE_ORDER)
MAX_TOTAL_PLIES_PER_GAME = 128
MAX_NODES_PER_MOVE = 1_000
MAX_GAME_SECONDS = 480
MAX_INTERNAL_SECONDS = 4_200
EXTERNAL_HARD_SECONDS = 4_500
MAX_DEPTH = 12
QDEPTH = (4, 8)
TT_ENTRIES = 250_000
PASS_CLASSIFICATION = "GEN1_SCORE_RACE_FRESH_PROMOTION_PASS"
FAIL_CLASSIFICATION = "GEN1_SCORE_RACE_FRESH_PROMOTION_FAIL"
INCONCLUSIVE_CLASSIFICATION = "GEN1_SCORE_RACE_FRESH_PROMOTION_INCONCLUSIVE"


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def resource_envelope() -> dict:
    searched = {str(row["seed"]): MAX_TOTAL_PLIES_PER_GAME - row["plies"] for row in OPENINGS}
    nodes = {seed: plies * MAX_NODES_PER_MOVE for seed, plies in searched.items()}
    return {
        "schema": "generic-chess-resource-envelope-v1",
        "envelope_id": "f153-sigma070-gen1-fresh-promotion-v1",
        "logical_cpu_count": 2,
        "intended_cpu_lanes": 1,
        "expected_wall_minutes": None,
        "hard_wall_minutes": EXTERNAL_HARD_SECONDS // 60,
        "expected_cpu_hours": None,
        "hard_cpu_hours": 2,
        "arena_pairs": MAX_PAIRS,
        "maximum_games": MAX_GAMES,
        "maximum_nodes": sum(nodes.values()) * 2,
        "maximum_plies": MAX_GAMES * MAX_TOTAL_PLIES_PER_GAME,
        "maximum_concurrent_games": 1,
        "stage_count": 1,
        "nodes_per_move": MAX_NODES_PER_MOVE,
        "max_depth": MAX_DEPTH,
        "qdepth": list(QDEPTH),
        "tt_entries": TT_ENTRIES,
        "opening_seed": OPENINGS[0]["seed"],
        "opening_count": MAX_PAIRS,
        "opening_id": OPENINGS[0]["opening_id"],
        "opening_plies": OPENINGS[0]["plies"],
        "opening_seeds": [row["seed"] for row in OPENINGS],
        "opening_ids": [row["opening_id"] for row in OPENINGS],
        "opening_plies_by_seed": {str(row["seed"]): row["plies"] for row in OPENINGS},
        "searched_plies_by_seed": searched,
        "maximum_total_plies_per_game_including_opening": MAX_TOTAL_PLIES_PER_GAME,
        "maximum_searched_plies_per_game": max(searched.values()),
        "maximum_nodes_per_game": max(nodes.values()),
        "maximum_game_wall_seconds": MAX_GAME_SECONDS,
        "maximum_internal_wall_seconds": MAX_INTERNAL_SECONDS,
        "external_hard_wall_seconds": EXTERNAL_HARD_SECONDS,
        "purpose": (
            "Exactly one candidate-Gen0 role-swapped pair on each of the four first-generated "
            "evaluator-neutral openings at seeds 1590401-1590404; no other games, replacement "
            "seeds, Gen2, or promotion"
        ),
    }


def _candidate() -> tuple[tuple[int, ...], tuple[int, ...]]:
    gen0 = tuple(gen0_vector(GEN0_SEED))
    if gen0 != GEN0_VALUES:
        raise AssertionError("Gen0 differs from the Chat order")
    vectors = tuple(tuple(row) for row in mutations.mutation_vectors_at_sigma(gen0, 0.70))
    if len(vectors) < 2 or vectors[1] != GEN1_VECTOR:
        raise AssertionError("selected Gen1 candidate differs from mutation sequence index 1")
    digest = mutations._sha(vectors[1])
    if digest != GEN1_SEQUENCE_SHA256:
        raise AssertionError("selected Gen1 candidate sequence SHA256 differs")
    return gen0, vectors[1]


def _generate_openings(compiled):
    if len({row["opening_id"] for row in OPENINGS}) != MAX_PAIRS:
        raise AssertionError("pinned promotion opening IDs are not mutually distinct")
    if {row["opening_id"] for row in OPENINGS} & PREVIOUS_OPENING_IDS:
        raise AssertionError("a promotion opening duplicates a prior diagnostic root")
    generated = []
    for expected in OPENINGS:
        candidates = race.opening_corpus(compiled, expected["seed"], 1)
        if len(candidates) != 1:
            raise AssertionError(f"seed {expected['seed']} did not return exactly one opening")
        opening = candidates[0]
        if (opening.index != 0 or len(opening.actions) != expected["plies"]
                or opening.target_plies != expected["target_plies"]
                or opening.final_position_key != expected["opening_id"]
                or not race.OPENING_MIN_PLIES <= len(opening.actions) <= race.OPENING_MAX_PLIES):
            raise AssertionError(f"seed {expected['seed']} differs from its accepted first opening")
        generated.append(opening)
    return generated


def _resource_violations(game: dict, opening: dict) -> list[dict]:
    limits = {
        "plies": MAX_TOTAL_PLIES_PER_GAME,
        "scored_plies": MAX_TOTAL_PLIES_PER_GAME - opening["plies"],
        "nodes": (MAX_TOTAL_PLIES_PER_GAME - opening["plies"]) * MAX_NODES_PER_MOVE,
        "elapsed_seconds": MAX_GAME_SECONDS,
    }
    return [
        {"metric": metric, "observed": game[metric], "approved_limit": limit}
        for metric, limit in limits.items()
        if game[metric] > limit
    ]


def _pair_record(opening: dict, games: list[dict]) -> dict:
    valid = (
        len(games) == 2
        and {game.get("candidate_owner") for game in games} == {0, 1}
        and all(game.get("completed") is True and game.get("valid") is True
                and game.get("resource_envelope_compliant") is True for game in games)
    )
    scores = [game.get("candidate_game_score") for game in games]
    score = sum(scores) / 2 if valid and all(value is not None for value in scores) else None
    differentials = [game.get("candidate_minus_gen0_event_points") for game in games]
    return {
        "opening_seed": opening["seed"],
        "opening_id": opening["opening_id"],
        "opening_plies": opening["plies"],
        "valid": valid,
        "pair_score": score,
        "pair_relation_to_half": "incomplete" if score is None else "above_0_5" if score > 0.5 else "below_0_5" if score < 0.5 else "equal_0_5",
        "aggregate_candidate_minus_gen0_event_point_differential": sum(x for x in differentials if x is not None),
        "games": games,
    }


def _classify(pairs: list[dict]) -> tuple[str, dict]:
    if len(pairs) != MAX_PAIRS or any(not pair["valid"] for pair in pairs):
        return INCONCLUSIVE_CLASSIFICATION, {}
    scores = [float(pair["pair_score"]) for pair in pairs]
    mean_score = sum(scores) / len(scores)
    positive = sum(score > 0.5 for score in scores)
    tied = sum(score == 0.5 for score in scores)
    negative = sum(score < 0.5 for score in scores)
    passed = mean_score > 0.5 and positive >= 2 and positive > negative
    return (PASS_CLASSIFICATION if passed else FAIL_CLASSIFICATION), {
        "promotion_mean_pair_score": mean_score,
        "positive_pairs": positive,
        "tied_pairs": tied,
        "negative_pairs": negative,
        "pass_conditions": {
            "mean_gt_0_5": mean_score > 0.5,
            "positive_pairs_at_least_2": positive >= 2,
            "positive_pairs_exceed_negative": positive > negative,
        },
    }


def _result_base(head: str, openings: list[dict], envelope: dict) -> dict:
    return {
        "schema": SCHEMA,
        "diagnostic_type": "STRENGTH_BENCHMARK",
        "strength_or_promotion_evidence": False,
        "base_git_sha": BASE_SHA,
        "git_sha": head,
        "candidate_index": 1,
        "gen0_values": list(GEN0_VALUES),
        "candidate_values": list(GEN1_VECTOR),
        "candidate_sequence_sha256": GEN1_SEQUENCE_SHA256,
        "score_race": {
            "capture_points": 1,
            "check_points": 1,
            "capture_plus_check_points": 2,
            "threshold": 10,
            "formal_core_decisive_precedence": True,
            "unequal_nondecisive_terminal": "score_tiebreak",
            "equal_nondecisive_terminal": "valid score_draw",
            "candidate_game_score": {"win": 1.0, "draw": 0.5, "loss": 0.0},
            "pair_score": "mean of the two role-swapped candidate game scores",
        },
        "search": {
            "material_only": True,
            "fixed_ordering": True,
            "nodes_per_move": MAX_NODES_PER_MOVE,
            "max_depth": MAX_DEPTH,
            "qdepth": list(QDEPTH),
            "tt_entries": TT_ENTRIES,
            "tuning": "SearchTuning()",
            "fresh_player_and_tt_per_game": True,
        },
        "openings": openings,
        "resource_envelope": envelope,
        "pairs": [],
        "games_attempted": 0,
        "games_completed_valid": 0,
        "total_nodes": 0,
        "classification": INCONCLUSIVE_CLASSIFICATION,
        "incomplete_reason": "benchmark_in_progress",
    }


def _snapshot(output_dir: Path, result: dict, pairs: list[dict], stop_reason: str | None = None) -> None:
    result["pairs"] = pairs
    games = [game for pair in pairs for game in pair["games"]]
    result["games_attempted"] = len(games)
    result["games_completed_valid"] = sum(game.get("completed") is True and game.get("valid") is True for game in games)
    result["total_nodes"] = sum(game.get("nodes", 0) for game in games)
    result["incomplete_reason"] = stop_reason or "benchmark_in_progress"
    _atomic_json(output_dir / "result.json", result)


def run(*, output_dir: Path) -> dict:
    started = time.monotonic()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(["git", "rev-parse", "origin/sandbox"], cwd=ROOT, text=True).strip()
    parent = subprocess.check_output(["git", "rev-parse", "HEAD^"], cwd=ROOT, text=True).strip()
    if head != remote or parent != BASE_SHA:
        raise AssertionError("fresh promotion benchmark requires a published checkpoint based directly on Chat SHA")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite fresh-promotion evidence: {output_dir}")
    gen0, candidate = _candidate()
    compiled = race._compile()
    envelope = resource_envelope()
    opening_rows = [
        {**row, "index": 0, "evaluator_neutral": True,
         "first_generated_opening_used_unconditionally": True}
        for row in OPENINGS
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    _atomic_json(output_dir / "resource-envelope.json", envelope)
    result = _result_base(head, opening_rows, envelope)
    _atomic_json(output_dir / "result.json", result)
    try:
        openings_native = _generate_openings(compiled)
    except Exception as exc:
        result["classification"] = INCONCLUSIVE_CLASSIFICATION
        result["incomplete_reason"] = f"prescribed_opening_unusable:{type(exc).__name__}:{exc}"
        _atomic_json(output_dir / "result.json", result)
        return result

    ordering = _ordering_values(compiled)
    deadline = started + MAX_INTERNAL_SECONDS
    pairs: list[dict] = []
    total_nodes = 0
    stop_reason = None
    for expected, opening, opening_row in zip(OPENINGS, openings_native, opening_rows):
        role_games = []
        for candidate_owner in ROLE_ORDER:
            if time.monotonic() >= deadline:
                stop_reason = f"seed_{expected['seed']}_owner_{candidate_owner}_internal_wall_clock_cap_before_start"
                break
            raw = bounded_game.play_capped_game(
                compiled, opening, gen0, candidate, candidate_owner, ordering,
                deadline=deadline, game_timeout=MAX_GAME_SECONDS,
            )
            game = {
                **raw,
                "mutant_index": 1,
                "candidate_index": 1,
                "candidate_owner": candidate_owner,
                "gen0_owner": 1 - candidate_owner,
                "opening_seed": expected["seed"],
                "opening_id": expected["opening_id"],
                "opening_plies": expected["plies"],
                "first_scoring_event": None,
                "resource_envelope_compliant": None,
                "resource_bound_violations": None,
            }
            game_path = output_dir / f"seed-{expected['seed']}-candidate-owner-{candidate_owner}.json"
            _atomic_json(game_path, game)

            candidate_points = int(raw["scores"][candidate_owner])
            gen0_points = int(raw["scores"][1 - candidate_owner])
            first_scoring = next((event for event in raw["actions"] if event.get("points", 0) > 0), None)
            game.update({
                "candidate_points": candidate_points,
                "gen0_points": gen0_points,
                "candidate_capture_events": int(raw["capture_points"][candidate_owner]),
                "gen0_capture_events": int(raw["capture_points"][1 - candidate_owner]),
                "candidate_check_events": int(raw["check_points"][candidate_owner]),
                "gen0_check_events": int(raw["check_points"][1 - candidate_owner]),
                "candidate_minus_gen0_event_points": candidate_points - gen0_points,
                "first_scoring_event": first_scoring,
                "terminal_category": _game_end_category(raw),
                "candidate_game_score": race.v2.child_game_score(raw),
            })
            per_opening_envelope = {
                **envelope,
                "maximum_searched_plies_per_game": MAX_TOTAL_PLIES_PER_GAME - expected["plies"],
                "maximum_nodes_per_game": (MAX_TOTAL_PLIES_PER_GAME - expected["plies"]) * MAX_NODES_PER_MOVE,
            }
            violations = _resource_bound_violations(game, per_opening_envelope)
            game["resource_envelope_compliant"] = not violations
            game["resource_bound_violations"] = violations
            if violations:
                game["valid"] = False
                game["candidate_game_score"] = None
            _atomic_json(game_path, game)
            role_games.append(game)
            total_nodes += game["nodes"]
            stop_reason = _game_stop_reason(game, violations)
            if stop_reason:
                stop_reason = f"seed_{expected['seed']}_owner_{candidate_owner}_{stop_reason}"
            pair = _pair_record(opening_row, role_games)
            current_pairs = [*pairs, pair]
            _snapshot(output_dir, result, current_pairs, stop_reason)
            if stop_reason:
                break
        pair = _pair_record(opening_row, role_games)
        pairs.append(pair)
        _atomic_json(output_dir / f"seed-{expected['seed']}-pair.json", pair)
        if stop_reason:
            break

    classification, statistics = _classify(pairs)
    game_records = [game for pair in pairs for game in pair["games"]]
    global_violations = []
    if len(game_records) > MAX_GAMES:
        global_violations.append({"metric": "games_attempted", "observed": len(game_records), "approved_limit": MAX_GAMES})
    if total_nodes > envelope["maximum_nodes"]:
        global_violations.append({"metric": "total_nodes", "observed": total_nodes, "approved_limit": envelope["maximum_nodes"]})
    if global_violations:
        classification, statistics = INCONCLUSIVE_CLASSIFICATION, {}
        stop_reason = stop_reason or "benchmark_global_resource_envelope_violation"
    result.update({
        "pairs": pairs,
        "classification": classification,
        "incomplete_reason": stop_reason if classification == INCONCLUSIVE_CLASSIFICATION else None,
        **statistics,
        "positive_pairs": statistics.get("positive_pairs"),
        "tied_pairs": statistics.get("tied_pairs"),
        "negative_pairs": statistics.get("negative_pairs"),
        "resource_bound_violations": global_violations,
        "games_attempted": len(game_records),
        "games_completed_valid": sum(game.get("completed") is True and game.get("valid") is True for game in game_records),
        "total_nodes": total_nodes,
        "elapsed_seconds": round(time.monotonic() - started, 6),
    })
    _atomic_json(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(output_dir=args.output_dir)
    print(json.dumps({
        "classification": result["classification"],
        "promotion_mean_pair_score": result.get("promotion_mean_pair_score"),
        "positive_pairs": result.get("positive_pairs"),
        "negative_pairs": result.get("negative_pairs"),
        "games": result["games_attempted"],
    }, sort_keys=True))
    return int(result["classification"] == INCONCLUSIVE_CLASSIFICATION)


if __name__ == "__main__":
    raise SystemExit(main())
