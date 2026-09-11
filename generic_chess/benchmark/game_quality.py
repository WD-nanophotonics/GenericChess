"""Cheap, serializable Game Quality Profile measurements for F86A."""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field, replace
from statistics import median
from typing import Any

from ..core.actions import action_source_square
from ..session.session import GameSession
from .minimal_generator import MinimalGeneratedGame, swap_owner_opening
from .tactical_probe import probe_terminal_only


QUALITY_REASONS = (
    "QUALIFIED_GENERAL",
    "SIDE_BIASED",
    "TRIVIAL_OR_SHALLOW_SOLVED",
    "FORCED_LINE",
    "SEARCH_EXPLOSIVE",
    "DRAW_DOMINATED",
    "TACTICAL_ONLY",
    "INSUFFICIENT_SKILL_DISCRIMINATION",
    "UNRESOLVED",
)


def _percentile(values: list[int], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction)))
    return float(ordered[index])


@dataclass(frozen=True, slots=True)
class QualityObservation:
    """One bounded game observation consumed by the shared aggregator."""

    branching_counts: tuple[int, ...]
    game_length: int
    terminal_status: str
    first_player_score: float | None = None
    second_player_score: float | None = None
    forced_win: bool | None = None
    solved: bool | None = None
    unique_best: bool | None = None


def profile_from_observations(
    observations: tuple[QualityObservation, ...] | list[QualityObservation],
    *,
    ruleset_fingerprint: str = "synthetic",
    board_size: int = 0,
) -> "GameQualityProfile":
    """Aggregate real or deterministic fixture observations through one path."""
    if not observations:
        raise ValueError("at least one quality observation is required")
    observations = tuple(observations)
    branchings = [count for observation in observations for count in observation.branching_counts]
    bins = {"opening": [], "mid": [], "end": []}
    for observation in observations:
        for ply, count in enumerate(observation.branching_counts):
            bins["opening" if ply < 8 else "mid" if ply < 16 else "end"].append(count)
    lengths = [observation.game_length for observation in observations]
    terminals = Counter(observation.terminal_status for observation in observations)
    forced = sum(count == 1 for count in branchings)
    low = sum(count <= 2 for count in branchings)
    mid_end = bins["mid"] + bins["end"]
    first = [o.first_player_score for o in observations if o.first_player_score is not None]
    second = [o.second_player_score for o in observations if o.second_player_score is not None]
    first_score = sum(first) / len(first) if first else None
    second_score = sum(second) / len(second) if second else None
    solved_values = [o.solved for o in observations if o.solved is not None]
    forced_values = [o.forced_win for o in observations if o.forced_win is not None]
    unique_values = [o.unique_best for o in observations if o.unique_best is not None]
    profile = GameQualityProfile(
        ruleset_fingerprint=ruleset_fingerprint,
        board_size=board_size,
        piece_counts_by_side={"0": 0, "1": 0},
        type_counts_by_side={"0": {}, "1": {}},
        opening_legal_actions=branchings[0] if branchings else 0,
        opening_mobility_by_type={},
        trajectory_count=len(observations),
        trajectory_lengths=tuple(lengths),
        branching_counts=tuple(branchings),
        median_branching=float(median(branchings)) if branchings else None,
        p10_game_branching=_percentile(branchings, 0.1),
        p90_game_branching=_percentile(branchings, 0.9),
        branching_by_ply_bin={key: tuple(value) for key, value in bins.items()},
        forced_move_fraction=forced / len(branchings) if branchings else 0.0,
        low_branch_fraction=low / len(branchings) if branchings else 0.0,
        branching_collapse_fraction=(sum(count <= 2 for count in mid_end) / len(mid_end) if mid_end else 0.0),
        terminal_distribution=dict(terminals),
        median_game_length=float(median(lengths)),
        p10_game_length=_percentile(lengths, 0.1),
        p90_game_length=_percentile(lengths, 0.9),
        repetition_draw_fraction=terminals["repetition"] / len(observations),
        very_short_terminal_fraction=sum(
            o.game_length <= 4 and o.terminal_status != "ongoing" for o in observations
        ) / len(observations),
        first_player_score=first_score,
        second_player_score=second_score,
        paired_game_count=len(first) if first and len(first) == len(second) else 0,
        side_bias_magnitude=(abs(first_score - second_score) if first_score is not None and second_score is not None else None),
        shallow_forced_win_rate=(sum(forced_values) / len(forced_values) if forced_values else None),
        solved_fraction=(sum(solved_values) / len(solved_values) if solved_values else None),
        unique_best_fraction=(sum(unique_values) / len(unique_values) if unique_values else None),
    )
    classification, reasons = classify_game_quality(profile)
    return GameQualityProfile(**{**profile.to_dict(), "classification": classification, "classification_reasons": reasons})


@dataclass(frozen=True, slots=True)
class GameQualityProfile:
    ruleset_fingerprint: str
    board_size: int
    piece_counts_by_side: dict[str, int]
    type_counts_by_side: dict[str, dict[str, int]]
    opening_legal_actions: int
    opening_mobility_by_type: dict[str, int]
    trajectory_count: int
    trajectory_lengths: tuple[int, ...]
    branching_counts: tuple[int, ...]
    median_branching: float | None
    p10_game_branching: float | None
    p90_game_branching: float | None
    branching_by_ply_bin: dict[str, tuple[int, ...]]
    forced_move_fraction: float
    low_branch_fraction: float
    branching_collapse_fraction: float
    terminal_distribution: dict[str, int]
    median_game_length: float | None
    p10_game_length: float | None
    p90_game_length: float | None
    repetition_draw_fraction: float
    very_short_terminal_fraction: float
    first_player_score: float | None = None
    second_player_score: float | None = None
    paired_game_count: int = 0
    side_bias_magnitude: float | None = None
    swapped_opening_consistent: bool | None = None
    shallow_forced_win_rate: float | None = None
    solved_fraction: float | None = None
    unique_best_fraction: float | None = None
    tactical_probe_position_count: int = 0
    tactical_probe_nodes: int = 0
    skill_discrimination: float | None = None
    classification: str = "UNRESOLVED"
    classification_reasons: tuple[str, ...] = field(default_factory=lambda: ("UNRESOLVED",))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_game_quality(
    profile: GameQualityProfile,
    *,
    thresholds: dict[str, float] | None = None,
) -> tuple[str, tuple[str, ...]]:
    """Return diagnostic flags; without calibrated thresholds, stay unresolved."""
    thresholds = thresholds or {}
    reasons: list[str] = []
    if profile.side_bias_magnitude is not None and profile.side_bias_magnitude > thresholds.get("side_bias", 0.15):
        reasons.append("SIDE_BIASED")
    if profile.solved_fraction is not None and profile.solved_fraction >= thresholds.get("solved_fraction", 0.75):
        reasons.append("TRIVIAL_OR_SHALLOW_SOLVED")
    if profile.branching_collapse_fraction >= thresholds.get("forced_line", 0.75):
        reasons.append("FORCED_LINE")
    if profile.p90_game_branching is not None and profile.p90_game_branching >= thresholds.get("p90_branching", 100):
        reasons.append("SEARCH_EXPLOSIVE")
    if profile.terminal_distribution:
        total = sum(profile.terminal_distribution.values())
        draw_statuses = {"repetition", "stalemate", "max_ply", "perpetual_check"}
        draws = sum(v for k, v in profile.terminal_distribution.items() if k in draw_statuses)
        if total and draws / total >= thresholds.get("draw_fraction", 0.9):
            reasons.append("DRAW_DOMINATED")
    if profile.shallow_forced_win_rate is not None and profile.shallow_forced_win_rate >= thresholds.get("forced_win", 0.75):
        reasons.append("TACTICAL_ONLY")
    if profile.skill_discrimination is not None and profile.skill_discrimination <= 0.01:
        reasons.append("INSUFFICIENT_SKILL_DISCRIMINATION")
    if not reasons:
        reasons.append("UNRESOLVED")
    # F86A-R1 has no population-calibrated admission thresholds.  Keep all
    # flags visible, but never turn a provisional diagnostic into authority.
    return (reasons[0] if thresholds else "UNRESOLVED"), tuple(reasons)


def _game_score(session: GameSession, player: int) -> float:
    winner = session.result.winner
    if winner is None:
        return 0.5
    return 1.0 if winner == player else 0.0


def _play_random_game(compiled, rng: random.Random, max_ply: int) -> GameSession:
    session = GameSession(compiled)
    while session.result.status.value == "ongoing" and len(session.history) < max_ply:
        actions = session.legal_actions()
        if not actions:
            break
        session.submit(actions[rng.randrange(len(actions))])
    return session


def measure_game_quality(
    game: MinimalGeneratedGame,
    *,
    trajectory_count: int = 8,
    max_ply: int = 32,
    seed: int = 0,
) -> GameQualityProfile:
    """Measure deterministic random trajectories without running a benchmark."""
    if trajectory_count < 1 or max_ply < 1:
        raise ValueError("trajectory_count and max_ply must be positive")
    compiled = game.compiled
    initial = compiled.initial_position
    piece_counts = {"0": 0, "1": 0}
    type_counts = {"0": Counter(), "1": Counter()}
    for piece in initial.board:
        if piece is not None:
            piece_counts[str(piece.owner)] += 1
            type_counts[str(piece.owner)][piece.current_type_id] += 1
    opening = GameSession(compiled)
    opening_actions = opening.legal_actions()
    mobility = Counter()
    for action in opening_actions:
        source = action_source_square(action)
        if source is not None and initial.board[source.rank * game.board_size + source.file] is not None:
            mobility[initial.board[source.rank * game.board_size + source.file].current_type_id] += 1

    rng = random.Random(seed)
    lengths: list[int] = []
    branchings: list[int] = []
    bins: dict[str, list[int]] = defaultdict(list)
    terminals: Counter[str] = Counter()
    short_terminal_count = 0
    first_scores: list[float] = []
    second_scores: list[float] = []
    tactical_results = []
    observations: list[QualityObservation] = []
    for _ in range(trajectory_count):
        session = GameSession(compiled)
        trajectory_branchings: list[int] = []
        while session.result.status.value == "ongoing" and len(session.history) < max_ply:
            actions = session.legal_actions()
            if not actions:
                break
            count = len(actions)
            ply = len(session.history)
            branchings.append(count)
            trajectory_branchings.append(count)
            bins["opening" if ply < 8 else "mid" if ply < 16 else "end"].append(count)
            session.submit(actions[rng.randrange(count)])
        lengths.append(len(session.history))
        terminals[session.result.status.value] += 1
        if session.result.status.value != "ongoing" and len(session.history) <= 4:
            short_terminal_count += 1
        first_scores.append(_game_score(session, 0))
        second_scores.append(_game_score(session, 1))
        observations.append(
            QualityObservation(
                tuple(trajectory_branchings),
                len(session.history),
                session.result.status.value,
                first_scores[-1],
                second_scores[-1],
            )
        )

    swapped = swap_owner_opening(game)
    swapped_consistent = None
    if swapped is not None:
        swapped_opening = GameSession(swapped.compiled)
        swapped_consistent = len(opening_actions) == len(swapped_opening.legal_actions())
        for _ in range(trajectory_count):
            swapped_session = _play_random_game(swapped.compiled, rng, max_ply)
            first_scores.append(_game_score(swapped_session, 0))
            second_scores.append(_game_score(swapped_session, 1))

    # Probe a bounded, fixed number of real game states.  The opening is
    # always included; this keeps F86A cheap while producing actual solver
    # observations rather than hand-authored metric values.
    tactical_results.append(probe_terminal_only(opening, depth=4, node_budget=256))

    forced = sum(count == 1 for count in branchings)
    low = sum(count <= 2 for count in branchings)
    mid_end = bins["mid"] + bins["end"]
    collapsed = sum(count <= 2 for count in mid_end)
    paired_count = len(first_scores)
    first_score = sum(first_scores) / paired_count if paired_count else None
    second_score = sum(second_scores) / paired_count if paired_count else None
    solved = sum(result.solved for result in tactical_results)
    forced_wins = sum(result.forced_win for result in tactical_results)
    unique_best_values = [result.unique_best for result in tactical_results if result.unique_best is not None]
    profile = profile_from_observations(
        observations,
        ruleset_fingerprint=game.ruleset_fingerprint,
        board_size=game.board_size,
    )
    profile = replace(
        profile,
        piece_counts_by_side=piece_counts,
        type_counts_by_side={side: dict(counts) for side, counts in type_counts.items()},
        opening_legal_actions=len(opening_actions),
        opening_mobility_by_type=dict(mobility),
        first_player_score=first_score,
        second_player_score=second_score,
        paired_game_count=paired_count,
        side_bias_magnitude=(abs(first_score - second_score) if first_score is not None and second_score is not None else None),
        swapped_opening_consistent=swapped_consistent,
        shallow_forced_win_rate=forced_wins / len(tactical_results) if tactical_results else None,
        solved_fraction=solved / len(tactical_results) if tactical_results else None,
        unique_best_fraction=(sum(unique_best_values) / len(unique_best_values) if unique_best_values else None),
        tactical_probe_position_count=len(tactical_results),
        tactical_probe_nodes=sum(result.nodes for result in tactical_results),
    )
    classification, reasons = classify_game_quality(profile)
    return GameQualityProfile(**{**profile.to_dict(), "classification": classification, "classification_reasons": reasons})
