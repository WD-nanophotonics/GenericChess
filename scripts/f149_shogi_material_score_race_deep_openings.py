"""F149: threshold-10 Standard Shogi score race with deep neutral openings."""

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
from generic_chess.core.attacks import is_in_check
from generic_chess.core.coordinates import square_to_index
from generic_chess.learning.openings import generate_arena_openings
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
SCORE_THRESHOLD = 10
CAPTURE_POINTS = 1
CHECK_POINTS = 1
SAFETY_MAX_PLIES = 512
OPENING_MIN_PLIES = 16
OPENING_MAX_PLIES = 32
TT_MAX_ENTRIES = 250_000
SEARCH_LIMITS = SearchLimits(max_nodes=1000, max_depth=12, quiescence_max_depth=4, quiescence_hard_max_depth=8, deterministic=True)
PILOT_SEED = 1_490_001
DISCRIMINATION_SEED = 1_490_101
SCREENING_SEEDS = {1: 1_491_001, 2: 1_491_002}
PROMOTION_SEEDS = {1: 1_492_001, 2: 1_492_002}
PILOT_TARGET_PAIRS = 8
DISCRIMINATION_TARGET_PAIRS = 12
SCREENING_TARGET_PAIRS = 8
PILOT_POOL_OPENINGS = 64
DISCRIMINATION_POOL_OPENINGS = 96
COMMON_POOL_OPENINGS = 128
PROMOTION_POOL_OPENINGS = 256


def _compile():
    return v2._compile()


def _limits(max_nodes=1000):
    return SearchLimits(max_nodes=max_nodes, max_depth=12, quiescence_max_depth=4, quiescence_hard_max_depth=8, deterministic=True)


def opening_corpus(compiled, seed, count):
    return generate_arena_openings(compiled, count=count, seed=seed, min_plies=OPENING_MIN_PLIES, max_plies=OPENING_MAX_PLIES).openings


def _opening_record(opening):
    return {"opening_id": opening.final_position_key, "index": opening.index, "target_plies": opening.target_plies, "actual_plies": len(opening.actions), "actions": [v2.action_to_dict(action) for action in opening.actions]}


def score_event(before_position, action, after_position, mover: int, compiled) -> dict:
    target = v2.action_target_square(action)
    captured = before_position.board[square_to_index(target, compiled.board_size)]
    capture = int(captured is not None and captured.owner != mover and not compiled.types_by_id[captured.current_type_id].is_anchor)
    check = int(is_in_check(after_position, 1 - mover, compiled))
    return {"capture": capture, "check": check, "points": CAPTURE_POINTS * capture + CHECK_POINTS * check}


def _core_winner(result):
    return v2._core_winner(result)


def resolve_terminal(result, scores):
    return v2.resolve_terminal(result, scores)


def resolve_threshold(scores, mover):
    return (mover, "score_threshold", True) if scores[mover] >= SCORE_THRESHOLD else (None, "", False)


def play_score_race(compiled, opening, champion, child, child_owner, ordering_values, limits=SEARCH_LIMITS):
    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    players = (_player(compiled, child if child_owner == 0 else champion, ordering_values), _player(compiled, child if child_owner == 1 else champion, ordering_values))
    scores, captures, checks, actions = [0, 0], [0, 0], [0, 0], []
    winner, reason, cause, threshold_ply = None, "", "ongoing", None
    while session.result.status is SessionStatus.ONGOING and len(session.history) < SAFETY_MAX_PLIES:
        mover = session.state.position.side_to_move
        decision = players[mover].choose_action(session, limits)
        if decision.declaration is not None:
            session.declare(decision.declaration)
            result = session.result
            cause = result.status.value
            if _core_winner(result):
                winner, reason = result.winner, result.status.value
            break
        if decision.action is None or decision.action not in session.legal_actions():
            raise RuntimeError("AlphaBeta returned no legal action")
        before = session.state.position
        after = session.submit(decision.action)
        event = score_event(before, decision.action, after.position, mover, compiled)
        scores[mover] += event["points"]
        captures[mover] += event["capture"]
        checks[mover] += event["check"]
        actions.append({"actor": mover, "action": v2.action_to_dict(decision.action), **event, "scores": list(scores)})
        result = session.result
        if _core_winner(result):
            winner, reason, cause = result.winner, result.status.value, result.status.value
            break
        threshold_winner, threshold_reason, threshold_valid = resolve_threshold(scores, mover)
        if threshold_valid:
            winner, reason, cause, threshold_ply = threshold_winner, threshold_reason, "score_threshold", len(session.history)
            break
    result = session.result
    if winner is None and not reason:
        cause = result.status.value if result.status is not SessionStatus.ONGOING else "max_ply"
        winner, reason, valid = resolve_terminal(result, scores)
    else:
        valid = winner is not None and reason in {"score_threshold", "score_tiebreak", "checkmate", "perpetual_check", "declaration", "resignation"}
    return {"child_owner": child_owner, "winner": winner, "result": reason if valid else "invalid_nondecisive_terminal", "decisive_reason": reason, "terminal_cause": cause, "threshold_ply": threshold_ply, "plies": len(session.history), "scores": list(scores), "capture_points": captures, "check_points": checks, "total_points": sum(scores), "valid": valid, "actions": actions}


def _pair_task(payload):
    compiled = _compile()
    opening = v2._opening_from_payload(payload["opening"])
    games = [play_score_race(compiled, opening, tuple(payload["champion"]), tuple(payload["child"]), owner, dict(payload["ordering_values"]), _limits(payload.get("max_nodes", 1000))) for owner in (0, 1)]
    pair_score = v2.pair_score(games)
    return {"pair_index": opening.index, "opening_id": opening.final_position_key, "opening_target_plies": opening.target_plies, "games": games, "valid": pair_score is not None, "pair_score": pair_score}


def _run_wave(openings, champion, child, ordering_values, workers):
    payloads = [{"opening": v2._opening_payload(o), "champion": list(champion), "child": list(child), "ordering_values": ordering_values} for o in openings]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_pair_task, payloads))


def run_pairs(champion, child, openings, ordering_values, workers=4, target_pairs=None):
    target = len(openings) if target_pairs is None else target_pairs
    attempts, valid_rows, cursor = [], [], 0
    while len(valid_rows) < target and cursor < len(openings):
        wave_size = target if cursor == 0 else min(target - len(valid_rows), len(openings) - cursor)
        wave = openings[cursor:cursor + wave_size]
        cursor += len(wave)
        rows = _run_wave(wave, champion, child, ordering_values, workers)
        attempts.extend(rows)
        valid_rows.extend(row for row in rows if row["valid"])
    return {"rows": sorted(valid_rows, key=lambda row: row["pair_index"])[:target], "attempts": attempts, "invalid_pairs": sum(not row["valid"] for row in attempts), "attempt_count": len(attempts)}


def summarize(result, seed):
    return v2.summarize(result, seed)


def _screen_shared(compiled, champion, mutants, ordering_values, seed, workers):
    pool = opening_corpus(compiled, seed, COMMON_POOL_OPENINGS)
    selected, maps, invalid = [], {i: {} for i in range(6)}, []
    for start in range(0, len(pool), SCREENING_TARGET_PAIRS):
        wave = pool[start:start + SCREENING_TARGET_PAIRS]
        if len(wave) < SCREENING_TARGET_PAIRS:
            break
        all_rows = []
        for i, mutant in enumerate(mutants):
            rows = _run_wave(wave, champion, mutant, ordering_values, workers)
            all_rows.append(rows)
            maps[i].update({row["opening_id"]: row for row in rows})
        for offset, opening in enumerate(wave):
            rows = [candidate[offset] for candidate in all_rows]
            if all(row["valid"] for row in rows):
                selected.append(opening.final_position_key)
                if len(selected) == SCREENING_TARGET_PAIRS:
                    records = []
                    for i, mutant in enumerate(mutants):
                        chosen = [maps[i][identity] for identity in selected]
                        records.append({"mutant_index": i, "vector": _vector_record(mutant), "result": summarize({"rows": chosen, "attempts": chosen, "invalid_pairs": 0}, 1_493_000 + i), "rows": chosen})
                    return records, {"shared_opening_ids": selected, "shared_opening_target_plies": [next(o.target_plies for o in pool if o.final_position_key == identity) for identity in selected], "invalid_attempts": invalid, "pool_opening_count": len(pool)}
            else:
                invalid.extend({"mutant_index": i, "pair_index": row["pair_index"], "valid": row["valid"]} for i, row in enumerate(rows) if not row["valid"])
    raise RuntimeError("F149 common screening opening pool exhausted")


def _promotion(compiled, champion, child, ordering_values, seed, workers, generation):
    result = run_pairs(champion, child, opening_corpus(compiled, seed, PROMOTION_POOL_OPENINGS), ordering_values, workers, 32)
    return result, summarize(result, 1_494_000 + generation)


def _base_result(compiled, ordering_values, gen0, workers):
    return {"schema": "F149_SHOGI_MATERIAL_SCORE_RACE_DEEP_OPENINGS_V1", "ruleset_fingerprint": compiled.ruleset_fingerprint, "type_ids": list(TYPE_IDS), "score_race": {"threshold": SCORE_THRESHOLD, "capture_points": 1, "check_points": 1, "capture_plus_check_points": 2, "safety_max_plies": SAFETY_MAX_PLIES, "score_independent_of_material_values": True}, "opening_contract": {"min_plies": OPENING_MIN_PLIES, "max_plies": OPENING_MAX_PLIES, "evaluator_neutral": True, "terminal_free_required": True}, "search": {"max_nodes": 1000, "max_depth": 12, "qdepth": [4, 8], "tt_max_entries": TT_MAX_ENTRIES, "tuning": "SearchTuning()", "fixed_ordering_values": ordering_values, "fixed_ordering_sha256": _sha(ordering_values), "process_workers": workers}, "f146_reproduction": {"material_evaluator": "F144 MaterialOnlyEvaluator", "gen0_seed": GEN0_SEED, "gen0_vector": list(gen0), "gen0_vector_sha256": _vector_record(gen0)["sha256"], "score_event_source_confirmation": "score_event reads only position/action/compiled/mover; no material vector input", "score_event_source_sha256": hashlib.sha256(inspect.getsource(score_event).encode()).hexdigest()}}


def run(*, output: Path, workers=4, pilot_only=False):
    compiled = _compile()
    ordering_values = _ordering_values(compiled)
    gen0 = gen0_vector(GEN0_SEED)
    expected = (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
    if tuple(gen0) != expected or tuple(diagnostic_vectors()["Gen0"]) != expected:
        raise RuntimeError("Gen0 vector parity failure")
    m140 = tuple(diagnostic_vectors()["M140"])
    pilot_openings = opening_corpus(compiled, PILOT_SEED, PILOT_POOL_OPENINGS)
    pilot_run = run_pairs(gen0, gen0, pilot_openings, ordering_values, workers, PILOT_TARGET_PAIRS)
    pilot = summarize(pilot_run, 1_495_001)
    pilot["self_pair_mean_exactly_half"] = pilot["mean_pair_score"] == 0.5
    pilot["acceptance"] = pilot["valid_pair_count"] == 8 and pilot["invalid_game_fraction"] < 0.25 and pilot["threshold_or_formal_decisive_fraction"] >= 0.50 and pilot["median_valid_game_plies"] < 200 and pilot["self_pair_mean_exactly_half"]
    base = _base_result(compiled, ordering_values, gen0, workers)
    base.update({"gen0": {"seed": GEN0_SEED, "vector": _vector_record(gen0), "sanity": _sanity(gen0)}, "pilot": pilot, "pilot_rows": pilot_run["rows"], "pilot_attempts": pilot_run["attempts"], "pilot_openings": [_opening_record(o) for o in pilot_openings], "pilot_only": pilot_only, "m140_diagnostic": {"seed": 1_440_401, "sigma": 1.40, "vector": _vector_record(m140)}})
    if pilot_only or not pilot["acceptance"]:
        base["classification"] = "SCORE_RACE_DEEP_OPENINGS_PILOT_ACCEPTED" if pilot["acceptance"] else "SCORE_RACE_DEEP_OPENINGS_PILOT_FAILED_DENSITY"
        base["source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        base["git_sha"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        output.write_text(json.dumps(base, indent=2, sort_keys=True), encoding="utf-8")
        return base
    discr_openings = opening_corpus(compiled, DISCRIMINATION_SEED, DISCRIMINATION_POOL_OPENINGS)
    discr_run = run_pairs(gen0, m140, discr_openings, ordering_values, workers, DISCRIMINATION_TARGET_PAIRS)
    discr = summarize(discr_run, 1_495_101)
    discr["non_0_5_pair_count"] = sum(score != 0.5 for score in discr["pair_scores"])
    discr["acceptance"] = discr["valid_pair_count"] == DISCRIMINATION_TARGET_PAIRS and discr["non_0_5_pair_count"] >= 3
    base.update({"discrimination": discr, "discrimination_rows": discr_run["rows"], "discrimination_openings": [_opening_record(o) for o in discr_openings]})
    if not discr["acceptance"]:
        base["classification"] = "SCORE_RACE_DEEP_OPENINGS_DENSE_BUT_INSUFFICIENT_MATERIAL_DISCRIMINATION"
        base["source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        base["git_sha"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        output.write_text(json.dumps(base, indent=2, sort_keys=True), encoding="utf-8")
        return base
    champion, generations = gen0, []
    for generation in (1, 2):
        mutants = mutate_vectors(champion, generation)
        screening, meta = _screen_shared(compiled, champion, mutants, ordering_values, SCREENING_SEEDS[generation], workers)
        selected = max(screening, key=lambda row: (row["result"]["mean_pair_score"], row["result"]["child_better_pairs"], -row["mutant_index"]))
        selected_vector = tuple(selected["vector"]["values"])
        promotion_run, promotion = _promotion(compiled, champion, selected_vector, ordering_values, PROMOTION_SEEDS[generation], workers, generation)
        passed = promotion["mean_pair_score"] > 0.5 and promotion["bootstrap_95_ci"][0] > 0.5
        generations.append({"generation": generation, "parent": _vector_record(champion), "mutants": screening, "screening_meta": meta, "selected_mutant_index": selected["mutant_index"], "selected": _vector_record(selected_vector), "promotion": promotion, "promotion_rows": promotion_run["rows"], "promoted": passed})
        if not passed:
            break
        champion = selected_vector
    classification = "MATERIAL_ONLY_SCORE_RACE_GEN1_DOES_NOT_BEAT_GEN0" if not generations or not generations[0]["promoted"] else "MATERIAL_ONLY_SCORE_RACE_GEN1_PASSES_GEN2_DOES_NOT_BEAT_GEN1" if len(generations) < 2 or not generations[1]["promoted"] else "MATERIAL_ONLY_SCORE_RACE_GEN1_GEN2_IMPROVEMENT_ESTABLISHED"
    base.update({"classification": classification, "generations": generations, "final_champion": _vector_record(champion), "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()})
    output.write_text(json.dumps(base, indent=2, sort_keys=True), encoding="utf-8")
    return base


def main():
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
