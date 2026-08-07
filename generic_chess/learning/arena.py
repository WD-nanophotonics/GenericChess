"""Fair parent-vs-child arena with swapped colors."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..ai.evaluation.config import EvaluationConfig
from ..ai.limits import SearchLimits
from ..native.compiler import compile_native_evaluation
from ..native.engine import NativeSearchEngine
from ..session.session import GameSession
from .material import LearnableMaterialCheckpoint


@dataclass(frozen=True, slots=True)
class ArenaConfig:
    pairs: int = 10
    nodes_per_move: int = 5000
    max_depth: int = 12
    tt_megabytes: int = 8
    seed: int = 0


@dataclass(frozen=True, slots=True)
class ArenaGameResult:
    pair: int
    child_owner: int
    winner: int | None
    result: str
    plies: int

    @property
    def child_points(self) -> float:
        if self.winner is None:
            return 0.5
        return 1.0 if self.winner == self.child_owner else 0.0


@dataclass(frozen=True, slots=True)
class ArenaSummary:
    wins: int
    draws: int
    losses: int
    score_rate: float
    wilson_low: float
    wilson_high: float
    games: list[ArenaGameResult]


def wilson_interval(wins: int, draws: int, total: int, z: float = 1.96):
    """Wilson score interval for the score rate (win=1, draw=0.5)."""
    if total == 0:
        return 0.0, 0.0
    score = (wins + 0.5 * draws) / total
    n = total
    p = score
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def _engine_for(compiled, native_rules, checkpoint, tt_mb):
    eval_tables = compile_native_evaluation(
        native_rules,
        _dummy_profile(compiled, checkpoint),
        EvaluationConfig(),
        material_override=checkpoint,
    )
    return NativeSearchEngine(compiled, native_rules, eval_tables, tt_mb)


def _dummy_profile(compiled, checkpoint):
    from types import SimpleNamespace

    return SimpleNamespace(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        promotion_gain_by_type={pt.type_id: 0 for pt in compiled.piece_types},
        evaluator_version=checkpoint.evaluator_version,
    )


def run_arena(
    compiled,
    native_rules,
    parent: LearnableMaterialCheckpoint,
    child: LearnableMaterialCheckpoint,
    config: ArenaConfig,
) -> ArenaSummary:
    """Paired matches: one game with parent as owner 0 / child owner 1, and
    one with colors swapped.  No exploration; same search budgets/TT size.
    Returns child-perspective statistics."""
    parent.validate_ruleset(compiled)
    child.validate_ruleset(compiled)
    parent_engine = _engine_for(compiled, native_rules, parent, config.tt_megabytes)
    child_engine = _engine_for(compiled, native_rules, child, config.tt_megabytes)
    games: list[ArenaGameResult] = []
    wins = draws = losses = 0
    for pair in range(config.pairs):
        for child_owner in (0, 1):
            session = GameSession(compiled)
            plies = 0
            while session.result.status.value == "ongoing":
                side = session.state.position.side_to_move
                engine = child_engine if side == child_owner else parent_engine
                result = engine.search(
                    session,
                    SearchLimits(
                        max_depth=config.max_depth,
                        max_nodes=config.nodes_per_move,
                        quiescence_max_depth=0,
                    ),
                )
                legal = session.legal_actions()
                if not legal or result.action is None:
                    break
                session.submit(result.action)
                plies += 1
            winner = session.result.winner
            if winner is None:
                draws += 1
            elif winner == child_owner:
                wins += 1
            else:
                losses += 1
            games.append(
                ArenaGameResult(
                    pair=pair,
                    child_owner=child_owner,
                    winner=winner,
                    result=session.result.status.value,
                    plies=plies,
                )
            )
    total = wins + draws + losses
    score_rate = (wins + 0.5 * draws) / total if total else 0.0
    low, high = wilson_interval(wins, draws, total)
    return ArenaSummary(
        wins=wins,
        draws=draws,
        losses=losses,
        score_rate=score_rate,
        wilson_low=low,
        wilson_high=high,
        games=tuple(games),
    )
