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

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

from .actions import Action
from .errors import IllegalActionError, ensure_ruleset_match
from .keys import position_key
from .movegen import iter_legal_actions_from_position
from .position import GameState
from .semantic_executor import semantic_engine_for, _semantic_public_action
from .terminal import TerminalStatus
from .transition import _semantic_transition, _transition
from .keys import semantic_position_key

if TYPE_CHECKING:
    from ..rules.compiled import CompiledRuleSet


_ISSUER = object()
Checkpoint = Callable[[], None]


class LegalSuccessorHandle:
    """A Core-issued, already-verified legal action with lazy child state.

    Callers must not construct handles directly; they are only produced by
    :func:`legal_successor_handles` for the state they belong to.
    """

    __slots__ = (
        "action", "_parent", "_issuer", "_child", "_child_key",
        "_semantic_action", "_semantic_binding",
    )

    def __init__(
        self,
        action: Action,
        parent: GameState,
        *,
        _issuer=None,
        _semantic_action=None,
        _semantic_binding=None,
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
        self._semantic_action = _semantic_action
        self._semantic_binding = _semantic_binding

    @property
    def materialized(self) -> bool:
        return self._child is not None


def legal_successor_handles(
    state: GameState,
    compiled: "CompiledRuleSet",
) -> tuple[LegalSuccessorHandle, ...]:
    """One legal move generation, returning lazily materializable handles."""
    return tuple(iter_legal_successor_handles(state, compiled))


def iter_legal_successor_handles(
    state: GameState,
    compiled: "CompiledRuleSet",
    checkpoint: Checkpoint | None = None,
) -> Iterator[LegalSuccessorHandle]:
    """Stream Core-issued handles without eagerly materializing child states."""
    ensure_ruleset_match(state.position, compiled)
    if state.terminal_status.status is not TerminalStatus.ONGOING:
        return
    engine = semantic_engine_for(compiled)
    if engine is not None:
        for semantic_action, binding in engine.iter_legal_action_bindings(
            state.position, checkpoint=checkpoint
        ):
            if checkpoint is not None:
                checkpoint()
            public_action = _semantic_public_action(engine, semantic_action)
            yield LegalSuccessorHandle(
                public_action,
                state,
                _issuer=_ISSUER,
                _semantic_action=semantic_action,
                _semantic_binding=binding,
            )
        return
    for action in iter_legal_actions_from_position(
        state.position, compiled, checkpoint=checkpoint
    ):
        yield LegalSuccessorHandle(action, state, _issuer=_ISSUER)


def materialize_legal_successor(
    state: GameState,
    handle: LegalSuccessorHandle,
    compiled: "CompiledRuleSet",
    checkpoint: Checkpoint | None = None,
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
        if handle._semantic_binding is not None:
            handle._child = _semantic_transition(
                state,
                handle._semantic_action,
                handle._semantic_binding,
                handle.action,
                compiled,
                checkpoint=checkpoint,
            )
            handle._child_key = semantic_position_key(
                handle._child.position,
                compiled.support,
                compiled.ir.aux_slots,
            )
        else:
            handle._child = _transition(state, handle.action, compiled)
            handle._child_key = position_key(handle._child.position, compiled)
    return handle._child, handle._child_key
