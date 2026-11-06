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


def test_fixed_nodes_preserves_explicit_zero_node_budget():
    limits = allocate_search_limits(
        None,
        _time_control(TimeControlMode.NONE),
        0,
        1,
        ThinkingConfig(strategy="fixed_nodes", max_nodes=0),
    )
    assert limits.max_nodes == 0
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


def test_string_thinking_strategy_uses_its_named_budget_policy():
    config = ThinkingConfig(
        strategy="fixed_nodes", preset="quick", max_nodes=500
    )
    assert config.strategy is ThinkingStrategy.FIXED_NODES
    assert config.preset is ThinkingPreset.QUICK
    limits = allocate_search_limits(
        None,
        _time_control(TimeControlMode.NONE),
        0,
        1,
        config,
    )
    assert limits.max_nodes == 500
    assert limits.max_time_seconds is None


@pytest.mark.parametrize(
    ("field", "value", "choices"),
    (
        ("strategy", "not-a-strategy", "fixed_nodes, fixed_time, auto_time"),
        ("preset", "not-a-preset", "quick, balanced, deep"),
    ),
)
def test_thinking_config_rejects_unknown_enum_value_strings(field, value, choices):
    with pytest.raises(ValueError, match=f"{field} must be one of: {choices}"):
        ThinkingConfig(**{field: value})


@pytest.mark.parametrize("field", ["move_time_seconds", "safety_margin_seconds"])
@pytest.mark.parametrize("value", [True, False])
def test_thinking_config_rejects_boolean_durations(field, value):
    with pytest.raises(ValueError, match=f"{field} must be a numeric duration"):
        ThinkingConfig(**{field: value})


@pytest.mark.parametrize("field", ["move_time_seconds", "safety_margin_seconds"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_thinking_config_rejects_nonfinite_durations(field, value):
    with pytest.raises(ValueError, match=f"{field} must be a finite numeric duration"):
        ThinkingConfig(**{field: value})


def test_thinking_config_rejects_negative_clock_safety_margin():
    with pytest.raises(ValueError, match="safety_margin_seconds must be >= 0"):
        ThinkingConfig(safety_margin_seconds=-0.1)


@pytest.mark.parametrize("seconds", [0, -1.0])
def test_fixed_time_numeric_low_duration_keeps_existing_minimum_budget(seconds):
    limits = allocate_search_limits(
        None,
        _time_control(TimeControlMode.NONE),
        0,
        1,
        ThinkingConfig(strategy=ThinkingStrategy.FIXED_TIME, move_time_seconds=seconds),
    )
    assert limits.max_time_seconds == pytest.approx(0.01)


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


@pytest.mark.parametrize(("margin", "expected"), [(0.0, 5.0), (5.0, 0.01), (10.0, 0.01)])
def test_fixed_nodes_clock_budget_stays_within_remaining_time(margin, expected):
    state = _clock_state(TimeControlMode.FISCHER, remaining=5000)
    limits = allocate_search_limits(
        state,
        _time_control(TimeControlMode.FISCHER),
        0,
        1,
        ThinkingConfig(
            strategy=ThinkingStrategy.FIXED_NODES,
            safety_margin_seconds=margin,
        ),
    )
    assert limits.max_time_seconds == pytest.approx(expected)
    assert limits.max_time_seconds <= 5.0


@pytest.mark.parametrize(
    ("remaining", "overtime", "expected"),
    [(5000, 2000, 6.7), (0, 2000, 1.7)],
)
def test_byoyomi_safety_margin_uses_remaining_main_plus_overtime(
    remaining, overtime, expected
):
    state = _clock_state(TimeControlMode.BYOYOMI, remaining=remaining, overtime=overtime)
    limits = allocate_search_limits(
        state,
        _time_control(TimeControlMode.BYOYOMI, overtime=2),
        0,
        1,
        ThinkingConfig(
            strategy=ThinkingStrategy.FIXED_NODES,
            safety_margin_seconds=0.3,
        ),
    )
    assert limits.max_time_seconds == pytest.approx(expected)


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
