"""Qt-free deterministic match clock (inspired by alphasho's engine.clock).

The clock is match-level infrastructure, not game rules: it never enters
positions, records or Core.  A callable ``now()`` (default
``time.monotonic``) can be injected so tests use a fake clock.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


class TimeControlMode(StrEnum):
    NONE = "none"
    FISCHER = "fischer"
    BYOYOMI = "byoyomi"


@dataclass(frozen=True, slots=True)
class SideTimeConfig:
    main_seconds: int = 600
    overtime_seconds: int = 30


@dataclass(frozen=True, slots=True)
class TimeControl:
    mode: TimeControlMode = TimeControlMode.NONE
    owner0: SideTimeConfig = SideTimeConfig()
    owner1: SideTimeConfig = SideTimeConfig()
    time_forfeit: bool = True

    def for_owner(self, owner: int) -> SideTimeConfig:
        return self.owner0 if owner == 0 else self.owner1


@dataclass(frozen=True, slots=True)
class ClockState:
    remaining_ms: tuple[int, int]
    overtime_remaining_ms: tuple[int, int]
    active_owner: int
    running: bool
    expired_owner: int | None = None

    def remaining_for(self, owner: int) -> int:
        return self.remaining_ms[owner]

    def overtime_for(self, owner: int) -> int:
        return self.overtime_remaining_ms[owner]


class MatchClock:
    """Two-sided clock: main time + optional overtime (byoyomi) / increment (fischer)."""

    def __init__(
        self,
        control: TimeControl,
        *,
        active_owner: int = 0,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        if active_owner not in (0, 1):
            raise ValueError("active_owner must be 0 or 1")
        self._control = control
        self._now = now
        self._remaining = [
            control.for_owner(0).main_seconds * 1000,
            control.for_owner(1).main_seconds * 1000,
        ]
        self._overtime = [
            control.for_owner(0).overtime_seconds * 1000,
            control.for_owner(1).overtime_seconds * 1000,
        ]
        self._active = active_owner
        self._running = control.mode is not TimeControlMode.NONE
        self._started_at = now()
        self._turn_elapsed_ms = 0

    def state(self) -> ClockState:
        remaining = list(self._remaining)
        overtime = list(self._overtime)
        if self._running:
            self._deduct(
                self._active,
                self._elapsed_since_start(),
                remaining,
                overtime,
                self._control.mode,
            )
        expired = self._expired_owner(remaining, overtime)
        return ClockState(
            remaining_ms=(max(0, remaining[0]), max(0, remaining[1])),
            overtime_remaining_ms=(max(0, overtime[0]), max(0, overtime[1])),
            active_owner=self._active,
            running=self._running,
            expired_owner=expired,
        )

    def complete_turn(self, mover: int) -> int:
        """Commit the mover's elapsed time, apply the control, and switch sides.

        Returns the committed elapsed time in whole seconds (for display).
        """
        if mover not in (0, 1):
            raise ValueError("mover must be 0 or 1")
        if mover != self._active:
            raise ValueError("clock mover does not match the active side")
        self._commit_elapsed()
        elapsed = self._turn_elapsed_ms
        side = self._control.for_owner(mover)
        if self._control.mode is TimeControlMode.FISCHER:
            self._remaining[mover] += side.overtime_seconds * 1000
        elif self._control.mode is TimeControlMode.BYOYOMI:
            self._overtime[mover] = side.overtime_seconds * 1000
        self._active = 1 - mover
        self._turn_elapsed_ms = 0
        self._started_at = self._now()
        self._running = self._control.mode is not TimeControlMode.NONE
        return max(0, (elapsed + 999) // 1000)

    def pause(self) -> None:
        if not self._running:
            return
        self._commit_elapsed()
        self._running = False

    def resume(self) -> None:
        if self._running or self._control.mode is TimeControlMode.NONE:
            return
        self._started_at = self._now()
        self._running = True

    def restore(self, state: ClockState) -> None:
        self._remaining = list(state.remaining_ms)
        self._overtime = list(state.overtime_remaining_ms)
        self._active = state.active_owner
        self._running = state.running and self._control.mode is not TimeControlMode.NONE
        self._turn_elapsed_ms = 0
        self._started_at = self._now()

    @property
    def active_owner(self) -> int:
        return self._active

    def _commit_elapsed(self) -> None:
        if not self._running:
            return
        elapsed = self._elapsed_since_start()
        remaining = list(self._remaining)
        overtime = list(self._overtime)
        self._deduct(self._active, elapsed, remaining, overtime, self._control.mode)
        self._remaining = remaining
        self._overtime = overtime
        self._turn_elapsed_ms += elapsed
        self._started_at = self._now()

    def _elapsed_since_start(self) -> int:
        return max(0, int((self._now() - self._started_at) * 1000))

    @staticmethod
    def _deduct(
        owner: int,
        elapsed: int,
        remaining: list[int],
        overtime: list[int],
        mode: TimeControlMode,
    ) -> None:
        if mode is TimeControlMode.FISCHER:
            remaining[owner] -= elapsed
            return
        if mode is TimeControlMode.BYOYOMI:
            main_used = min(max(0, remaining[owner]), elapsed)
            remaining[owner] -= main_used
            overtime[owner] -= elapsed - main_used

    def _expired_owner(
        self,
        remaining: list[int],
        overtime: list[int],
    ) -> int | None:
        if not self._control.time_forfeit:
            return None
        mode = self._control.mode
        for owner in (0, 1):
            if mode is TimeControlMode.FISCHER and remaining[owner] <= 0:
                return owner
            if mode is TimeControlMode.BYOYOMI and remaining[owner] <= 0 and overtime[owner] <= 0:
                return owner
        return None
