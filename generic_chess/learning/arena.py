"""Integrity-preserving paired arena.

Measurement rules:
* every game replays one corpus opening (identical within a pair);
* every game creates **fresh** parent and child engines (TT never crosses
  games);
* engine failures are raised, never counted as draws;
* the primary statistic is the paired score with a pair-level bootstrap CI.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..ai.evaluation.config import EvaluationConfig
from ..ai.limits import SearchLimits
from ..core.actions import Action, action_to_dict
from ..core.identity import position_identity_key
from ..native.compiler import compile_native_evaluation
from ..native.engine import NativeSearchEngine
from ..native.semantic_engine import SemanticSearchEngine
from ..session.session import GameSession
from .material import LearnableMaterialCheckpoint
from .openings import ArenaOpeningCorpus, generate_arena_openings
from .statistics import bootstrap_pair_mean_ci


class ArenaExecutionError(RuntimeError):
    """Raised when the arena cannot produce a valid measurement."""


@dataclass(frozen=True, slots=True)
class ArenaConfig:
    pairs: int = 10
    nodes_per_move: int = 5000
    max_depth: int = 12
    tt_megabytes: int = 8
    opening_seed: int = 314159
    opening_count: int = 0  # 0 -> use pairs
    min_plies: int = 2
    max_plies: int = 6

    def __post_init__(self) -> None:
        if self.pairs <= 0 or self.nodes_per_move <= 0 or self.max_depth <= 0:
            raise ValueError("arena budgets must be positive")


@dataclass(frozen=True, slots=True)
class ArenaGameResult:
    pair: int
    opening_id: str
    opening_position_key: str
    child_owner: int
    winner: int | None
    result: str
    plies: int
    actions: tuple[Action, ...]
    final_position_key: str

    @property
    def child_points(self) -> float:
        if self.winner is None:
            return 0.5
        return 1.0 if self.winner == self.child_owner else 0.0


@dataclass(frozen=True, slots=True)
class ArenaPairResult:
    pair_index: int
    opening_id: str
    game_child_owner0: ArenaGameResult
    game_child_owner1: ArenaGameResult

    @property
    def child_pair_score(self) -> float:
        return (
            self.game_child_owner0.child_points
            + self.game_child_owner1.child_points
        ) / 2.0


@dataclass(frozen=True, slots=True)
class ArenaSummary:
    pair_count: int
    pair_scores: tuple[float, ...]
    mean_pair_score: float
    child_better_pairs: int
    tied_pairs: int
    child_worse_pairs: int
    bootstrap_low: float
    bootstrap_high: float
    # Descriptive game-level aggregates.
    game_wins: int
    game_draws: int
    game_losses: int
    game_score_rate: float
    pairs: tuple[ArenaPairResult, ...]


def _engine_for(compiled, native_rules, checkpoint, tt_mb):
    from ..rules.ir import CompiledSemanticRuleset

    if isinstance(compiled, CompiledSemanticRuleset):
        return SemanticSearchEngine(
            compiled, native_rules, checkpoint=checkpoint,
            tt_megabytes=tt_mb,
        )
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


def _play_one_game(
    compiled,
    native_rules,
    parent,
    child,
    *,
    opening,
    child_owner: int,
    config: ArenaConfig,
) -> ArenaGameResult:
    """Replay ``opening``, then play one game with fresh engines."""
    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    opening_key = position_identity_key(session.state.position, compiled)
    parent_engine = _engine_for(
        compiled, native_rules, parent, config.tt_megabytes
    )
    child_engine = _engine_for(
        compiled, native_rules, child, config.tt_megabytes
    )
    actions: list[Action] = []
    plies = 0
    while session.result.status.value == "ongoing":
        legal = session.legal_actions()
        if not legal:
            raise ArenaExecutionError(
                "Core reports no legal moves but the session is ongoing"
            )
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
        if getattr(result, "declaration_id", None) is not None:
            session.declare(result.declaration_id)
            break
        if result.action is None:
            raise ArenaExecutionError(
                "engine returned no action on an ongoing position "
                f"(termination_reason={result.termination_reason})"
            )
        session.submit(result.action)
        actions.append(result.action)
        plies += 1
    return ArenaGameResult(
        pair=opening.index,
        opening_id=opening.final_position_key,
        opening_position_key=opening_key,
        child_owner=child_owner,
        winner=session.result.winner,
        result=session.result.status.value,
        plies=plies,
        actions=tuple(actions),
        final_position_key=position_identity_key(session.state.position, compiled),
    )


def run_arena(
    compiled,
    native_rules,
    parent: LearnableMaterialCheckpoint,
    child: LearnableMaterialCheckpoint,
    config: ArenaConfig,
    openings: ArenaOpeningCorpus | None = None,
) -> ArenaSummary:
    """Paired matches over a fixed evaluator-neutral opening corpus.

    Each pair plays the same opening twice with swapped colors; every game
    uses fresh parent/child engines so TT never crosses games.
    """
    parent.validate_ruleset(compiled)
    child.validate_ruleset(compiled)
    if openings is None:
        openings = generate_arena_openings(
            compiled,
            count=config.opening_count or config.pairs,
            seed=config.opening_seed,
            min_plies=config.min_plies,
            max_plies=config.max_plies,
        )
    openings.validate(compiled)
    if len(openings.openings) < config.pairs:
        raise ValueError(
            f"opening corpus has {len(openings.openings)} openings but "
            f"{config.pairs} pairs requested"
        )

    pairs: list[ArenaPairResult] = []
    game_wins = game_draws = game_losses = 0
    for pair_index in range(config.pairs):
        opening = openings.openings[pair_index]
        game_child_owner0 = _play_one_game(
            compiled, native_rules, parent, child,
            opening=opening, child_owner=0, config=config,
        )
        game_child_owner1 = _play_one_game(
            compiled, native_rules, parent, child,
            opening=opening, child_owner=1, config=config,
        )
        pairs.append(
            ArenaPairResult(
                pair_index=pair_index,
                opening_id=opening.final_position_key,
                game_child_owner0=game_child_owner0,
                game_child_owner1=game_child_owner1,
            )
        )
        game_wins += sum(
            1 for g in (game_child_owner0, game_child_owner1) if g.child_points == 1.0
        )
        game_draws += sum(
            1 for g in (game_child_owner0, game_child_owner1) if g.child_points == 0.5
        )
        game_losses += sum(
            1 for g in (game_child_owner0, game_child_owner1) if g.child_points == 0.0
        )

    pair_scores = tuple(p.child_pair_score for p in pairs)
    mean = sum(pair_scores) / len(pair_scores) if pair_scores else 0.0
    better = sum(1 for s in pair_scores if s > 0.5)
    tied = sum(1 for s in pair_scores if s == 0.5)
    worse = sum(1 for s in pair_scores if s < 0.5)
    low, high = bootstrap_pair_mean_ci(list(pair_scores))
    total_games = game_wins + game_draws + game_losses
    return ArenaSummary(
        pair_count=len(pairs),
        pair_scores=pair_scores,
        mean_pair_score=mean,
        child_better_pairs=better,
        tied_pairs=tied,
        child_worse_pairs=worse,
        bootstrap_low=low,
        bootstrap_high=high,
        game_wins=game_wins,
        game_draws=game_draws,
        game_losses=game_losses,
        game_score_rate=(
            (game_wins + 0.5 * game_draws) / total_games if total_games else 0.0
        ),
        pairs=tuple(pairs),
    )
