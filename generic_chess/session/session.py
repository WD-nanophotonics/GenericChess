"""Stateful GameSession built on top of Core's public API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.actions import Action
from ..core.errors import IllegalActionError
from ..core.identity import position_identity_key
from ..core.movegen import legal_actions
from ..core.position import GameState
from ..core.transition import apply_action, initial_state
from .record import ActionRecord, GameRecord
from .result import SessionResult, SessionStatus, session_result_from_terminal

if TYPE_CHECKING:
    from ..rules.compiled import CompiledRuleSet


class SessionFinishedError(ValueError):
    """Raised when an action or resignation is attempted on a finished session."""


class SessionRecordError(ValueError):
    """Raised when a game record is malformed or cannot be replayed."""


class GameSession:
    """A stateful, boundary-clear session around one compiled ruleset.

    All state mutations happen through ``submit`` / ``resign``; failures never
    leave a partially updated session.  Core's GameState / Position / Action
    values remain immutable.
    """

    __slots__ = ("_compiled", "_state", "_history", "_resigned_by")

    def __init__(self, compiled: "CompiledRuleSet") -> None:
        self._compiled = compiled
        self._state: GameState = initial_state(compiled)
        self._history: tuple[ActionRecord, ...] = ()
        self._resigned_by: int | None = None

    @property
    def compiled(self) -> "CompiledRuleSet":
        return self._compiled

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def history(self) -> tuple[ActionRecord, ...]:
        return self._history

    @property
    def result(self) -> SessionResult:
        if self._resigned_by is not None:
            return SessionResult(
                status=SessionStatus.RESIGNATION,
                winner=1 - self._resigned_by,
                resigned_by=self._resigned_by,
            )
        return session_result_from_terminal(self._state.terminal_status)

    def legal_actions(self) -> tuple[Action, ...]:
        return tuple(legal_actions(self._state, self._compiled))

    def submit(self, action: Action) -> GameState:
        if self.result.status is not SessionStatus.ONGOING:
            raise SessionFinishedError(f"cannot submit an action to a finished session ({self.result})")
        before_key = position_identity_key(self._state.position, self._compiled)
        player = self._state.position.side_to_move
        new_state = apply_action(self._state, action, self._compiled)
        after_key = position_identity_key(new_state.position, self._compiled)
        record = ActionRecord(
            ply=len(self._history) + 1,
            player=player,
            action=action,
            before_key=before_key,
            after_key=after_key,
        )
        # Commit only after every Core call succeeded.
        self._state = new_state
        self._history = self._history + (record,)
        return new_state

    def resign(self) -> SessionResult:
        if self._resigned_by is not None:
            raise SessionFinishedError("the session already ended by resignation")
        if self._state.terminal_status.is_terminal:
            raise SessionFinishedError(f"cannot resign after the game ended ({self.result})")
        self._resigned_by = self._state.position.side_to_move
        return self.result

    def to_record(self) -> GameRecord:
        return GameRecord(
            schema_version=1,
            ruleset_fingerprint=self._compiled.ruleset_fingerprint,
            actions=tuple(rec.action for rec in self._history),
            resigned_by=self._resigned_by,
        )

    @classmethod
    def replay(cls, compiled: "CompiledRuleSet", record: GameRecord) -> "GameSession":
        """Rebuild a session by replaying a record through ``submit``."""
        if record.schema_version != 1:
            raise SessionRecordError(
                f"unsupported game record schema_version {record.schema_version!r}"
            )
        if record.ruleset_fingerprint != compiled.ruleset_fingerprint:
            raise SessionRecordError(
                f"record fingerprint {record.ruleset_fingerprint!r} does not match "
                f"ruleset fingerprint {compiled.ruleset_fingerprint!r}"
            )
        session = cls(compiled)
        try:
            for action in record.actions:
                session.submit(action)
        except SessionFinishedError as exc:
            raise SessionRecordError(
                f"record contains an action after the game ended: {exc}"
            ) from exc
        except IllegalActionError as exc:
            raise SessionRecordError(f"record contains an illegal action: {exc}") from exc

        if record.resigned_by is not None:
            if session.result.status is not SessionStatus.ONGOING:
                raise SessionRecordError(
                    "record declares a resignation after the game already ended"
                )
            if record.resigned_by != session._state.position.side_to_move:
                raise SessionRecordError(
                    f"record resigned_by {record.resigned_by} is not the side to move "
                    f"({session._state.position.side_to_move})"
                )
            session.resign()
        return session
