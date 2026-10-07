"""Search budget allocation from a clock."""

import pytest

from generic_chess.ai.budget import (
    PRESET_NODES,
    ThinkingConfig,
    ThinkingPreset,
    ThinkingStrategy,
    allocate_search_limits,
)
from generic_chess.clock import ClockState, SideTimeConfig, TimeControl, TimeControlMode


def _clock_state(mode: TimeControlMode, remaining=60000, overtime=10000, active=0):
    return ClockState(
        remaining_ms=(remaining, remaining),
        overtime_remaining_ms=(overtime, overtime),
        active_owner=active,
        running=mode is not TimeControlMode.NONE,
    )


def _time_control(mode: TimeControlMode, overtime=10):
    return TimeControl(
        mode=mode,
        owner0=SideTimeConfig(60, overtime),
        owner1=SideTimeConfig(60, overtime),
    )


def test_fixed_nodes_without_clock():
    limits = allocate_search_limits(
        None,
        _time_control(TimeControlMode.NONE),
        0,
        1,
        ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset=ThinkingPreset.DEEP),
    )
    assert limits.max_nodes == PRESET_NODES[ThinkingPreset.DEEP]
    assert limits.max_time_seconds is None


def test_fixed_time():
    limits = allocate_search_limits(
        None,
        _time_control(TimeControlMode.NONE),
        0,
        1,
        ThinkingConfig(strategy=ThinkingStrategy.FIXED_TIME, move_time_seconds=2.5),
    )
    assert limits.max_time_seconds == pytest.approx(2.5)


def test_auto_time_uses_main_time_with_safety():
    state = _clock_state(TimeControlMode.BYOYOMI, remaining=60000)
    limits = allocate_search_limits(
        state,
        _time_control(TimeControlMode.BYOYOMI),
        0,
        1,
        ThinkingConfig(strategy=ThinkingStrategy.AUTO_TIME, preset=ThinkingPreset.BALANCED),
    )
    assert limits.max_time_seconds is not None
    assert 0.01 < limits.max_time_seconds <= 60.0


def test_auto_time_byoyomi_uses_overtime_when_main_empty():
    state = _clock_state(TimeControlMode.BYOYOMI, remaining=0, overtime=10000)
    limits = allocate_search_limits(
        state,
        _time_control(TimeControlMode.BYOYOMI, overtime=10),
        0,
        5,
        ThinkingConfig(strategy=ThinkingStrategy.AUTO_TIME, preset=ThinkingPreset.BALANCED),
    )
    assert limits.max_time_seconds is not None
    assert limits.max_time_seconds <= 8.0 + 1e-9  # overtime * 0.8


def test_fixed_nodes_clamped_by_clock_safety():
    state = _clock_state(TimeControlMode.FISCHER, remaining=5000)
    limits = allocate_search_limits(
        state,
        _time_control(TimeControlMode.FISCHER),
        0,
        1,
        ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset=ThinkingPreset.DEEP),
    )
    assert limits.max_time_seconds == pytest.approx(4.7)  # 5.0 - 0.3 safety


def test_max_depth_passthrough():
    limits = allocate_search_limits(
        None,
        _time_control(TimeControlMode.NONE),
        0,
        1,
        ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, max_depth=6),
    )
    assert limits.max_depth == 6


def test_fixed_nodes_keeps_preset_with_clock():
    state = _clock_state(TimeControlMode.FISCHER, remaining=10_000)
    limits = allocate_search_limits(
        state,
        _time_control(TimeControlMode.FISCHER),
        0,
        1,
        ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset=ThinkingPreset.DEEP),
    )
    assert limits.max_time_seconds == pytest.approx(9.7)  # 10.0 - 0.3 safety
    assert limits.max_nodes == PRESET_NODES[ThinkingPreset.DEEP]  # no time nps cap
