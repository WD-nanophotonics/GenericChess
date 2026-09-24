"""One-opening, role-swapped B0 vs Gen0 score-race diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import f149_shogi_material_score_race_deep_openings as race
from scripts import f153_shogi_material_mutation_root_sensitivity as mutations
from scripts import f158_shogi_sigma070_single_pair_diagnostic as bounded_game
from scripts.f144_shogi_material_only_arena_evolution import (
    GEN0_SEED, MUTATION_BASE_SEED, _ordering_values, canonicalize_vector, gen0_vector,
)
from scripts.f153_sigma070_gen1_single_opening_population_screen import _game_end_category

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "64f9abf98e31632c7a3b8ce291c83d30e9709d42"
SCHEMA = "F153_SIGMA070_GEN1_B0_SINGLE_PAIR_DIAGNOSTIC_V1"
OPENING_SEED = 1_590_501
OPENING_COUNT = 1
OPENING_ID = "7f41b405eb646fdf24fec42aa499b40f33ba340909ad3a80a38adcf394a91c43"
OPENING_PLIES = 27
GEN0_VALUES = (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
B0_INDEX = 0
B0_RNG_SEED = 1_440_501
B0_VALUES = (176, 653, 4765, 6541, 260, 575, 12231, 620, 5193, 1000, 2161, 3312, 762)
B0_SEQUENCE_SHA256 = "c6d2f2bc610678f69fdfa69ca7e2b4bebc5f48e8c32f472d843de2e6dfcbc1a3"
ROLE_ORDER = (0, 1)
MAX_GAMES = 2
MAX_TOTAL_PLIES_PER_GAME = 128
MAX_NODES_PER_MOVE = 1_000
MAX_GAME_SECONDS = 420
MAX_INTERNAL_SECONDS = 840
EXTERNAL_HARD_SECONDS = 900
MAX_DEPTH = 12
QDEPTH = (4, 8)
TT_ENTRIES = 250_000
CLASSIFICATIONS = {
    "positive": "GEN1_RESTART_BATCH_B0_POSITIVE_SIGNAL",
    "tie": "GEN1_RESTART_BATCH_B0_TIED",
    "negative": "GEN1_RESTART_BATCH_B0_NEGATIVE_SIGNAL",
    "inconclusive": "GEN1_RESTART_BATCH_B0_INCONCLUSIVE",
}
PRIOR_ROOTS_BY_SOURCE = {
    "5738e1f589b8096372ce9c369692937123c13a383f70ceb44ec4f6a19a9bfd2b":
        "F153 mutant4 single-pair score-signal diagnostic",
    "742b4fc33ad8a8e9e57369f74b7544245622932fe16d99326f82a9163c1b801c":
        "F151 root-sensitivity opening; also F158 historical opening",
    "5d4f445657c94a1d4a6ec5acc51ecdd0eaea001bdba8e7e81304d9277392dd6d":
        "historical root pinned by F153 mutant4 fresh-pair diagnostic",
    "b046dec8bd8675adfbbc6dc1c0d439ffbd878c8b08a433ab84abb200b119160b":
        "F153 material mutation root-sensitivity diagnostic; F158 historical root",
    "88f8c456be07973346e31075ff83271f28cb898ce1912755f566d41c591c6dbd":
        "F153 material mutation root-sensitivity diagnostic result",
    "8abe104fc6a2960e6ba2052484abbb61e0cd01aed79a0e6ae67f9818519e2439":
        "F153 material mutation root-sensitivity diagnostic result",
    "8e30c44f09ec4f5af088cbaaed6727a664f29af8abd12c38ab0c9d0561717c91":
        "F153 material mutation root-sensitivity diagnostic result",
    "a4397bb2b7538ae608cb0a19887348b68433d6e3ac77cdf29a713a68baee0716":
        "F153 material mutation root-sensitivity diagnostic result",
    "acf8ddb443682ab8c0db80e0c1172b33736e99a1f72471728230a06c637785f5":
        "F153 material mutation root-sensitivity diagnostic result",
    "bddff5b4466c5b5c75faa8297d52524a78c618e7c298f0b6938e00568175cccf":
        "F153 material mutation root-sensitivity diagnostic result",
    "c081cff6ca9620e3588f5e0d2c61d4cbb4ede158e817a3debb964d9e4909061a":
        "F153 material mutation root-sensitivity diagnostic result",
    "d14e25b47a125dac58ebed2d3d74e2aef0fc32169ff18bfcad06a0a98d0c4bdd":
        "F153 material mutation root-sensitivity diagnostic result",
    "e06770317abac084ce7a3e9d4c4a513f5d45f4e9be47bd8d2d66ca4975509620":
        "F153 material mutation root-sensitivity diagnostic result",
    "7e04681975c54713539109e629d64d568aebf72547382db2f04faf53a920bda9":
        "F153 mutant4 fresh single-pair diagnostic",
    "5af7d590672eb94fffc329ae6de806754e505e7f64be31d8470eb4799ca290a8":
        "F153 Gen1 first-opening population selection screen",
    "7a426930f39a4c1d267dbbf3bb861ffa91c3fad3e7c9d1ff1e9698913a2a46ef":
        "F153 Gen1 second-opening candidate selection screen",
    "aa1404a624da9ab33da03b018d55c1446e5c8d87fa5f9d32cc1b7f6955a6e6c9":
        "F153 Gen1 promotion benchmark opening seed 1590401",
    "55c88a8fe6da49131e9af2eb53bc533b85a0e90e74454c93b1106f5f245cf29e":
        "F153 Gen1 promotion opening seed 1590402; mutant4/mutant5 weak-opening diagnostics",
    "7aed7c89773a348adf45e5cdf1803289190af2140b44415fe78f61c2970023ca":
        "F153 Gen1 promotion benchmark opening seed 1590403",
    "8c47ed2f29aca51e607df59766dd05d57d6ddb521cb0569e8a7180ba2c287753":
        "F153 Gen1 promotion benchmark opening seed 1590404",
}
PREVIOUS_OPENING_IDS = frozenset(PRIOR_ROOTS_BY_SOURCE)


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _candidate() -> tuple[tuple[int, ...], tuple[int, ...]]:
    gen0 = tuple(gen0_vector(GEN0_SEED))
    if gen0 != GEN0_VALUES:
        raise AssertionError("Gen0 differs from the amended Chat order")
    seed = MUTATION_BASE_SEED + 200 + B0_INDEX
    if seed != B0_RNG_SEED:
        raise AssertionError("B0 RNG seed differs from F144 generation-2 index-0 contract")
    rng = random.Random(seed)
    derived = canonicalize_vector(
        value * math.exp(0.70 * rng.gauss(0.0, 1.0)) for value in gen0
    )
    if len(derived) != len(gen0) or derived != B0_VALUES:
        raise AssertionError("derived B0 differs from the amended Chat vector")
    if mutations._sha(derived) != B0_SEQUENCE_SHA256:
        raise AssertionError("B0 vector or sequence hash differs from the amended Chat order")
    return gen0, derived


def _opening(compiled):
    openings = race.opening_corpus(compiled, OPENING_SEED, OPENING_COUNT)
    if len(openings) != OPENING_COUNT:
        raise AssertionError("the prescribed seed/count did not yield exactly one opening")
    opening = openings[0]  # no fallback/replacement opening is permitted
    if not race.OPENING_MIN_PLIES <= len(opening.actions) <= race.OPENING_MAX_PLIES:
        raise AssertionError("the first generated opening violates F149's 16-32 ply contract")
    if opening.final_position_key in PREVIOUS_OPENING_IDS:
        raise AssertionError("the first generated opening duplicates a prior diagnostic root")
    if (opening.index != 0 or opening.final_position_key != OPENING_ID
            or len(opening.actions) != OPENING_PLIES):
        raise AssertionError("the prescribed seed no longer yields the pinned opening")
    return opening


def resource_envelope(opening_plies: int = OPENING_PLIES,
                      opening_id: str = OPENING_ID) -> dict:
    if not race.OPENING_MIN_PLIES <= opening_plies <= race.OPENING_MAX_PLIES:
        raise AssertionError("opening is outside F149's 16-32 ply contract")
    searched = MAX_TOTAL_PLIES_PER_GAME - opening_plies
    nodes_per_game = searched * MAX_NODES_PER_MOVE
    return {
        "schema": "generic-chess-resource-envelope-v1",
        "envelope_id": "f153-sigma070-gen1-b0-single-pair-v1",
        "logical_cpu_count": 2,
        "intended_cpu_lanes": 1,
        "expected_wall_minutes": None,
        "hard_wall_minutes": 15,
        "expected_cpu_hours": None,
        "hard_cpu_hours": 1,
        "arena_pairs": 1,
        "maximum_games": MAX_GAMES,
        "maximum_nodes": MAX_GAMES * nodes_per_game,
        "maximum_plies": MAX_GAMES * MAX_TOTAL_PLIES_PER_GAME,
        "maximum_concurrent_games": 1,
        "stage_count": 1,
        "nodes_per_move": MAX_NODES_PER_MOVE,
        "max_depth": MAX_DEPTH,
        "qdepth": list(QDEPTH),
        "tt_entries": TT_ENTRIES,
        "opening_seed": OPENING_SEED,
        "opening_count": OPENING_COUNT,
        "opening_id": opening_id,
        "opening_plies": opening_plies,
        "opening_seeds": [OPENING_SEED],
        "opening_ids": [opening_id],
        "opening_plies_by_seed": {str(OPENING_SEED): opening_plies},
        "searched_plies_by_seed": {str(OPENING_SEED): searched},
        "maximum_total_plies_per_game_including_opening": MAX_TOTAL_PLIES_PER_GAME,
        "maximum_searched_plies_per_game": searched,
        "maximum_nodes_per_game": nodes_per_game,
        "maximum_game_wall_seconds": MAX_GAME_SECONDS,
        "maximum_internal_wall_seconds": MAX_INTERNAL_SECONDS,
        "external_hard_wall_seconds": EXTERNAL_HARD_SECONDS,
        "purpose": (
            "Exactly one B0-versus-Gen0 role-swapped pair on the first opening from seed 1590501; "
            "no replacement opening, additional candidate, Gen2, promotion, or full-game validation."
        ),
    }


def _resource_bound_violations(game: dict, envelope: dict) -> list[dict]:
    fields = (
        ("plies", "maximum_total_plies_per_game_including_opening"),
        ("scored_plies", "maximum_searched_plies_per_game"),
        ("nodes", "maximum_nodes_per_game"),
        ("elapsed_seconds", "maximum_game_wall_seconds"),
    )
    return [
        {"metric": metric, "observed": game[metric], "approved_limit": envelope[bound]}
        for metric, bound in fields if game[metric] > envelope[bound]
    ]


def _classify(pair_score: float | None) -> str:
    if pair_score is None:
        return CLASSIFICATIONS["inconclusive"]
    if pair_score > 0.5:
        return CLASSIFICATIONS["positive"]
    if pair_score == 0.5:
        return CLASSIFICATIONS["tie"]
    return CLASSIFICATIONS["negative"]


def _first_scoring_event(game: dict, opening_plies: int) -> dict | None:
    for scored_ply, action in enumerate(game["actions"], start=1):
        if int(action["points"]) > 0:
            return {
                "scored_ply": scored_ply,
                "total_game_ply": opening_plies + scored_ply,
                "actor": action["actor"],
                "capture": action["capture"],
                "check": action["check"],
                "points": action["points"],
            }
    return None


def _pair(games: list[dict]) -> dict:
    valid = (
        len(games) == MAX_GAMES
        and {game.get("child_owner") for game in games} == {0, 1}
        and all(game.get("completed") is True and game.get("valid") is True
                and game.get("resource_envelope_compliant") is True for game in games)
    )
    scores = [race.v2.child_game_score(game) for game in games]
    score = sum(scores) / MAX_GAMES if valid and all(item is not None for item in scores) else None
    role_differentials = [
        {"candidate_owner": game.get("candidate_owner", game.get("child_owner")),
         "candidate_minus_gen0_event_points": game.get("candidate_minus_gen0_event_points")}
        for game in games
    ]
    return {
        "valid": valid and score is not None,
        "pair_score": score,
        "aggregate_candidate_minus_gen0_event_points": sum(
            row["candidate_minus_gen0_event_points"] or 0 for row in role_differentials
        ),
        "per_role_event_point_differential": role_differentials,
        "games": games,
        "classification": _classify(score),
    }


def run(*, output_dir: Path) -> dict:
    started = time.monotonic()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(["git", "rev-parse", "origin/sandbox"], cwd=ROOT, text=True).strip()
    parent = subprocess.check_output(["git", "rev-parse", "HEAD^"], cwd=ROOT, text=True).strip()
    if head != remote or parent != BASE_SHA:
        raise AssertionError("diagnostic requires a published checkpoint based directly on Chat BASE_SHA")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite diagnostic evidence: {output_dir}")

    gen0, b0 = _candidate()
    output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "schema": SCHEMA,
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "classification": CLASSIFICATIONS["inconclusive"],
        "incomplete_reason": "run_in_progress_or_external_timeout",
        "strength_or_promotion_evidence": False,
        "base_git_sha": BASE_SHA,
        "git_sha": head,
        "candidate": {"name": "B0", "index": B0_INDEX, "rng_seed": B0_RNG_SEED,
                      "values": list(b0), "sequence_sha256": B0_SEQUENCE_SHA256},
        "gen0_values": list(gen0),
        "opening": {"seed": OPENING_SEED, "count": OPENING_COUNT,
                    "opening_id": OPENING_ID, "plies": OPENING_PLIES,
                    "first_generated_opening_used_unconditionally": True,
                    "replacement_allowed": False},
        "score_race": {"capture_points": 1, "check_points": 1,
                       "capture_plus_check_points": 2, "threshold": race.SCORE_THRESHOLD,
                       "formal_core_decisive_precedence": True,
                       "score_independent_of_material_values": True},
        "search": {"material_only": True, "fixed_ordering_values": None,
                   "nodes_per_move": MAX_NODES_PER_MOVE, "max_depth": MAX_DEPTH,
                   "qdepth": list(QDEPTH), "tt_entries": TT_ENTRIES,
                   "tuning": "SearchTuning()", "fresh_player_and_tt_per_game": True},
        "resource_envelope": None,
        "games": [], "games_attempted": 0, "games_completed_valid": 0,
        "total_nodes": 0, "pair_score": None,
    }
    _atomic_json(output_dir / "result.json", result)
    try:
        compiled = race._compile()
        opening = _opening(compiled)
    except Exception as exc:
        result["incomplete_reason"] = f"opening_or_compile_unusable:{type(exc).__name__}:{exc}"
        _atomic_json(output_dir / "result.json", result)
        return result

    envelope = resource_envelope(len(opening.actions), opening.final_position_key)
    result["resource_envelope"] = envelope
    _atomic_json(output_dir / "resource-envelope.json", envelope)
    ordering = _ordering_values(compiled)
    result["search"]["fixed_ordering_values"] = ordering
    deadline = started + MAX_INTERNAL_SECONDS
    games: list[dict] = []
    stop_reason = None
    previous_node_limit = bounded_game.MAX_TOTAL_NODES
    bounded_game.MAX_TOTAL_NODES = envelope["maximum_nodes"]
    try:
        for owner in ROLE_ORDER:
            if time.monotonic() >= deadline:
                stop_reason = "internal_wall_cap_before_next_game"
                break
            raw = bounded_game.play_capped_game(
                compiled, opening, gen0, b0, owner, ordering,
                deadline=deadline, game_timeout=MAX_GAME_SECONDS,
            )
            game_path = output_dir / f"seed-{OPENING_SEED}-candidate-owner-{owner}.json"
            _atomic_json(game_path, raw)  # durable raw return precedes any resource assessment
            game = {
                **raw,
                "candidate": "B0",
                "candidate_owner": owner,
                "gen0_owner": 1 - owner,
                "opening_seed": OPENING_SEED,
                "opening_id": opening.final_position_key,
                "candidate_points": int(raw["scores"][owner]),
                "gen0_points": int(raw["scores"][1 - owner]),
                "candidate_capture_events": int(raw["capture_points"][owner]),
                "gen0_capture_events": int(raw["capture_points"][1 - owner]),
                "candidate_check_events": int(raw["check_points"][owner]),
                "gen0_check_events": int(raw["check_points"][1 - owner]),
                "candidate_event_points": int(raw["scores"][owner]),
                "gen0_event_points": int(raw["scores"][1 - owner]),
                "candidate_minus_gen0_event_points": int(raw["scores"][owner] - raw["scores"][1 - owner]),
                "first_scoring_event": _first_scoring_event(raw, len(opening.actions)),
                "threshold_10_reached": raw.get("threshold_ply") is not None,
                "terminal_category": _game_end_category(raw),
                "resource_envelope_compliant": None,
            }
            violations = _resource_bound_violations(game, envelope)
            game["resource_envelope_compliant"] = not violations
            game["resource_bound_violations"] = violations
            if violations:
                game["valid"] = False
            _atomic_json(game_path, game)
            games.append(game)
            if violations or not game.get("completed") or not game.get("valid"):
                stop_reason = "resource_bound_violation" if violations else (
                    game.get("inconclusive_reason") or "incomplete_or_invalid_game"
                )
            partial = _pair(games)
            result.update({"games": games, "games_attempted": len(games),
                           "games_completed_valid": sum(g.get("completed") is True and g.get("valid") is True for g in games),
                           "total_nodes": sum(g.get("nodes", 0) for g in games),
                           "pair_score": partial["pair_score"],
                           "classification": partial["classification"] if partial["valid"] else CLASSIFICATIONS["inconclusive"],
                           "incomplete_reason": stop_reason or "diagnostic_in_progress"})
            _atomic_json(output_dir / "result.json", result)
            if stop_reason:
                break
    finally:
        bounded_game.MAX_TOTAL_NODES = previous_node_limit

    pair = _pair(games)
    total_nodes = sum(game.get("nodes", 0) for game in games)
    result.update({
        "pair": pair,
        "pair_score": pair["pair_score"],
        "classification": pair["classification"] if pair["valid"] else CLASSIFICATIONS["inconclusive"],
        "incomplete_reason": None if pair["valid"] else (stop_reason or "pair_incomplete_or_invalid"),
        "games": games,
        "games_attempted": len(games),
        "games_completed_valid": sum(g.get("completed") is True and g.get("valid") is True for g in games),
        "total_nodes": total_nodes,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    })
    _atomic_json(output_dir / "result.json", result)
    _atomic_json(output_dir / "pair.json", pair)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    result = run(output_dir=parser.parse_args().output_dir)
    print(json.dumps({"classification": result["classification"],
                      "games": result["games_attempted"], "pair_score": result["pair_score"]}, sort_keys=True))
    return int(result["classification"] == CLASSIFICATIONS["inconclusive"])


if __name__ == "__main__":
    raise SystemExit(main())
