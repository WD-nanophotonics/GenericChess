"""F147: threshold-1 Standard Shogi material-only score-race evolution.

F147 changes only the F146 score-race threshold.  The evaluator, fixed search
+budget, event weights, terminal precedence, and paired process runner remain
unchanged.  The pilot is intentionally runnable by itself so density is
verified before any mutation screening or promotion work begins.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import inspect
import json
import statistics
import subprocess
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.limits import SearchLimits
from generic_chess.learning.openings import ArenaOpening, generate_arena_openings
from generic_chess.session.result import SessionStatus
from generic_chess.session.session import GameSession

from scripts import f146_shogi_material_score_race_threshold3_evolution as v2
from scripts.f145_shogi_material_only_fitness_signal_diagnosis import diagnostic_vectors
from scripts.f144_shogi_material_only_arena_evolution import (
    GEN0_SEED,
    TYPE_IDS,
    _ordering_values,
    _player,
    _sanity,
    _sha,
    _vector_record,
    gen0_vector,
    mutate_vectors,
)

ROOT = Path(__file__).resolve().parents[1]
SCORE_THRESHOLD = 1
SAFETY_MAX_PLIES = 512
TT_MAX_ENTRIES = 250_000
SEARCH_LIMITS = SearchLimits(
    max_nodes=1000,
    max_depth=12,
    quiescence_max_depth=4,
    quiescence_hard_max_depth=8,
    deterministic=True,
)
PILOT_SEED = 1_470_001
DISCRIMINATION_SEED = 1_470_101
SCREENING_SEEDS = {1: 1_471_001, 2: 1_471_002}
PROMOTION_SEEDS = {1: 1_472_001, 2: 1_472_002}
PILOT_TARGET_PAIRS = 8
DISCRIMINATION_TARGET_PAIRS = 8
SCREENING_TARGET_PAIRS = 8
PROMOTION_TARGET_PAIRS = 32
COMMON_POOL_OPENINGS = 128
PILOT_POOL_OPENINGS = 64
DISCRIMINATION_POOL_OPENINGS = 64
PROMOTION_POOL_OPENINGS = 256


def _compile():
    return v2._compile()


def _limits(max_nodes: int = SEARCH_LIMITS.max_nodes) -> SearchLimits:
    return SearchLimits(
        max_nodes=max_nodes,
        max_depth=12,
        quiescence_max_depth=4,
        quiescence_hard_max_depth=8,
        deterministic=True,
    )


def score_event(before_position, action, after_position, mover: int, compiled) -> dict:
    """Score only capture/check events; no material vector enters this path."""
    return v2.score_event(before_position, action, after_position, mover, compiled)


def _core_winner(result) -> bool:
    return v2._core_winner(result)


def resolve_terminal(result, scores: list[int]) -> tuple[int | None, str, bool]:
    return v2.resolve_terminal(result, scores)


def resolve_threshold(scores: list[int], mover: int) -> tuple[int | None, str, bool]:
    if scores[mover] >= SCORE_THRESHOLD:
        return mover, "score_threshold", True
    return None, "", False


def play_score_race(compiled, opening, champion, child, child_owner, ordering_values, limits=SEARCH_LIMITS):
    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    players = (
        _player(compiled, child if child_owner == 0 else champion, ordering_values),
        _player(compiled, child if child_owner == 1 else champion, ordering_values),
    )
    scores = [0, 0]
    capture_points = [0, 0]
    check_points = [0, 0]
    actions = []
    winner = None
    decisive_reason = ""
    terminal_cause = "ongoing"
    threshold_ply = None
    while session.result.status is SessionStatus.ONGOING and len(session.history) < SAFETY_MAX_PLIES:
        mover = session.state.position.side_to_move
        decision = players[mover].choose_action(session, limits)
        if decision.declaration is not None:
            session.declare(decision.declaration)
            result = session.result
            terminal_cause = result.status.value
            if _core_winner(result):
                winner = result.winner
                decisive_reason = result.status.value
            break
        if decision.action is None:
            raise RuntimeError(f"ongoing game returned no action: {decision.termination_reason}")
        if decision.action not in session.legal_actions():
            raise RuntimeError("AlphaBeta returned an illegal action")
        before = session.state.position
        after = session.submit(decision.action)
        event = score_event(before, decision.action, after.position, mover, compiled)
        scores[mover] += event["points"]
        capture_points[mover] += event["capture"]
        check_points[mover] += event["check"]
        actions.append({"actor": mover, "action": v2.action_to_dict(decision.action), **event, "scores": list(scores)})
        result = session.result
        if _core_winner(result):
            winner = result.winner
            decisive_reason = result.status.value
            terminal_cause = result.status.value
            break
        threshold_winner, threshold_reason, threshold_valid = resolve_threshold(scores, mover)
        if threshold_valid:
            winner = threshold_winner
            decisive_reason = threshold_reason
            terminal_cause = "score_threshold"
            threshold_ply = len(session.history)
            break
    result = session.result
    if winner is None and decisive_reason == "":
        terminal_cause = result.status.value if result.status is not SessionStatus.ONGOING else "max_ply"
        winner, decisive_reason, valid = resolve_terminal(result, scores)
    else:
        valid = winner is not None and decisive_reason in {
            "score_threshold", "score_tiebreak", "checkmate", "perpetual_check", "declaration", "resignation"
        }
    return {
        "child_owner": child_owner,
        "winner": winner,
        "result": decisive_reason if valid else "invalid_nondecisive_terminal",
        "decisive_reason": decisive_reason,
        "terminal_cause": terminal_cause,
        "threshold_ply": threshold_ply,
        "plies": len(session.history),
        "scores": list(scores),
        "capture_points": list(capture_points),
        "check_points": list(check_points),
        "total_points": sum(scores),
        "valid": valid,
        "actions": actions,
    }


def _play_pair_task(payload: dict) -> dict:
    compiled = _compile()
    opening = v2._opening_from_payload(payload["opening"])
    games = [
        play_score_race(
            compiled, opening, tuple(payload["champion"]), tuple(payload["child"]), owner,
            dict(payload["ordering_values"]), _limits(int(payload.get("max_nodes", 1000)))
        )
        for owner in (0, 1)
    ]
    scores = [None if not game["valid"] else (1.0 if game["winner"] == game["child_owner"] else 0.0) for game in games]
    return {
        "pair_index": opening.index,
        "opening_id": opening.final_position_key,
        "games": games,
        "valid": all(game["valid"] for game in games),
        "pair_score": None if any(score is None for score in scores) else sum(scores) / 2.0,
    }


def _payloads(openings, champion, child, ordering_values, max_nodes=1000):
    return [
        {
            "opening": v2._opening_payload(opening),
            "champion": list(champion),
            "child": list(child),
            "ordering_values": ordering_values,
            "max_nodes": max_nodes,
        }
        for opening in openings
    ]


def _run_wave(openings, champion, child, ordering_values, workers, max_nodes=1000):
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_play_pair_task, _payloads(openings, champion, child, ordering_values, max_nodes)))


def run_pairs(champion, child, openings, ordering_values, workers=4, target_pairs=None, max_nodes=1000):
    target = len(openings) if target_pairs is None else target_pairs
    if len(openings) < target:
        raise ValueError("opening pool is smaller than target pair count")
    attempts = []
    valid_rows = []
    cursor = 0
    while len(valid_rows) < target and cursor < len(openings):
        wave_size = target if cursor == 0 else min(target - len(valid_rows), len(openings) - cursor)
        wave = openings[cursor : cursor + wave_size]
        cursor += len(wave)
        wave_rows = _run_wave(wave, champion, child, ordering_values, workers, max_nodes)
        attempts.extend(wave_rows)
        valid_rows.extend(row for row in wave_rows if row["valid"])
    return {
        "rows": sorted(valid_rows, key=lambda row: row["pair_index"])[:target],
        "attempts": attempts,
        "attempt_count": len(attempts),
        "invalid_equal_score_games": sum(not game["valid"] for row in attempts for game in row["games"]),
        "invalid_pairs": sum(not row["valid"] for row in attempts),
    }


def summarize(result, bootstrap_seed):
    return v2.summarize(result, bootstrap_seed)


def _openings(compiled, seed, count):
    return generate_arena_openings(compiled, count=count, seed=seed, min_plies=4, max_plies=12).openings


def _screen_shared(compiled, champion, mutants, ordering_values, seed, workers):
    pool = _openings(compiled, seed, COMMON_POOL_OPENINGS)
    by_mutant = {index: {} for index in range(len(mutants))}
    invalid_attempts = []
    selected_ids = []
    for start in range(0, len(pool), SCREENING_TARGET_PAIRS):
        wave = pool[start : start + SCREENING_TARGET_PAIRS]
        if len(wave) < SCREENING_TARGET_PAIRS:
            break
        wave_rows = []
        for mutant_index, mutant in enumerate(mutants):
            raw = _run_wave(wave, champion, mutant, ordering_values, workers)
            wave_rows.append(raw)
            by_mutant[mutant_index].update({row["opening_id"]: row for row in raw})
        for offset, opening in enumerate(wave):
            rows = [raw[offset] for raw in wave_rows]
            if all(row["valid"] for row in rows):
                selected_ids.append(opening.final_position_key)
                if len(selected_ids) == SCREENING_TARGET_PAIRS:
                    records = []
                    for mutant_index, mutant in enumerate(mutants):
                        chosen = [by_mutant[mutant_index][opening_id] for opening_id in selected_ids]
                        records.append({
                            "mutant_index": mutant_index,
                            "vector": _vector_record(mutant),
                            "result": summarize({"rows": chosen, "attempts": chosen, "invalid_pairs": 0}, 1_473_000 + mutant_index),
                            "rows": chosen,
                        })
                    return records, {
                        "shared_opening_ids": selected_ids,
                        "invalid_attempts": invalid_attempts,
                        "pool_opening_count": len(pool),
                    }
            else:
                invalid_attempts.extend({"mutant_index": i, "pair_index": row["pair_index"], "valid": row["valid"]} for i, row in enumerate(rows) if not row["valid"])
    raise RuntimeError("F147 common screening opening pool exhausted")


def _promotion(compiled, champion, child, ordering_values, seed, workers, generation):
    openings = _openings(compiled, seed, PROMOTION_POOL_OPENINGS)
    result = run_pairs(champion, child, openings, ordering_values, workers=workers, target_pairs=PROMOTION_TARGET_PAIRS)
    return result, summarize(result, 1_474_000 + generation)


def _base_result(compiled, ordering_values, gen0, workers):
    return {
        "schema": "F147_SHOGI_MATERIAL_SCORE_RACE_V3",
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "type_ids": list(TYPE_IDS),
        "score_race": {
            "threshold": SCORE_THRESHOLD,
            "capture_points": 1,
            "check_points": 1,
            "capture_plus_check_points": 2,
            "safety_max_plies": SAFETY_MAX_PLIES,
            "score_independent_of_material_values": True,
        },
        "search": {
            "max_nodes": 1000,
            "max_depth": 12,
            "qdepth": [4, 8],
            "tt_max_entries": TT_MAX_ENTRIES,
            "tuning": "SearchTuning()",
            "fixed_ordering_values": ordering_values,
            "fixed_ordering_sha256": _sha(ordering_values),
            "process_workers": workers,
        },
        "f146_reproduction": {
            "material_evaluator": "F144 MaterialOnlyEvaluator",
            "gen0_seed": GEN0_SEED,
            "gen0_vector": list(gen0),
            "gen0_vector_sha256": _vector_record(gen0)["sha256"],
            "score_event_source_confirmation": "score_event reads only position/action/compiled/mover; no material vector input",
            "score_event_source_sha256": hashlib.sha256(inspect.getsource(score_event).encode()).hexdigest(),
        },
    }


def run(*, output: Path, workers: int = 4, pilot_only: bool = False) -> dict:
    compiled = _compile()
    ordering_values = _ordering_values(compiled)
    gen0 = gen0_vector(GEN0_SEED)
    expected_gen0 = (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
    if tuple(gen0) != expected_gen0:
        raise RuntimeError("Gen0 vector parity failure")
    vectors = diagnostic_vectors()
    if tuple(vectors["Gen0"]) != gen0:
        raise RuntimeError("F145 diagnostic Gen0 parity failure")
    m140 = tuple(vectors["M140"])
    pilot_run = run_pairs(gen0, gen0, _openings(compiled, PILOT_SEED, PILOT_POOL_OPENINGS), ordering_values, workers=workers, target_pairs=PILOT_TARGET_PAIRS)
    pilot = summarize(pilot_run, 1_475_001)
    pilot["self_pair_mean_exactly_half"] = pilot["mean_pair_score"] == 0.5
    pilot["acceptance"] = (
        pilot["valid_pair_count"] == PILOT_TARGET_PAIRS
        and pilot["invalid_game_fraction"] < 0.50
        and pilot["threshold_or_formal_decisive_fraction"] >= 0.50
        and pilot["median_valid_game_plies"] < 150
        and pilot["self_pair_mean_exactly_half"]
    )
    base = _base_result(compiled, ordering_values, gen0, workers)
    base.update({
        "gen0": {"seed": GEN0_SEED, "vector": _vector_record(gen0), "sanity": _sanity(gen0)},
        "pilot": pilot,
        "pilot_rows": pilot_run["rows"],
        "pilot_only": pilot_only,
        "m140_diagnostic": {"seed": 1_440_401, "sigma": 1.40, "vector": _vector_record(m140)},
    })
    if pilot_only or not pilot["acceptance"]:
        base["classification"] = "SCORE_RACE_THRESHOLD1_PILOT_ACCEPTED" if pilot["acceptance"] else "SCORE_RACE_THRESHOLD1_PILOT_FAILED_DENSITY"
        base["source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        base["git_sha"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        output.write_text(json.dumps(base, indent=2, sort_keys=True), encoding="utf-8")
        return base
    discrimination_run = run_pairs(gen0, m140, _openings(compiled, DISCRIMINATION_SEED, DISCRIMINATION_POOL_OPENINGS), ordering_values, workers=workers, target_pairs=DISCRIMINATION_TARGET_PAIRS)
    discrimination = summarize(discrimination_run, 1_475_101)
    discrimination["non_0_5_pair_count"] = sum(score != 0.5 for score in discrimination["pair_scores"])
    discrimination["acceptance"] = discrimination["valid_pair_count"] == DISCRIMINATION_TARGET_PAIRS and discrimination["non_0_5_pair_count"] >= 1
    base.update({"discrimination": discrimination, "discrimination_rows": discrimination_run["rows"]})
    if not discrimination["acceptance"]:
        base["classification"] = "SCORE_RACE_THRESHOLD1_DENSE_BUT_NO_MATERIAL_DISCRIMINATION"
        base["source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        base["git_sha"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        output.write_text(json.dumps(base, indent=2, sort_keys=True), encoding="utf-8")
        return base
    champion = gen0
    generations = []
    for generation in (1, 2):
        mutants = mutate_vectors(champion, generation)
        screening, screening_meta = _screen_shared(compiled, champion, mutants, ordering_values, SCREENING_SEEDS[generation], workers)
        selected = max(screening, key=lambda row: (row["result"]["mean_pair_score"], row["result"]["child_better_pairs"], -row["mutant_index"]))
        selected_vector = tuple(selected["vector"]["values"])
        promotion_run, promotion = _promotion(compiled, champion, selected_vector, ordering_values, PROMOTION_SEEDS[generation], workers, generation)
        passed = promotion["mean_pair_score"] > 0.5 and promotion["bootstrap_95_ci"][0] > 0.5
        generations.append({
            "generation": generation,
            "parent": _vector_record(champion),
            "mutants": screening,
            "screening_meta": screening_meta,
            "selected_mutant_index": selected["mutant_index"],
            "selected": _vector_record(selected_vector),
            "promotion": promotion,
            "promotion_rows": promotion_run["rows"],
            "promoted": passed,
        })
        if not passed:
            break
        champion = selected_vector
    if not generations or not generations[0]["promoted"]:
        classification = "MATERIAL_ONLY_SCORE_RACE_GEN1_DOES_NOT_BEAT_GEN0"
    elif len(generations) < 2 or not generations[1]["promoted"]:
        classification = "MATERIAL_ONLY_SCORE_RACE_GEN1_PASSES_GEN2_DOES_NOT_BEAT_GEN1"
    else:
        classification = "MATERIAL_ONLY_SCORE_RACE_GEN1_GEN2_IMPROVEMENT_ESTABLISHED"
    base.update({
        "classification": classification,
        "generations": generations,
        "final_champion": _vector_record(champion),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    })
    output.write_text(json.dumps(base, indent=2, sort_keys=True), encoding="utf-8")
    return base


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--pilot-only", action="store_true")
    args = parser.parse_args()
    result = run(output=args.output, workers=args.workers, pilot_only=args.pilot_only)
    print(json.dumps({"classification": result["classification"], "generations": len(result.get("generations", ()))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
