"""Per-move search budget allocation from a match clock (Qt-free)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..clock import ClockState, TimeControl, TimeControlMode
from .limits import SearchLimits


class ThinkingStrategy(StrEnum):
    FIXED_NODES = "fixed_nodes"
    FIXED_TIME = "fixed_time"
    AUTO_TIME = "auto_time"


class ThinkingPreset(StrEnum):
    QUICK = "quick"
    BALANCED = "balanced"
    DEEP = "deep"


PRESET_NODES = {
    ThinkingPreset.QUICK: 5000,
    ThinkingPreset.BALANCED: 50000,
    ThinkingPreset.DEEP: 200000,
}


@dataclass(frozen=True, slots=True)
class ThinkingConfig:
    strategy: ThinkingStrategy = ThinkingStrategy.FIXED_NODES
    preset: ThinkingPreset = ThinkingPreset.BALANCED
    move_time_seconds: float = 1.0
    max_nodes: int | None = None
    max_depth: int | None = None
    safety_margin_seconds: float = 0.3
    quiescence_max_depth: int = 4


def allocate_search_limits(
    clock_state: ClockState | None,
    time_control: TimeControl,
    owner: int,
    move_number: int,
    config: ThinkingConfig,
) -> SearchLimits:
    """Map a thinking config + clock state to a SearchLimits budget."""
    nodes: int | None = None
    seconds: float | None = None

    if config.strategy is ThinkingStrategy.FIXED_NODES:
        nodes = config.max_nodes or PRESET_NODES[config.preset]
        if (
            time_control.mode is not TimeControlMode.NONE
            and time_control.time_forfeit
            and clock_state is not None
        ):
            available = _clock_available_seconds(time_control, clock_state, owner)
            seconds = max(0.01, available - config.safety_margin_seconds)
    elif config.strategy is ThinkingStrategy.FIXED_TIME:
        seconds = max(0.01, config.move_time_seconds)
        nodes = config.max_nodes
    else:  # AUTO_TIME
        seconds = _automatic_seconds(time_control, clock_state, owner, move_number, config)
        nodes = config.max_nodes

    if seconds is not None and (
        time_control.mode is not TimeControlMode.NONE and time_control.time_forfeit
    ):
        remaining = _clock_available_seconds(time_control, clock_state, owner)
        seconds = min(seconds, max(0.01, remaining - config.safety_margin_seconds))

    return SearchLimits(
        max_depth=config.max_depth,
        max_nodes=nodes,
        max_time_seconds=seconds,
        quiescence_max_depth=config.quiescence_max_depth,
    )


def _clock_available_seconds(
    time_control: TimeControl, clock: ClockState, owner: int
) -> float:
    remaining = clock.remaining_for(owner) / 1000.0
    if time_control.mode is TimeControlMode.BYOYOMI:
        remaining += clock.overtime_for(owner) / 1000.0
    return remaining


def _automatic_seconds(
    time_control: TimeControl,
    clock: ClockState | None,
    owner: int,
    move_number: int,
    config: ThinkingConfig,
) -> float:
    if time_control.mode is TimeControlMode.NONE or clock is None:
        return max(0.01, config.move_time_seconds)
    main = clock.remaining_for(owner) / 1000.0
    overtime = max(0.0, float(time_control.for_owner(owner).overtime_seconds))
    own_moves_played = max(0, (max(1, move_number) - 1) // 2)
    expected, minimum = {
        ThinkingPreset.QUICK: (80, 30),
        ThinkingPreset.BALANCED: (60, 20),
        ThinkingPreset.DEEP: (40, 15),
    }[config.preset]
    moves_to_go = max(minimum, expected - own_moves_played)
    if time_control.mode is TimeControlMode.BYOYOMI and main <= 0:
        calculated = clock.overtime_for(owner) / 1000.0 * 0.8
    else:
        calculated = main * 0.9 / moves_to_go + overtime * 0.8
    return max(0.01, calculated)
