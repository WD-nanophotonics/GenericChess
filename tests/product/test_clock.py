"""MatchClock: modes, deduction, increment, byoyomi, pause/restore, expiry."""

import pytest

from generic_chess.clock import (
    MatchClock,
    SideTimeConfig,
    TimeControl,
    TimeControlMode,
)


class FakeNow:
    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def _clock(mode, main=60, overtime=10, forfeit=True, active=0):
    control = TimeControl(
        mode=mode,
        owner0=SideTimeConfig(main, overtime),
        owner1=SideTimeConfig(main, overtime),
        time_forfeit=forfeit,
    )
    now = FakeNow()
    return MatchClock(control, active_owner=active, now=now), now


def test_none_mode_never_deducts():
    clock, now = _clock(TimeControlMode.NONE)
    now.t += 100.0
    state = clock.state()
    assert state.remaining_ms == (60000, 60000)
    assert not state.running
    assert clock.complete_turn(0) == 0
    assert clock.state().active_owner == 1


def test_byoyomi_deducts_main_then_overtime():
    clock, now = _clock(TimeControlMode.BYOYOMI)
    now.t += 1.5
    state = clock.state()
    assert state.remaining_ms[0] == 58500
    assert state.overtime_remaining_ms[0] == 10000
    clock.complete_turn(0)
    assert clock.state().active_owner == 1
    now.t += 61.0  # owner 1 spends 61s: 60 main + 1 overtime
    state = clock.state()
    assert state.remaining_ms[1] == 0
    assert state.overtime_remaining_ms[1] == 9000
    assert state.expired_owner is None
    now.t += 9.0  # overtime exhausted
    assert clock.state().expired_owner == 1


def test_fischer_increments_main_time():
    clock, now = _clock(TimeControlMode.FISCHER, overtime=3)
    now.t += 2.0
    clock.complete_turn(0)
    state = clock.state()
    assert state.remaining_ms[0] == 61000  # 60000 - 2000 + 3000
    assert state.active_owner == 1


def test_complete_turn_mover_mismatch_raises():
    clock, _ = _clock(TimeControlMode.BYOYOMI, active=0)
    with pytest.raises(ValueError):
        clock.complete_turn(1)


def test_pause_and_resume():
    clock, now = _clock(TimeControlMode.BYOYOMI)
    now.t += 1.0
    clock.pause()
    frozen = clock.state().remaining_ms[0]
    now.t += 10.0
    assert clock.state().remaining_ms[0] == frozen
    clock.resume()
    now.t += 1.0
    assert clock.state().remaining_ms[0] == frozen - 1000


def test_restore_snapshot():
    clock, now = _clock(TimeControlMode.BYOYOMI)
    now.t += 2.0
    clock.complete_turn(0)
    snapshot = clock.state()
    now.t += 3.0
    clock.restore(snapshot)
    restored = clock.state()
    assert restored.remaining_ms == snapshot.remaining_ms
    assert restored.active_owner == snapshot.active_owner


def test_time_forfeit_disabled_never_expires():
    clock, now = _clock(TimeControlMode.BYOYOMI, forfeit=False)
    now.t += 10_000.0
    assert clock.state().expired_owner is None
