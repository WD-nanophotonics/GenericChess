"""Cheap, serializable Game Quality Profile measurements for F86A."""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from statistics import median
from typing import Any

from ..core.actions import action_source_square
from ..session.session import GameSession
from .minimal_generator import MinimalGeneratedGame


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
    side_bias_magnitude: float | None = None
    swapped_opening_consistent: bool | None = None
    shallow_forced_win_rate: float | None = None
    solved_fraction: float | None = None
    unique_best_fraction: float | None = None
    skill_discrimination: float | None = None
    classification: str = "UNRESOLVED"
    classification_reasons: tuple[str, ...] = field(default_factory=lambda: ("UNRESOLVED",))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_game_quality(profile: GameQualityProfile) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    if profile.side_bias_magnitude is not None and profile.side_bias_magnitude > 0.15:
        reasons.append("SIDE_BIASED")
    if profile.solved_fraction is not None and profile.solved_fraction >= 0.75:
        reasons.append("TRIVIAL_OR_SHALLOW_SOLVED")
    if profile.branching_collapse_fraction >= 0.75:
        reasons.append("FORCED_LINE")
    if profile.p90_game_branching >= 100:
        reasons.append("SEARCH_EXPLOSIVE")
    if profile.terminal_distribution:
        total = sum(profile.terminal_distribution.values())
        draw_statuses = {"repetition", "stalemate", "max_ply", "perpetual_check"}
        draws = sum(v for k, v in profile.terminal_distribution.items() if k in draw_statuses)
        if total and draws / total >= 0.9:
            reasons.append("DRAW_DOMINATED")
    if profile.shallow_forced_win_rate is not None and profile.shallow_forced_win_rate >= 0.75:
        reasons.append("TACTICAL_ONLY")
    if profile.skill_discrimination is not None and profile.skill_discrimination <= 0.01:
        reasons.append("INSUFFICIENT_SKILL_DISCRIMINATION")
    if not reasons:
        reasons.append("UNRESOLVED")
    return reasons[0], tuple(reasons)


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
    for _ in range(trajectory_count):
        session = GameSession(compiled)
        while session.result.status.value == "ongoing" and len(session.history) < max_ply:
            actions = session.legal_actions()
            if not actions:
                break
            count = len(actions)
            ply = len(session.history)
            branchings.append(count)
            bins["opening" if ply < 8 else "mid" if ply < 16 else "end"].append(count)
            session.submit(actions[rng.randrange(count)])
        lengths.append(len(session.history))
        terminals[session.result.status.value] += 1
        if session.result.status.value != "ongoing" and len(session.history) <= 4:
            short_terminal_count += 1

    forced = sum(count == 1 for count in branchings)
    low = sum(count <= 2 for count in branchings)
    mid_end = bins["mid"] + bins["end"]
    collapsed = sum(count <= 2 for count in mid_end)
    profile = GameQualityProfile(
        ruleset_fingerprint=game.ruleset_fingerprint,
        board_size=game.board_size,
        piece_counts_by_side=piece_counts,
        type_counts_by_side={side: dict(counts) for side, counts in type_counts.items()},
        opening_legal_actions=len(opening_actions),
        opening_mobility_by_type=dict(mobility),
        trajectory_count=trajectory_count,
        trajectory_lengths=tuple(lengths),
        branching_counts=tuple(branchings),
        median_branching=float(median(branchings)) if branchings else None,
        p10_game_branching=_percentile(branchings, 0.1),
        p90_game_branching=_percentile(branchings, 0.9),
        branching_by_ply_bin={key: tuple(value) for key, value in bins.items()},
        forced_move_fraction=forced / len(branchings) if branchings else 0.0,
        low_branch_fraction=low / len(branchings) if branchings else 0.0,
        branching_collapse_fraction=collapsed / len(mid_end) if mid_end else 0.0,
        terminal_distribution=dict(terminals),
        median_game_length=float(median(lengths)) if lengths else None,
        p10_game_length=_percentile(lengths, 0.1),
        p90_game_length=_percentile(lengths, 0.9),
        repetition_draw_fraction=(terminals["repetition"] / trajectory_count),
        very_short_terminal_fraction=short_terminal_count / trajectory_count,
    )
    classification, reasons = classify_game_quality(profile)
    return GameQualityProfile(**{**profile.to_dict(), "classification": classification, "classification_reasons": reasons})
