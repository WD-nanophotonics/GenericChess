"""F144: Standard Shogi material-only self-improvement by paired Arena games.

The benchmark deliberately keeps the existing AlphaBeta search path fixed and
changes only the leaf evaluator.  It is a small, interpretable evolution
strategy whose only selection signal is fresh paired game score.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import json
import math
import random
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.learning.openings import ArenaOpening, generate_arena_openings
from generic_chess.learning.serialization import stable_sha256
from generic_chess.learning.statistics import bootstrap_pair_mean_ci
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.session.session import GameSession

ROOT = Path(__file__).resolve().parents[1]
TYPE_IDS = ("P", "L", "N", "S", "G", "B", "R", "TP", "TL", "TN", "TS", "TB", "TR")
GEN0_SEED = 1_440_201
MUTATION_BASE_SEED = 1_440_301
SCREENING_SEEDS = {1: 1_441_001, 2: 1_441_002, 3: 1_441_003}
PROMOTION_SEEDS = {1: 1_442_001, 2: 1_442_002, 3: 1_442_003}
SEARCH_LIMITS = SearchLimits(
    max_nodes=1000,
    max_depth=12,
    quiescence_max_depth=4,
    quiescence_hard_max_depth=8,
    deterministic=True,
)
TT_MAX_ENTRIES = 250_000


def _sha(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _median(values: Iterable[int]) -> float:
    return statistics.median(tuple(values))


def canonicalize_vector(values: Iterable[float | int]) -> tuple[int, ...]:
    """Apply the fixed positive median gauge exactly once plus one repair pass."""
    raw = tuple(float(value) for value in values)
    if len(raw) != len(TYPE_IDS) or any(not math.isfinite(value) or value <= 0 for value in raw):
        raise ValueError("material vector must contain 13 finite positive values")

    def normalize(current: tuple[float, ...]) -> tuple[int, ...]:
        median = _median(current)
        return tuple(max(1, int(round(value * 1000.0 / median))) for value in current)

    first = normalize(raw)
    if _median(first) != 1000:
        return normalize(tuple(float(value) for value in first))
    return first


def gen0_vector(seed: int = GEN0_SEED) -> tuple[int, ...]:
    rng = random.Random(seed)
    raw = tuple(math.exp(rng.uniform(math.log(250), math.log(4000))) for _ in TYPE_IDS)
    return canonicalize_vector(raw)


def mutate_vectors(champion: tuple[int, ...], generation: int) -> tuple[tuple[int, ...], ...]:
    if len(champion) != len(TYPE_IDS):
        raise ValueError("champion must contain 13 values")
    result: list[tuple[int, ...]] = []
    used = {tuple(champion)}
    for candidate_index in range(6):
        rng = random.Random(MUTATION_BASE_SEED + 100 * generation + candidate_index)
        while True:
            candidate = canonicalize_vector(
                value * math.exp(0.35 * rng.gauss(0.0, 1.0)) for value in champion
            )
            if candidate not in used:
                used.add(candidate)
                result.append(candidate)
                break
    return tuple(result)


class MaterialOnlyEvaluator:
    """F144 leaf evaluator with immutable rule-derived ordering values."""

    __slots__ = ("_values", "_ordering_values")

    def __init__(self, values: tuple[int, ...], ordering_values: dict[str, int]):
        if tuple(values) != canonicalize_vector(values):
            raise ValueError("material values must be canonical positive integers")
        self._values = dict(zip(TYPE_IDS, values))
        self._ordering_values = dict(ordering_values)

    @property
    def values(self) -> tuple[int, ...]:
        return tuple(self._values[type_id] for type_id in TYPE_IDS)

    def evaluate(self, state) -> int:
        score = 0
        position = state.position
        for piece in position.board:
            if piece is None:
                continue
            value = self._values.get(piece.current_type_id, 0)
            score += value if piece.owner == 0 else -value
        for owner in (0, 1):
            for type_id, count in position.hands[owner].counts:
                value = self._values.get(type_id, 0)
                score += count * value if owner == 0 else -count * value
        return score if position.side_to_move == 0 else -score

    def capture_order_value(self, moving_piece, captured_piece) -> int:
        moving = self._ordering_values[moving_piece.current_type_id]
        captured = self._ordering_values[captured_piece.current_type_id]
        return captured * 10 - moving // 10

    def type_value(self, type_id: str) -> int:
        return self._ordering_values[type_id]


@dataclass(frozen=True, slots=True)
class GameOutcome:
    child_owner: int
    winner: int | None
    result: str
    plies: int
    actions: tuple[dict, ...]

    @property
    def child_points(self) -> float:
        if self.result == "no_contest":
            raise RuntimeError("explicit no-contest cannot become a draw")
        if self.winner is None:
            return 0.5
        return 1.0 if self.winner == self.child_owner else 0.0


def _player(compiled, values: tuple[int, ...], ordering_values: dict[str, int]) -> AlphaBetaPlayer:
    return AlphaBetaPlayer(
        compiled,
        evaluation_config=EvaluationConfig(),
        evaluator_override=MaterialOnlyEvaluator(values, ordering_values),
        tt_max_entries=TT_MAX_ENTRIES,
        use_disk_cache=False,
        use_tt=True,
        use_ordering=True,
        use_native_semantic_legality=True,
        tuning=SearchTuning(),
    )


def play_game(compiled, opening: ArenaOpening, champion: tuple[int, ...], child: tuple[int, ...], child_owner: int, ordering_values: dict[str, int]) -> GameOutcome:
    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    players = (
        _player(compiled, child if child_owner == 0 else champion, ordering_values),
        _player(compiled, child if child_owner == 1 else champion, ordering_values),
    )
    actions = []
    while session.result.status.value == "ongoing":
        side = session.state.position.side_to_move
        decision = players[side].choose_action(session, SEARCH_LIMITS)
        if decision.declaration is not None:
            session.declare(decision.declaration)
            break
        if decision.action is None:
            raise RuntimeError(f"ongoing game returned no action: {decision.termination_reason}")
        if decision.action not in session.legal_actions():
            raise RuntimeError("AlphaBeta returned an illegal action")
        session.submit(decision.action)
        actions.append(action_to_dict(decision.action))
    result = session.result
    return GameOutcome(
        child_owner=child_owner,
        winner=result.winner,
        result=result.status.value,
        plies=len(actions),
        actions=tuple(actions),
    )


def _run_pair(compiled, opening: ArenaOpening, champion: tuple[int, ...], child: tuple[int, ...], ordering_values: dict[str, int]) -> dict:
    outcomes = [
        play_game(compiled, opening, champion, child, owner, ordering_values)
        for owner in (0, 1)
    ]
    scores = [outcome.child_points for outcome in outcomes]
    return {
        "pair_index": opening.index,
        "opening_id": opening.final_position_key,
        "games": [
            {
                "child_owner": outcome.child_owner,
                "winner": outcome.winner,
                "result": outcome.result,
                "plies": outcome.plies,
                "actions": list(outcome.actions),
            }
            for outcome in outcomes
        ],
        "pair_score": sum(scores) / 2.0,
    }


def run_pairs(compiled, champion: tuple[int, ...], child: tuple[int, ...], openings, ordering_values: dict[str, int], workers: int) -> tuple[dict, ...]:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run_pair, compiled, opening, champion, child, ordering_values) for opening in openings]
        rows = [future.result() for future in futures]
    return tuple(sorted(rows, key=lambda row: row["pair_index"]))


def summary(rows: tuple[dict, ...], *, bootstrap_seed: int) -> dict:
    scores = tuple(float(row["pair_score"]) for row in rows)
    if not scores:
        raise ValueError("no scoring pairs")
    low, high = bootstrap_pair_mean_ci(scores, seed=bootstrap_seed)
    wins = draws = losses = 0
    for row in rows:
        for game in row["games"]:
            if game["result"] == "no_contest":
                raise RuntimeError("no-contest is not a scoring draw")
            if game["winner"] is None:
                draws += 1
            elif game["winner"] == game["child_owner"]:
                wins += 1
            else:
                losses += 1
    return {
        "pair_count": len(scores),
        "pair_scores": list(scores),
        "mean_pair_score": sum(scores) / len(scores),
        "child_better_pairs": sum(score > 0.5 for score in scores),
        "tied_pairs": sum(score == 0.5 for score in scores),
        "child_worse_pairs": sum(score < 0.5 for score in scores),
        "bootstrap_95_ci": [low, high],
        "game_wins": wins,
        "game_draws": draws,
        "game_losses": losses,
        "game_score_rate": sum(scores) / len(scores),
    }


def _ordering_values(compiled) -> dict[str, int]:
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    return {type_id: int(profile.board_value_by_type[type_id]) for type_id in compiled.types_by_id}


def _vector_record(values: tuple[int, ...]) -> dict:
    return {"type_ids": list(TYPE_IDS), "values": list(values), "sha256": _sha(dict(zip(TYPE_IDS, values)))}


def _sanity(values: tuple[int, ...]) -> str:
    strongest = TYPE_IDS[max(range(len(values)), key=values.__getitem__)]
    weakest = TYPE_IDS[min(range(len(values)), key=values.__getitem__)]
    return f"descriptive only: strongest={strongest}, weakest={weakest}, median={int(_median(values))}"


def run(*, output: Path, workers: int = 4, include_gen3: bool = True) -> dict:
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    if tuple(type_id for type_id in compiled.types_by_id if type_id != "K") != TYPE_IDS:
        raise RuntimeError("Standard Shogi material type order drift")
    ordering_values = _ordering_values(compiled)
    ordering_sha = _sha(ordering_values)
    gen0 = gen0_vector()
    integrity_openings = generate_arena_openings(compiled, count=4, seed=1_440_901, min_plies=4, max_plies=12).openings
    integrity_rows = run_pairs(compiled, gen0, gen0, integrity_openings, ordering_values, workers)
    integrity = summary(integrity_rows, bootstrap_seed=1_440_991)
    if integrity["mean_pair_score"] != 0.5:
        classification = "F144_PAIRED_ARENA_INTEGRITY_FAILURE"
        result = {"classification": classification, "integrity": integrity}
        output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        return result

    champion = gen0
    generations = []
    max_generation = 3 if include_gen3 else 2
    for generation in range(1, max_generation + 1):
        mutants = mutate_vectors(champion, generation)
        screening_openings = generate_arena_openings(compiled, count=4, seed=SCREENING_SEEDS[generation], min_plies=4, max_plies=12).openings
        screening = []
        for mutant_index, mutant in enumerate(mutants):
            rows = run_pairs(compiled, champion, mutant, screening_openings, ordering_values, workers)
            record = summary(rows, bootstrap_seed=1_443_000 + generation * 10 + mutant_index)
            screening.append({"mutant_index": mutant_index, "vector": _vector_record(mutant), "result": record})
        selected = max(screening, key=lambda row: (row["result"]["mean_pair_score"], row["result"]["child_better_pairs"], -row["mutant_index"]))
        selected_vector = tuple(selected["vector"]["values"])
        promotion_openings = generate_arena_openings(compiled, count=24, seed=PROMOTION_SEEDS[generation], min_plies=4, max_plies=12).openings
        promotion_rows = run_pairs(compiled, champion, selected_vector, promotion_openings, ordering_values, workers)
        promotion = summary(promotion_rows, bootstrap_seed=1_444_000 + generation)
        passed = promotion["mean_pair_score"] > 0.5 and promotion["bootstrap_95_ci"][0] > 0.5
        generations.append({
            "generation": generation,
            "parent": _vector_record(champion),
            "mutants": screening,
            "selected_mutant_index": selected["mutant_index"],
            "selected": _vector_record(selected_vector),
            "screening_opening_seed": SCREENING_SEEDS[generation],
            "promotion_opening_seed": PROMOTION_SEEDS[generation],
            "promotion": promotion,
            "promoted": passed,
        })
        if not passed:
            classification = "MATERIAL_ONLY_GEN1_DOES_NOT_BEAT_GEN0" if generation == 1 else "MATERIAL_ONLY_GEN1_PASSES_GEN2_DOES_NOT_BEAT_GEN1" if generation == 2 else "MATERIAL_ONLY_TWO_GENERATION_IMPROVEMENT_ESTABLISHED_GEN3_PLATEAUS"
            break
        champion = selected_vector
    else:
        classification = "MATERIAL_ONLY_GEN1_GEN2_GEN3_IMPROVEMENT_ESTABLISHED" if include_gen3 else "MATERIAL_ONLY_TWO_GENERATION_IMPROVEMENT_ESTABLISHED"
    if len(generations) >= 2 and all(row["promoted"] for row in generations[:2]) and not include_gen3:
        classification = "MATERIAL_ONLY_TWO_GENERATION_IMPROVEMENT_ESTABLISHED"
    result = {
        "schema": "F144_SHOGI_MATERIAL_ONLY_ARENA_EVOLUTION_V1",
        "classification": classification,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "type_ids": list(TYPE_IDS),
        "search": {
            "max_nodes": 1000,
            "max_depth": 12,
            "quiescence_max_depth": 4,
            "quiescence_hard_max_depth": 8,
            "tt_max_entries": TT_MAX_ENTRIES,
            "tuning": "SearchTuning()",
            "fresh_player_per_game": True,
            "fixed_ordering_values": ordering_values,
            "fixed_ordering_sha256": ordering_sha,
        },
        "gen0": {"seed": GEN0_SEED, "raw_sampling": "log(value)~Uniform(log(250),log(4000))", "vector": _vector_record(gen0), "sanity": _sanity(gen0)},
        "integrity": integrity,
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
    parser.add_argument("--no-gen3", action="store_true")
    args = parser.parse_args()
    result = run(output=args.output, workers=args.workers, include_gen3=not args.no_gen3)
    print(json.dumps({"classification": result["classification"], "generations": len(result.get("generations", ()))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
