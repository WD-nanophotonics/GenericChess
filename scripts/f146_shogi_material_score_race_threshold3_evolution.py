"""F146: threshold-3 Standard Shogi material-only score-race evolution."""

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
from generic_chess.core.actions import action_from_dict, action_target_square, action_to_dict
from generic_chess.core.attacks import is_in_check
from generic_chess.core.coordinates import square_to_index
from generic_chess.learning.openings import ArenaOpening, generate_arena_openings
from generic_chess.learning.statistics import bootstrap_pair_mean_ci
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.session.result import SessionStatus
from generic_chess.session.session import GameSession

from scripts import f145_shogi_material_score_race as v1
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
SCORE_THRESHOLD = 3
SAFETY_MAX_PLIES = 512
TT_MAX_ENTRIES = 250_000
SEARCH_LIMITS = SearchLimits(
    max_nodes=1000,
    max_depth=12,
    quiescence_max_depth=4,
    quiescence_hard_max_depth=8,
    deterministic=True,
)
PILOT_SEED = 1_460_001
SCREENING_SEEDS = {1: 1_461_001, 2: 1_461_002}
PROMOTION_SEEDS = {1: 1_462_001, 2: 1_462_002}


def _opening_payload(opening: ArenaOpening) -> dict:
    return {
        "index": opening.index,
        "opening_seed": opening.opening_seed,
        "target_plies": opening.target_plies,
        "actions": [action_to_dict(action) for action in opening.actions],
        "final_position_key": opening.final_position_key,
    }


def _opening_from_payload(payload: dict) -> ArenaOpening:
    return ArenaOpening(
        index=int(payload["index"]),
        opening_seed=int(payload["opening_seed"]),
        target_plies=int(payload["target_plies"]),
        actions=tuple(action_from_dict(action) for action in payload["actions"]),
        final_position_key=str(payload["final_position_key"]),
    )


def _compile():
    return compile_ruleset_for_execution(build_standard_shogi_ruleset())


def _limits(max_nodes: int = SEARCH_LIMITS.max_nodes) -> SearchLimits:
    return SearchLimits(
        max_nodes=max_nodes,
        max_depth=12,
        quiescence_max_depth=4,
        quiescence_hard_max_depth=8,
        deterministic=True,
    )


def score_event(before_position, action, after_position, mover: int, compiled) -> dict:
    """Score only the observable capture/check event; no material vector input."""
    target = action_target_square(action)
    captured = before_position.board[square_to_index(target, compiled.board_size)]
    capture = int(
        captured is not None
        and captured.owner != mover
        and not compiled.types_by_id[captured.current_type_id].is_anchor
    )
    gave_check = int(is_in_check(after_position, 1 - mover, compiled))
    return {"capture": capture, "check": gave_check, "points": capture + gave_check}


def _core_winner(result) -> bool:
    return result.status in {
        SessionStatus.CHECKMATE,
        SessionStatus.PERPETUAL_CHECK,
        SessionStatus.DECLARATION,
        SessionStatus.RESIGNATION,
    } and result.winner is not None


def resolve_terminal(result, scores: list[int]) -> tuple[int | None, str, bool]:
    """Prefer formal Core winners, then use the race score at nondecisive ends."""
    if _core_winner(result):
        return result.winner, result.status.value, True
    if scores[0] == scores[1]:
        return None, "score_draw", True
    return (0 if scores[0] > scores[1] else 1), "score_tiebreak", True


def child_game_score(game: dict) -> float | None:
    """Map a valid score-race game to child win/draw/loss fitness."""
    if not game["valid"]:
        return None
    if game["decisive_reason"] == "score_draw" and game["winner"] is None:
        return 0.5
    if game["winner"] is None:
        return None
    return 1.0 if game["winner"] == game["child_owner"] else 0.0


def pair_score(games: list[dict]) -> float | None:
    """Return the mean child score for a complete two-role pair."""
    if len(games) != 2 or {game["child_owner"] for game in games} != {0, 1}:
        return None
    scores = [child_game_score(game) for game in games]
    return None if any(score is None for score in scores) else sum(scores) / 2.0


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
        actions.append({"actor": mover, "action": action_to_dict(decision.action), **event, "scores": list(scores)})
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
        valid = winner is not None and decisive_reason in {"score_threshold", "score_tiebreak", "checkmate", "perpetual_check", "declaration", "resignation"}
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
    opening = _opening_from_payload(payload["opening"])
    games = [
        play_score_race(
            compiled, opening, tuple(payload["champion"]), tuple(payload["child"]), owner,
            dict(payload["ordering_values"]), _limits(int(payload.get("max_nodes", 1000)))
        )
        for owner in (0, 1)
    ]
    paired_score = pair_score(games)
    return {
        "pair_index": opening.index,
        "opening_id": opening.final_position_key,
        "games": games,
        "valid": paired_score is not None,
        "pair_score": paired_score,
    }


def _payloads(openings, champion, child, ordering_values, max_nodes=1000):
    return [
        {"opening": _opening_payload(opening), "champion": list(champion), "child": list(child),
         "ordering_values": ordering_values, "max_nodes": max_nodes}
        for opening in openings
    ]


def _run_wave(openings, champion, child, ordering_values, workers, max_nodes=1000):
    payloads = _payloads(openings, champion, child, ordering_values, max_nodes)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_play_pair_task, payloads))


def run_pairs(champion, child, openings, ordering_values, workers=4, target_pairs=None, max_nodes=1000):
    target = len(openings) if target_pairs is None else target_pairs
    if len(openings) < target:
        raise ValueError("opening pool is smaller than target pair count")
    attempts = []
    valid_rows = []
    cursor = 0
    while len(valid_rows) < target and cursor < len(openings):
        wave_size = target if cursor == 0 else target - len(valid_rows)
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


def _percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    return float(ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))])


def summarize(result, bootstrap_seed):
    rows = result["rows"]
    pair_scores = [row["pair_score"] for row in rows]
    low, high = bootstrap_pair_mean_ci(pair_scores, seed=bootstrap_seed) if pair_scores else (0.0, 0.0)
    games = [game for row in rows for game in row["games"]]
    all_attempted_games = [game for row in result["attempts"] for game in row["games"]]
    causes = Counter(game["terminal_cause"] for game in all_attempted_games if not game["valid"])
    valid_plies = [game["plies"] for game in games]
    threshold_plies = [game["threshold_ply"] for game in all_attempted_games if game["decisive_reason"] == "score_threshold"]
    threshold_or_formal = sum(
        game["decisive_reason"] == "score_threshold"
        or game["decisive_reason"] in {"checkmate", "perpetual_check", "declaration", "resignation"}
        for game in all_attempted_games
    )
    scored_outcomes = sum(
        game["decisive_reason"] in {"score_threshold", "score_tiebreak", "checkmate", "perpetual_check", "declaration", "resignation"}
        for game in all_attempted_games
    )
    return {
        "attempted_pair_count": len(result["attempts"]),
        "valid_pair_count": len(rows),
        "invalid_pair_count": result["invalid_pairs"],
        "pair_count": len(rows),
        "pair_scores": pair_scores,
        "mean_pair_score": sum(pair_scores) / len(pair_scores) if pair_scores else 0.0,
        "bootstrap_95_ci": [low, high],
        "child_better_pairs": sum(score > 0.5 for score in pair_scores),
        "tied_pairs": sum(score == 0.5 for score in pair_scores),
        "child_worse_pairs": sum(score < 0.5 for score in pair_scores),
        "attempted_games": len(all_attempted_games),
        "valid_games": len(games),
        "threshold_winning_games": sum(game["decisive_reason"] == "score_threshold" for game in all_attempted_games),
        "formal_core_decisive_games": sum(game["decisive_reason"] in {"checkmate", "perpetual_check", "declaration", "resignation"} for game in all_attempted_games),
        "threshold_or_formal_decisive_fraction": threshold_or_formal / max(1, len(all_attempted_games)),
        "score_tiebreak_games": sum(game["decisive_reason"] == "score_tiebreak" for game in all_attempted_games),
        "scored_outcome_games": scored_outcomes,
        "scored_outcome_fraction": scored_outcomes / max(1, len(all_attempted_games)),
        "invalid_games": sum(not game["valid"] for game in all_attempted_games),
        "invalid_game_fraction": sum(not game["valid"] for game in all_attempted_games) / max(1, len(all_attempted_games)),
        "invalid_repetition_games": causes.get("repetition", 0),
        "invalid_terminal_causes": dict(sorted(causes.items())),
        "capture_points": sum(sum(game["capture_points"]) for game in all_attempted_games),
        "check_points": sum(sum(game["check_points"]) for game in all_attempted_games),
        "total_points": sum(game["total_points"] for game in all_attempted_games),
        "median_valid_game_plies": statistics.median(valid_plies) if valid_plies else 0.0,
        "p90_valid_game_plies": _percentile(valid_plies, 0.90),
        "max_valid_game_plies": max(valid_plies) if valid_plies else 0,
        "threshold_ply_distribution": {
            "count": len(threshold_plies),
            "values": threshold_plies,
            "median": statistics.median(threshold_plies) if threshold_plies else 0.0,
            "p90": _percentile(threshold_plies, 0.90),
            "max": max(threshold_plies) if threshold_plies else 0,
        },
    }


def _pool(compiled, seed, pairs):
    return generate_arena_openings(compiled, count=pairs * 4, seed=seed, min_plies=4, max_plies=12).openings


def _screen_shared(compiled, champion, mutants, ordering_values, seed, workers):
    pool = _pool(compiled, seed, 4)
    invalid_attempts = []
    for start in range(0, len(pool), 4):
        wave = pool[start : start + 4]
        if len(wave) < 4:
            break
        candidate_results = []
        all_valid = True
        for mutant_index, mutant in enumerate(mutants):
            raw = _run_wave(wave, champion, mutant, ordering_values, workers)
            candidate_results.append((mutant_index, mutant, raw))
            if not all(row["valid"] for row in raw):
                all_valid = False
        if all_valid:
            records = []
            for mutant_index, mutant, raw in candidate_results:
                result = {"rows": raw, "attempts": raw, "attempt_count": 4, "invalid_pairs": 0, "invalid_equal_score_games": 0}
                records.append({"mutant_index": mutant_index, "vector": _vector_record(mutant), "result": summarize(result, 1_463_000 + mutant_index), "rows": raw})
            return records, {"shared_opening_ids": [row["opening_id"] for row in candidate_results[0][2]], "invalid_attempts": invalid_attempts}
        for mutant_index, _, raw in candidate_results:
            invalid_attempts.extend({"mutant_index": mutant_index, "pair_index": row["pair_index"], "valid": row["valid"]} for row in raw if not row["valid"])
    raise RuntimeError("shared screening opening pool exhausted")


def _promotion(compiled, champion, child, ordering_values, seed, workers, generation):
    result = run_pairs(champion, child, _pool(compiled, seed, 24), ordering_values, workers=workers, target_pairs=24)
    return result, summarize(result, 1_464_000 + generation)


def _base_result(compiled, ordering_values, gen0, workers):
    return {
        "schema": "F146_SHOGI_MATERIAL_SCORE_RACE_V2",
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "type_ids": list(TYPE_IDS),
        "score_race": {"threshold": 3, "capture_points": 1, "check_points": 1, "capture_plus_check_points": 2, "safety_max_plies": 512, "score_independent_of_material_values": True},
        "search": {"max_nodes": 1000, "max_depth": 12, "qdepth": [4, 8], "tt_max_entries": TT_MAX_ENTRIES, "tuning": "SearchTuning()", "fixed_ordering_values": ordering_values, "fixed_ordering_sha256": _sha(ordering_values), "process_workers": workers},
        "f145_reproduction": {"material_evaluator": "F144 MaterialOnlyEvaluator", "gen0_seed": GEN0_SEED, "gen0_vector": list(gen0), "gen0_vector_sha256": _vector_record(gen0)["sha256"], "score_event_source_confirmation": "score_event reads only position/action/compiled/mover; no material vector input", "score_event_source_sha256": hashlib.sha256(inspect.getsource(score_event).encode()).hexdigest()},
    }


def run(*, output: Path, workers: int = 4, pilot_only: bool = False) -> dict:
    compiled = _compile()
    ordering_values = _ordering_values(compiled)
    gen0 = gen0_vector(GEN0_SEED)
    if tuple(gen0) != (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240):
        raise RuntimeError("Gen0 vector parity failure")
    pilot_run = run_pairs(gen0, gen0, _pool(compiled, PILOT_SEED, 4), ordering_values, workers=workers, target_pairs=4)
    pilot = summarize(pilot_run, 1_466_001)
    pilot["self_pair_mean_exactly_half"] = pilot["mean_pair_score"] == 0.5
    pilot["acceptance"] = (
        pilot["valid_pair_count"] == 4
        and pilot["threshold_or_formal_decisive_fraction"] >= 0.80
        and pilot["invalid_game_fraction"] < 0.20
        and pilot["median_valid_game_plies"] < 200
        and pilot["self_pair_mean_exactly_half"]
    )
    base = _base_result(compiled, ordering_values, gen0, workers)
    base.update({"gen0": {"seed": GEN0_SEED, "vector": _vector_record(gen0), "sanity": _sanity(gen0)}, "pilot": pilot, "pilot_rows": pilot_run["rows"], "pilot_only": pilot_only})
    if pilot_only or not pilot["acceptance"]:
        base["classification"] = "SCORE_RACE_THRESHOLD3_PILOT_ACCEPTED" if pilot["acceptance"] else "SCORE_RACE_THRESHOLD3_PILOT_FAILED_ACCEPTANCE"
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
        generations.append({"generation": generation, "parent": _vector_record(champion), "mutants": screening, "screening_meta": screening_meta, "selected_mutant_index": selected["mutant_index"], "selected": _vector_record(selected_vector), "promotion": promotion, "promotion_rows": promotion_run["rows"], "promoted": passed})
        if not passed:
            break
        champion = selected_vector
    if not generations or not generations[0]["promoted"]:
        classification = "MATERIAL_ONLY_SCORE_RACE_GEN1_DOES_NOT_BEAT_GEN0"
    elif len(generations) < 2 or not generations[1]["promoted"]:
        classification = "MATERIAL_ONLY_SCORE_RACE_GEN1_PASSES_GEN2_DOES_NOT_BEAT_GEN1"
    else:
        classification = "MATERIAL_ONLY_SCORE_RACE_GEN1_GEN2_IMPROVEMENT_ESTABLISHED"
    base.update({"classification": classification, "generations": generations, "final_champion": _vector_record(champion), "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()})
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
