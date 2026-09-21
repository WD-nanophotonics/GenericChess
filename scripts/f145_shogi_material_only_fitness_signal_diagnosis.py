"""F145: diagnose the flat F144 material-only Arena fitness signal.

This diagnostic keeps the F144 material evaluator, frozen ordering, and ABP
search path unchanged.  It probes mutation amplitude, action leverage,
terminal outcomes, search budget, and opening depth using actual paired games.
Process workers are only an execution detail; every result is sorted by its
deterministic position/opening identity before it is summarized.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import json
import math
import statistics
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.learning.openings import ArenaOpening, generate_arena_openings
from generic_chess.learning.serialization import stable_sha256
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.session.session import GameSession

from scripts.f144_shogi_material_only_arena_evolution import (
    GEN0_SEED,
    TYPE_IDS,
    MaterialOnlyEvaluator,
    _ordering_values,
    _player,
    _sha,
    canonicalize_vector,
    gen0_vector,
)

ROOT = Path(__file__).resolve().parents[1]
MUTANT0_SEED = 1_440_401
DIAGNOSTIC_VECTORS = {
    "M035": 0.35,
    "M070": 0.70,
    "M140": 1.40,
}
DEFAULT_WORKERS = 4


def _mutate_once(champion: tuple[int, ...], seed: int, sigma: float) -> tuple[int, ...]:
    import random

    rng = random.Random(seed)
    return canonicalize_vector(
        value * math.exp(sigma * rng.gauss(0.0, 1.0)) for value in champion
    )


def diagnostic_vectors() -> dict[str, tuple[int, ...]]:
    gen0 = gen0_vector(GEN0_SEED)
    return {
        "Gen0": gen0,
        **{
            label: _mutate_once(gen0, MUTANT0_SEED, sigma)
            for label, sigma in DIAGNOSTIC_VECTORS.items()
        },
    }


def _vector_record(values: tuple[int, ...]) -> dict:
    return {
        "type_ids": list(TYPE_IDS),
        "values": list(values),
        "sha256": _sha(dict(zip(TYPE_IDS, values))),
    }


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


def _limits(max_nodes: int) -> SearchLimits:
    return SearchLimits(
        max_nodes=max_nodes,
        max_depth=12,
        quiescence_max_depth=4,
        quiescence_hard_max_depth=8,
        deterministic=True,
    )


def _compile():
    return compile_ruleset_for_execution(build_standard_shogi_ruleset())


def _play_game_task(payload: dict) -> dict:
    compiled = _compile()
    opening = _opening_from_payload(payload["opening"])
    champion = tuple(payload["champion"])
    child = tuple(payload["child"])
    ordering_values = dict(payload["ordering_values"])
    child_owner = int(payload["child_owner"])
    limits = _limits(int(payload["max_nodes"]))
    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    players = (
        _player(compiled, child if child_owner == 0 else champion, ordering_values),
        _player(compiled, child if child_owner == 1 else champion, ordering_values),
    )
    while session.result.status.value == "ongoing":
        side = session.state.position.side_to_move
        decision = players[side].choose_action(session, limits)
        if decision.declaration is not None:
            session.declare(decision.declaration)
            break
        if decision.action is None:
            raise RuntimeError(
                f"ongoing game returned no action: {decision.termination_reason}"
            )
        if decision.action not in session.legal_actions():
            raise RuntimeError("AlphaBeta returned an illegal action")
        session.submit(decision.action)
    result = session.result
    return {
        "child_owner": child_owner,
        "winner": result.winner,
        "result": result.status.value,
        "plies": len(session.history),
    }


def _run_pair_task(payload: dict) -> dict:
    games = [
        _play_game_task({**payload, "child_owner": child_owner})
        for child_owner in (0, 1)
    ]
    scores = []
    for game in games:
        if game["result"] == "no_contest":
            scores.append(None)
        elif game["winner"] is None:
            scores.append(0.5)
        else:
            scores.append(1.0 if game["winner"] == game["child_owner"] else 0.0)
    pair_score = None if any(score is None for score in scores) else sum(scores) / 2.0
    return {
        "pair_index": int(payload["opening"]["index"]),
        "opening_id": payload["opening"]["final_position_key"],
        "games": games,
        "pair_score": pair_score,
    }


def _run_tasks(tasks: list[dict], workers: int) -> list[dict]:
    if not tasks:
        return []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(_run_pair_task, tasks))
    return sorted(rows, key=lambda row: row["pair_index"])


def run_pairs(
    champion: tuple[int, ...],
    child: tuple[int, ...],
    openings: tuple[ArenaOpening, ...],
    ordering_values: dict[str, int],
    max_nodes: int,
    workers: int,
) -> list[dict]:
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
    return _run_tasks(payloads, workers)


def _percentile(values: list[int], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))
    return float(ordered[index])


def summarize_pairs(rows: list[dict]) -> dict:
    games = [game for row in rows for game in row["games"]]
    scores = [row["pair_score"] for row in rows if row["pair_score"] is not None]
    terminal_status = Counter(game["result"] for game in games)
    plies = [int(game["plies"]) for game in games]
    wins = sum(game["winner"] is not None for game in games)
    child_wins = sum(
        game["winner"] is not None and game["winner"] == game["child_owner"]
        for game in games
    )
    child_losses = wins - child_wins
    scoring_draws = sum(
        game["winner"] is None and game["result"] != "no_contest"
        for game in games
    )
    return {
        "pair_count": len(scores),
        "pair_scores": [row["pair_score"] for row in rows],
        "scoring_pair_scores": scores,
        "non_scoring_pair_count": len(rows) - len(scores),
        "mean_pair_score": sum(scores) / len(scores) if scores else 0.0,
        "non_0_5_scoring_pair_count": sum(score != 0.5 for score in scores),
        "wins": child_wins,
        "losses": child_losses,
        "scoring_draws": scoring_draws,
        "no_contests": terminal_status["no_contest"],
        "terminal_status_histogram": dict(sorted(terminal_status.items())),
        "mean_game_plies": statistics.mean(plies) if plies else 0.0,
        "median_game_plies": statistics.median(plies) if plies else 0.0,
        "p90_game_plies": _percentile(plies, 0.9),
        "max_game_plies": max(plies) if plies else 0,
        "game_count": len(games),
        "game_status_fractions": {
            status: count / len(games) for status, count in sorted(terminal_status.items())
        } if games else {},
        "games_reaching_plies": {
            str(threshold): sum(ply >= threshold for ply in plies) / len(plies)
            for threshold in (100, 200, 400)
        } if plies else {"100": 0.0, "200": 0.0, "400": 0.0},
    }


def _decision_task(payload: dict) -> dict:
    compiled = _compile()
    opening = _opening_from_payload(payload["opening"])
    ordering_values = dict(payload["ordering_values"])
    vectors = {label: tuple(values) for label, values in payload["vectors"].items()}
    limits = _limits(int(payload["max_nodes"]))
    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    decisions = {}
    for label, vector in vectors.items():
        player = _player(compiled, vector, ordering_values)
        decision = player.choose_action(session, limits)
        decisions[label] = {
            "action": action_to_dict(decision.action) if decision.action is not None else None,
            "score": decision.score,
            "completed_depth": decision.completed_depth,
            "nodes": decision.nodes,
            "qnodes": decision.qnodes,
            "node_count": decision.nodes + decision.qnodes,
            "termination_reason": decision.termination_reason,
        }
    return {
        "position_index": opening.index,
        "position_id": opening.final_position_key,
        "target_plies": opening.target_plies,
        "decisions": decisions,
    }


def decision_probe(
    vectors: dict[str, tuple[int, ...]],
    openings: tuple[ArenaOpening, ...],
    ordering_values: dict[str, int],
    max_nodes: int,
    workers: int,
) -> dict:
    payloads = [
        {
            "opening": _opening_payload(opening),
            "vectors": {label: list(vector) for label, vector in vectors.items()},
            "ordering_values": ordering_values,
            "max_nodes": max_nodes,
        }
        for opening in openings
    ]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = sorted(pool.map(_decision_task, payloads), key=lambda row: row["position_index"])
    comparisons = {}
    for label in ("M035", "M070", "M140"):
        action_differences = []
        score_differences = []
        node_differences = []
        completed_depths = []
        same_actions = 0
        same_nodes = 0
        first_difference = None
        for row in rows:
            base = row["decisions"]["Gen0"]
            mutant = row["decisions"][label]
            same_action = mutant["action"] == base["action"]
            same_node = mutant["node_count"] == base["node_count"]
            if same_action:
                same_actions += 1
            elif first_difference is None:
                first_difference = row["position_id"]
            if same_node:
                same_nodes += 1
            action_differences.append(not same_action)
            score_differences.append(mutant["score"] - base["score"])
            node_differences.append(mutant["node_count"] - base["node_count"])
            completed_depths.append(mutant["completed_depth"])
        comparisons[label] = {
            "position_count": len(rows),
            "best_action_disagreement_count": sum(action_differences),
            "best_action_disagreement_rate": sum(action_differences) / len(rows),
            "exact_same_action_count": same_actions,
            "score_difference_distribution": {
                "min": min(score_differences),
                "median": statistics.median(score_differences),
                "max": max(score_differences),
                "values": score_differences,
            },
            "completed_depth_distribution": dict(sorted(Counter(completed_depths).items())),
            "node_count_parity": {
                "exact_same_count": same_nodes,
                "exact_same_rate": same_nodes / len(rows),
                "differences": node_differences,
            },
            "first_position_id_where_action_differs": first_difference,
        }
    return {"max_nodes": max_nodes, "positions": rows, "comparisons": comparisons}


def _cell(
    name: str,
    champion: tuple[int, ...],
    child: tuple[int, ...],
    openings: tuple[ArenaOpening, ...],
    ordering_values: dict[str, int],
    max_nodes: int,
    workers: int,
) -> dict:
    rows = run_pairs(champion, child, openings, ordering_values, max_nodes, workers)
    return {
        "name": name,
        "opening_seed": openings[0].opening_seed // 1000 if openings else None,
        "opening_count": len(openings),
        "max_nodes": max_nodes,
        "rows": rows,
        "summary": summarize_pairs(rows),
    }


def _decisive(cell: dict) -> bool:
    summary = cell["summary"]
    return bool(summary["wins"] or summary["losses"]) and bool(summary["non_0_5_scoring_pair_count"])


def _classification(
    baseline_decisive: bool,
    search_decisive: bool,
    deeper_decisive: bool,
    probes: dict,
) -> str:
    if baseline_decisive:
        return "MATERIAL_ONLY_F144_FAILURE_MUTATION_SIGNAL_TOO_WEAK"
    if search_decisive:
        return "MATERIAL_ONLY_F144_FAILURE_SEARCH_BUDGET_TOO_SHALLOW"
    if deeper_decisive:
        return "MATERIAL_ONLY_F144_FAILURE_OPENING_DISTRIBUTION_TOO_QUIET"
    m140_rates = [
        probes[str(max_nodes)]["comparisons"]["M140"]["best_action_disagreement_rate"]
        for max_nodes in (1000, 4000)
        if str(max_nodes) in probes
    ]
    if any(rate >= 0.20 for rate in m140_rates):
        return "MATERIAL_ONLY_DECISIONS_CHANGE_BUT_STRENGTH_SIGNAL_DOES_NOT_CONVERT"
    if len(m140_rates) == 2 and all(rate < 0.05 for rate in m140_rates):
        return "MATERIAL_ONLY_EVALUATOR_HAS_INSUFFICIENT_ABP_DECISION_LEVERAGE"
    return "MATERIAL_ONLY_ZERO_FITNESS_SIGNAL_CAUSE_UNRESOLVED"


def run(*, output: Path, workers: int = DEFAULT_WORKERS) -> dict:
    compiled = _compile()
    ordering_values = _ordering_values(compiled)
    vectors = diagnostic_vectors()
    expected_m035_sha = "23ac030713751c7e29afd424d690dd72bf87d6ca98cedde5929730e00d3588fe"
    if _vector_record(vectors["M035"])["sha256"] != expected_m035_sha:
        raise RuntimeError("F144 M035 vector SHA parity failure")

    baseline_openings = generate_arena_openings(
        compiled, count=4, seed=1_450_001, min_plies=4, max_plies=12
    ).openings
    baseline = _cell(
        "baseline_gen0_vs_m035",
        vectors["Gen0"],
        vectors["M035"],
        baseline_openings,
        ordering_values,
        1000,
        workers,
    )

    probe_openings = generate_arena_openings(
        compiled, count=32, seed=1_450_101, min_plies=4, max_plies=20
    ).openings
    probes = {}
    for max_nodes in (1000, 4000):
        probes[str(max_nodes)] = decision_probe(
            vectors, probe_openings, ordering_values, max_nodes, workers
        )

    mutation_openings = generate_arena_openings(
        compiled, count=8, seed=1_451_001, min_plies=4, max_plies=12
    ).openings
    mutation_scale = {
        label: _cell(
            f"gen0_vs_{label.lower()}_mutation_scale",
            vectors["Gen0"],
            vectors[label],
            mutation_openings,
            ordering_values,
            1000,
            workers,
        )
        for label in ("M035", "M070", "M140")
    }
    baseline_decisive = any(_decisive(cell) for cell in mutation_scale.values())

    search_budget = None
    search_decisive = False
    if not baseline_decisive:
        search_budget = _cell(
            "gen0_vs_m140_search_budget",
            vectors["Gen0"],
            vectors["M140"],
            mutation_openings,
            ordering_values,
            4000,
            workers,
        )
        search_decisive = _decisive(search_budget)

    deeper_opening = None
    deeper_decisive = False
    if not baseline_decisive and not search_decisive:
        deeper_openings = generate_arena_openings(
            compiled, count=8, seed=1_451_002, min_plies=16, max_plies=32
        ).openings
        deeper_opening = _cell(
            "gen0_vs_m140_deeper_opening",
            vectors["Gen0"],
            vectors["M140"],
            deeper_openings,
            ordering_values,
            4000,
            workers,
        )
        deeper_decisive = _decisive(deeper_opening)

    classification = _classification(
        baseline_decisive,
        search_decisive,
        deeper_decisive,
        probes,
    )
    result = {
        "schema": "F145_SHOGI_MATERIAL_ONLY_FITNESS_SIGNAL_DIAGNOSIS_V1",
        "classification": classification,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "type_ids": list(TYPE_IDS),
        "f144_integrity_reference": {
            "git_sha": "cb1f93d035f0584db6215602b561afd9362be18c",
            "classification": "F144_PAIRED_ARENA_INTEGRITY_PASS",
        },
        "search": {
            "max_nodes": [1000, 4000],
            "max_depth": 12,
            "quiescence_max_depth": 4,
            "quiescence_hard_max_depth": 8,
            "tt_max_entries": 250000,
            "tuning": "SearchTuning()",
            "fresh_player_per_search": True,
            "fixed_ordering_values": ordering_values,
            "fixed_ordering_sha256": _sha(ordering_values),
        },
        "vectors": {label: _vector_record(vector) for label, vector in vectors.items()},
        "vector_contract": {
            "gen0_seed": GEN0_SEED,
            "mutation_seed": MUTANT0_SEED,
            "sigmas": DIAGNOSTIC_VECTORS,
            "m035_sha_parity_required": expected_m035_sha,
        },
        "baseline_sanity": baseline,
        "decision_probe": probes,
        "mutation_scale": mutation_scale,
        "baseline_decisive_signal": baseline_decisive,
        "search_budget": search_budget,
        "search_budget_decisive_signal": search_decisive,
        "deeper_opening": deeper_opening,
        "deeper_opening_decisive_signal": deeper_decisive,
        "routing": {
            "mutation_scale_cells": ["M035", "M070", "M140"],
            "search_budget_executed": search_budget is not None,
            "deeper_opening_executed": deeper_opening is not None,
        },
        "source_sha256": stable_sha256(Path(__file__).read_text(encoding="utf-8")),
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()
    result = run(output=args.output, workers=args.workers)
    print(json.dumps({"classification": result["classification"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
