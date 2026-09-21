"""F145: Standard Shogi material-only score-race Arena.

This keeps F144's evaluator and search path fixed.  Arena games are adjudicated
by deterministic, evaluator-independent capture/check events so that a game
produces a useful fitness signal before ordinary Shogi repetition dominates.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import hashlib
import json
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import (
    action_from_dict,
    action_target_square,
    action_to_dict,
)
from generic_chess.core.attacks import is_in_check
from generic_chess.core.coordinates import square_to_index
from generic_chess.learning.openings import ArenaOpening, generate_arena_openings
from generic_chess.learning.statistics import bootstrap_pair_mean_ci
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus

from scripts.f144_shogi_material_only_arena_evolution import (
    GEN0_SEED,
    MUTATION_BASE_SEED,
    TYPE_IDS,
    MaterialOnlyEvaluator,
    _ordering_values,
    _player,
    _sanity,
    _sha,
    _vector_record,
    canonicalize_vector,
    gen0_vector,
    mutate_vectors,
)

ROOT = Path(__file__).resolve().parents[1]
SCORE_THRESHOLD = 10
SAFETY_MAX_PLIES = 512
TT_MAX_ENTRIES = 250_000
SEARCH_LIMITS = SearchLimits(
    max_nodes=1000,
    max_depth=12,
    quiescence_max_depth=4,
    quiescence_hard_max_depth=8,
    deterministic=True,
)
SCREENING_SEEDS = {1: 1_451_001, 2: 1_451_002}
PROMOTION_SEEDS = {1: 1_452_001, 2: 1_452_002}


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


def _limits(max_nodes: int) -> SearchLimits:
    return SearchLimits(
        max_nodes=max_nodes,
        max_depth=12,
        quiescence_max_depth=4,
        quiescence_hard_max_depth=8,
        deterministic=True,
    )


def score_event(before_position, action, after_position, mover: int, compiled) -> dict:
    """Return evaluator-independent capture/check points for one legal move."""
    target = action_target_square(action)
    captured = before_position.board[square_to_index(target, compiled.board_size)]
    capture = int(
        captured is not None
        and captured.owner != mover
        and not compiled.types_by_id[captured.current_type_id].is_anchor
    )
    gave_check = int(is_in_check(after_position, 1 - mover, compiled))
    return {
        "capture": capture,
        "check": gave_check,
        "points": capture + gave_check,
    }


def _core_winner(result) -> bool:
    return result.status in {
        SessionStatus.CHECKMATE,
        SessionStatus.PERPETUAL_CHECK,
        SessionStatus.DECLARATION,
        SessionStatus.RESIGNATION,
    } and result.winner is not None


def _finish_formal(result, scores: list[int]) -> tuple[int | None, str, bool]:
    if scores[0] == scores[1]:
        return None, "invalid_equal_score_terminal", False
    return (0 if scores[0] > scores[1] else 1), "score_tiebreak", True


def play_score_race(
    compiled,
    opening: ArenaOpening,
    champion: tuple[int, ...],
    child: tuple[int, ...],
    child_owner: int,
    ordering_values: dict[str, int],
    limits: SearchLimits = SEARCH_LIMITS,
) -> dict:
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
    threshold_ply = None
    terminal_cause = "ongoing"
    decisive_reason = ""
    winner = None

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
        actions.append(
            {
                "actor": mover,
                "action": action_to_dict(decision.action),
                **event,
                "scores": list(scores),
            }
        )
        result = session.result
        if _core_winner(result):
            winner = result.winner
            decisive_reason = result.status.value
            terminal_cause = result.status.value
            break
        if scores[mover] >= SCORE_THRESHOLD:
            winner = mover
            decisive_reason = "score_threshold"
            terminal_cause = "score_threshold"
            threshold_ply = len(session.history)
            break

    result = session.result
    if winner is None and decisive_reason == "":
        terminal_cause = result.status.value if result.status is not SessionStatus.ONGOING else "max_ply"
        winner, decisive_reason, valid = _finish_formal(result, scores)
    else:
        valid = True
    return {
        "child_owner": child_owner,
        "winner": winner,
        "result": "invalid_equal_score_terminal" if not valid else decisive_reason,
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
            compiled,
            opening,
            tuple(payload["champion"]),
            tuple(payload["child"]),
            owner,
            dict(payload["ordering_values"]),
            _limits(int(payload.get("max_nodes", SEARCH_LIMITS.max_nodes))),
        )
        for owner in (0, 1)
    ]
    scores = [
        None if not game["valid"] else (1.0 if game["winner"] == game["child_owner"] else 0.0)
        for game in games
    ]
    return {
        "pair_index": opening.index,
        "opening_id": opening.final_position_key,
        "games": games,
        "valid": all(game["valid"] for game in games),
        "pair_score": None if any(score is None for score in scores) else sum(scores) / 2.0,
    }


def run_pairs(
    champion: tuple[int, ...],
    child: tuple[int, ...],
    openings: tuple[ArenaOpening, ...],
    ordering_values: dict[str, int],
    workers: int = 4,
    target_pairs: int | None = None,
    max_nodes: int = SEARCH_LIMITS.max_nodes,
) -> dict:
    target = len(openings) if target_pairs is None else target_pairs
    payloads = [
        {
            "opening": _opening_payload(opening),
            "champion": list(champion),
            "child": list(child),
            "ordering_values": ordering_values,
            "max_nodes": max_nodes,
        }
        for opening in openings
    ]
    if len(payloads) < target:
        raise ValueError("opening pool is smaller than target pair count")
    attempts = []
    valid_rows = []
    cursor = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        while len(valid_rows) < target and cursor < len(payloads):
            wave_size = target if cursor == 0 else target - len(valid_rows)
            wave = payloads[cursor : cursor + wave_size]
            cursor += len(wave)
            wave_rows = list(pool.map(_play_pair_task, wave))
            attempts.extend(wave_rows)
            valid_rows.extend(row for row in wave_rows if row["valid"])
    valid_rows = sorted(valid_rows, key=lambda row: row["pair_index"])
    if len(valid_rows) < target:
        raise RuntimeError(
            f"fresh opening pool exhausted: target={target}, valid={len(valid_rows)}, attempts={len(attempts)}"
        )
    return {
        "rows": valid_rows[:target],
        "attempt_count": len(attempts),
        "invalid_equal_score_games": sum(
            not game["valid"] for row in attempts for game in row["games"]
        ),
        "invalid_equal_score_pairs": sum(not row["valid"] for row in attempts),
    }


def _percentile(values: list[int], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * fraction)))
    return float(ordered[index])


def summarize(result: dict, *, bootstrap_seed: int) -> dict:
    rows = result["rows"]
    pair_scores = [row["pair_score"] for row in rows]
    low, high = bootstrap_pair_mean_ci(pair_scores, seed=bootstrap_seed)
    games = [game for row in rows for game in row["games"]]
    terminal = Counter(game["terminal_cause"] for game in games)
    accepted = sum(
        game["decisive_reason"] == "score_threshold"
        or game["decisive_reason"] in {"checkmate", "perpetual_check", "declaration", "resignation"}
        for game in games
    )
    plies = [game["plies"] for game in games]
    return {
        "pair_count": len(rows),
        "pair_scores": pair_scores,
        "mean_pair_score": sum(pair_scores) / len(pair_scores),
        "child_better_pairs": sum(score > 0.5 for score in pair_scores),
        "tied_pairs": sum(score == 0.5 for score in pair_scores),
        "child_worse_pairs": sum(score < 0.5 for score in pair_scores),
        "bootstrap_95_ci": [low, high],
        "attempt_count": result["attempt_count"],
        "invalid_equal_score_games": result["invalid_equal_score_games"],
        "invalid_equal_score_fraction": result["invalid_equal_score_games"] / max(1, 2 * result["attempt_count"]),
        "valid_games": len(games),
        "score_threshold_games": sum(game["decisive_reason"] == "score_threshold" for game in games),
        "formal_decisive_games": accepted - sum(game["decisive_reason"] == "score_threshold" for game in games),
        "accepted_signal_fraction": accepted / max(1, len(games)),
        "terminal_causes": dict(sorted(terminal.items())),
        "capture_points": sum(sum(game["capture_points"]) for game in games),
        "check_points": sum(sum(game["check_points"]) for game in games),
        "total_points": sum(game["total_points"] for game in games),
        "median_plies": statistics.median(plies),
        "p90_plies": _percentile(plies, 0.90),
        "max_plies": max(plies),
        "median_shortness_threshold": 250,
        "median_shortness_pass": statistics.median(plies) < 250,
        "valid_for_promotion": accepted / max(1, len(games)) >= 0.80
        and result["invalid_equal_score_games"] / max(1, 2 * result["attempt_count"]) < 0.10
        and statistics.median(plies) < 250,
    }


def _opening_pool(compiled, *, seed: int, pairs: int):
    return generate_arena_openings(
        compiled,
        count=pairs * 4,
        seed=seed,
        min_plies=4,
        max_plies=12,
    ).openings


def _run_batch(compiled, champion, child, ordering_values, *, seed: int, pairs: int, workers: int, bootstrap_seed: int):
    result = run_pairs(
        champion,
        child,
        _opening_pool(compiled, seed=seed, pairs=pairs),
        ordering_values,
        workers=workers,
        target_pairs=pairs,
    )
    return result, summarize(result, bootstrap_seed=bootstrap_seed)


def _run_promotion(compiled, champion, child, ordering_values, *, seed: int, workers: int, generation: int):
    all_rows = []
    attempts = invalid_games = 0
    batches = []
    for batch_index, batch_pairs in enumerate((8, 8, 8, 8), start=1):
        result = run_pairs(
            champion,
            child,
            _opening_pool(compiled, seed=seed + batch_index, pairs=batch_pairs),
            ordering_values,
            workers=workers,
            target_pairs=batch_pairs,
        )
        all_rows.extend(result["rows"])
        attempts += result["attempt_count"]
        invalid_games += result["invalid_equal_score_games"]
        aggregate = summarize(
            {"rows": all_rows, "attempt_count": attempts, "invalid_equal_score_games": invalid_games},
            bootstrap_seed=1_454_000 + generation * 100 + batch_index,
        )
        batches.append({"batch": batch_index, "pairs_added": batch_pairs, "summary": aggregate})
        if aggregate["bootstrap_95_ci"][0] > 0.5:
            break
    return batches, {"rows": all_rows, "attempt_count": attempts, "invalid_equal_score_games": invalid_games}


def run(*, output: Path, workers: int = 4, pilot_pairs: int = 2, pilot_only: bool = False) -> dict:
    compiled = _compile()
    ordering_values = _ordering_values(compiled)
    gen0 = gen0_vector(GEN0_SEED)
    pilot_result, pilot = _run_batch(
        compiled,
        gen0,
        gen0,
        ordering_values,
        seed=1_450_001,
        pairs=pilot_pairs,
        workers=workers,
        bootstrap_seed=1_450_101,
    )
    if pilot_only:
        result = {
            "schema": "F145_SHOGI_MATERIAL_SCORE_RACE_V1",
            "classification": "SCORE_RACE_PILOT_ACCEPTED" if pilot["valid_for_promotion"] else "SCORE_RACE_PILOT_FAILED_ACCEPTANCE",
            "pilot_only": True,
            "score_race": {
                "threshold": SCORE_THRESHOLD,
                "safety_max_plies": SAFETY_MAX_PLIES,
                "capture_points": 1,
                "check_points": 1,
                "capture_plus_check_points": 2,
                "score_independent_of_material_values": True,
            },
            "pilot": pilot,
            "pilot_rows": pilot_result["rows"],
        }
        output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        return result
    if not pilot["valid_for_promotion"]:
        result = {
            "schema": "F145_SHOGI_MATERIAL_SCORE_RACE_V1",
            "classification": "SCORE_RACE_PILOT_FAILED_ACCEPTANCE",
            "pilot": pilot,
            "pilot_rows": pilot_result["rows"],
        }
        output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        return result

    champion = gen0
    generations = []
    for generation in (1, 2):
        mutants = mutate_vectors(champion, generation)
        screening = []
        for mutant_index, mutant in enumerate(mutants):
            _, record = _run_batch(
                compiled,
                champion,
                mutant,
                ordering_values,
                seed=SCREENING_SEEDS[generation] + mutant_index,
                pairs=4,
                workers=workers,
                bootstrap_seed=1_453_000 + generation * 10 + mutant_index,
            )
            screening.append({"mutant_index": mutant_index, "vector": _vector_record(mutant), "result": record})
        selected = max(screening, key=lambda row: (row["result"]["mean_pair_score"], row["result"]["child_better_pairs"], -row["mutant_index"]))
        selected_vector = tuple(selected["vector"]["values"])
        batches, promotion_result = _run_promotion(
            compiled,
            champion,
            selected_vector,
            ordering_values,
            seed=PROMOTION_SEEDS[generation],
            workers=workers,
            generation=generation,
        )
        promotion = batches[-1]["summary"]
        passed = promotion["mean_pair_score"] > 0.5 and promotion["bootstrap_95_ci"][0] > 0.5
        generations.append({
            "generation": generation,
            "parent": _vector_record(champion),
            "mutants": screening,
            "selected_mutant_index": selected["mutant_index"],
            "selected": _vector_record(selected_vector),
            "promotion_batches": batches,
            "promotion": promotion,
            "promoted": passed,
        })
        if not passed:
            break
        champion = selected_vector

    classification = (
        "MATERIAL_ONLY_SCORE_RACE_GEN1_GEN2_IMPROVEMENT_ESTABLISHED"
        if len(generations) == 2 and all(row["promoted"] for row in generations)
        else "MATERIAL_ONLY_SCORE_RACE_GEN1_DOES_NOT_BEAT_GEN0"
        if not generations or not generations[0]["promoted"]
        else "MATERIAL_ONLY_SCORE_RACE_GEN2_DOES_NOT_BEAT_GEN1"
    )
    result = {
        "schema": "F145_SHOGI_MATERIAL_SCORE_RACE_V1",
        "classification": classification,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "type_ids": list(TYPE_IDS),
        "score_race": {
            "threshold": SCORE_THRESHOLD,
            "safety_max_plies": SAFETY_MAX_PLIES,
            "capture_points": 1,
            "check_points": 1,
            "capture_plus_check_points": 2,
            "score_independent_of_material_values": True,
        },
        "search": {
            "max_nodes": SEARCH_LIMITS.max_nodes,
            "max_depth": SEARCH_LIMITS.max_depth,
            "quiescence_max_depth": SEARCH_LIMITS.quiescence_max_depth,
            "quiescence_hard_max_depth": SEARCH_LIMITS.quiescence_hard_max_depth,
            "tt_max_entries": TT_MAX_ENTRIES,
            "tuning": "SearchTuning()",
            "fixed_ordering_values": ordering_values,
            "fixed_ordering_sha256": _sha(ordering_values),
            "process_workers": workers,
        },
        "gen0": {"seed": GEN0_SEED, "vector": _vector_record(gen0), "sanity": _sanity(gen0)},
        "pilot": pilot,
        "generations": generations,
        "final_champion": _vector_record(champion),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--pilot-pairs", type=int, default=2)
    parser.add_argument("--pilot-only", action="store_true")
    args = parser.parse_args()
    result = run(output=args.output, workers=args.workers, pilot_pairs=args.pilot_pairs, pilot_only=args.pilot_only)
    print(json.dumps({"classification": result["classification"], "generations": len(result.get("generations", ()))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
