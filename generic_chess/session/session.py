"""Stateful GameSession built on top of Core's public API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.actions import Action
from ..core.errors import IllegalActionError
from ..core.identity import position_identity_key
from ..core.movegen import legal_actions
from ..core.position import GameState
from ..core.transition import apply_action, initial_state
from ..core.declarations import assess_declaration, available_declarations
from .record import ActionRecord, DeclarationRecord, GameRecord
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

    __slots__ = (
        "_compiled",
        "_state",
        "_history",
        "_resigned_by",
        "_declaration",
        "_search_history_witnesses",
    )

    def __init__(self, compiled: "CompiledRuleSet") -> None:
        self._compiled = compiled
        self._state: GameState = initial_state(compiled)
        self._search_history_witnesses = (self._state.position,)
        self._history: tuple[ActionRecord, ...] = ()
        self._resigned_by: int | None = None
        self._declaration: DeclarationRecord | None = None

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
        if self._declaration is not None:
            declaration = self._declaration
            winner = declaration.declared_by if declaration.outcome == "WIN" else (
                1 - declaration.declared_by if declaration.outcome == "LOSS" else None
            )
            return SessionResult(
                status=SessionStatus.DECLARATION,
                winner=winner,
                declaration_id=declaration.declaration_id,
                declared_by=declaration.declared_by,
                declaration_outcome=declaration.outcome,
                declaration_score=declaration.weighted_score,
            )
        return session_result_from_terminal(self._state.terminal_status)

    def legal_actions(self) -> tuple[Action, ...]:
        if self.result.status is not SessionStatus.ONGOING:
            return ()
        return tuple(legal_actions(self._state, self._compiled))

    def available_declarations(self):
        if self.result.status is not SessionStatus.ONGOING:
            return ()
        return available_declarations(self._state, self._compiled)

    def declare(self, declaration_id: str) -> SessionResult:
        if self.result.status is not SessionStatus.ONGOING:
            raise SessionFinishedError(
                f"cannot declare in a finished session ({self.result})"
            )
        assessment = assess_declaration(self._state, self._compiled, declaration_id)
        # Commit only the session-level terminal marker.  The authoritative
        # GameState and its history are intentionally untouched.
        self._declaration = DeclarationRecord(
            declaration_id=assessment.declaration_id,
            declared_by=assessment.actor,
            outcome=assessment.outcome,
            weighted_score=assessment.weighted_score,
        )
        return self.result

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
        self._search_history_witnesses = self._search_history_witnesses + (
            new_state.position,
        )
        return new_state

    @property
    def _search_witnesses(self):
        """Private exact positions for the Core-owned search runtime."""
        return self._search_history_witnesses

    def resign(self) -> SessionResult:
        if self._resigned_by is not None:
            raise SessionFinishedError("the session already ended by resignation")
        if self.result.status is not SessionStatus.ONGOING:
            raise SessionFinishedError(f"cannot resign after the game ended ({self.result})")
        self._resigned_by = self._state.position.side_to_move
        return self.result

    def to_record(self) -> GameRecord:
        return GameRecord(
            schema_version=2 if self._declaration is not None else 1,
            ruleset_fingerprint=self._compiled.ruleset_fingerprint,
            actions=tuple(rec.action for rec in self._history),
            resigned_by=self._resigned_by,
            declaration=self._declaration,
        )

    @classmethod
    def replay(cls, compiled: "CompiledRuleSet", record: GameRecord) -> "GameSession":
        """Rebuild a session by replaying a record through ``submit``."""
        if record.schema_version not in (1, 2):
            raise SessionRecordError(
                f"unsupported game record schema_version {record.schema_version!r}"
            )
        if record.schema_version == 2 and record.declaration is None:
            raise SessionRecordError("schema v2 requires a declaration")
        if record.schema_version == 1 and record.declaration is not None:
            raise SessionRecordError("schema v1 cannot contain a declaration")
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
        if record.declaration is not None:
            if record.schema_version != 2:
                raise SessionRecordError("declaration requires game record schema_version 2")
            if record.resigned_by is not None:
                raise SessionRecordError("record cannot contain resignation and declaration")
            if session.result.status is not SessionStatus.ONGOING:
                raise SessionRecordError(
                    "record declares a declaration after the game already ended"
                )
            try:
                result = session.declare(record.declaration.declaration_id)
            except (SessionFinishedError, IllegalActionError, ValueError) as exc:
                raise SessionRecordError(f"record declaration cannot be replayed: {exc}") from exc
            actual = session._declaration
            expected = record.declaration
            if (
                actual is None
                or actual.declared_by != expected.declared_by
                or actual.outcome != expected.outcome
                or actual.weighted_score != expected.weighted_score
            ):
                raise SessionRecordError(
                    "record declaration does not match the authoritative assessment"
                )
        return session
