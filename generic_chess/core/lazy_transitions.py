"""Core-managed verified action handles with lazy child materialization.

The experiment behind this module: main-search alpha-beta cutoffs often mean
many legal children of a node are never searched.  ``legal_successor_handles``
performs the single legal move generation and returns Core-issued handles; the
child state (transition + terminal + repetition) is only materialized when the
search actually explores the action.  Legality stays inside Core: handles are
only created from the official legal-action set, and materialization is
identity-bound to the generating state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .actions import Action
from .errors import IllegalActionError, ensure_ruleset_match
from .keys import position_key
from .movegen import legal_actions_from_position
from .position import GameState
from .terminal import TerminalStatus
from .transition import _transition

if TYPE_CHECKING:
    from ..rules.compiled import CompiledRuleSet


_ISSUER = object()


class LegalSuccessorHandle:
    """A Core-issued, already-verified legal action with lazy child state.

    Callers must not construct handles directly; they are only produced by
    :func:`legal_successor_handles` for the state they belong to.
    """

    __slots__ = ("action", "_parent", "_issuer", "_child", "_child_key")

    def __init__(
        self,
        action: Action,
        parent: GameState,
        *,
        _issuer=None,
    ) -> None:
        if _issuer is not _ISSUER:
            raise TypeError(
                "LegalSuccessorHandle must be issued by Core; "
                "construct it only via legal_successor_handles()"
            )
        self.action = action
        self._parent = parent
        self._issuer = _issuer
        self._child: GameState | None = None
        self._child_key: str | None = None

    @property
    def materialized(self) -> bool:
        return self._child is not None


def legal_successor_handles(
    state: GameState,
    compiled: "CompiledRuleSet",
) -> tuple[LegalSuccessorHandle, ...]:
    """One legal move generation, returning lazily materializable handles."""
    ensure_ruleset_match(state.position, compiled)
    if state.terminal_status.status is not TerminalStatus.ONGOING:
        return ()
    actions = legal_actions_from_position(state.position, compiled)
    return tuple(
        LegalSuccessorHandle(action, state, _issuer=_ISSUER) for action in actions
    )


def materialize_legal_successor(
    state: GameState,
    handle: LegalSuccessorHandle,
    compiled: "CompiledRuleSet",
) -> tuple[GameState, str]:
    """Materialize (once) the verified child state and its position key."""
    ensure_ruleset_match(state.position, compiled)
    if handle._issuer is not _ISSUER:
        raise IllegalActionError(
            "legal successor handle was not issued by Core"
        )
    if handle._parent is not state:
        raise IllegalActionError(
            "legal successor handle does not belong to the given state"
        )
    if handle._child is None:
        handle._child = _transition(state, handle.action, compiled)
        handle._child_key = position_key(handle._child.position, compiled)
    return handle._child, handle._child_key
