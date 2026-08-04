"""State-level transitions: initial state and action application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .actions import Action
from .errors import IllegalActionError, ensure_ruleset_match
from .keys import position_key
from .movegen import _apply_action_unchecked, legal_actions_from_position
from .position import GameState
from .repetition import update_repetition_counts
from .terminal import _terminal_from_parts, TerminalStatus

if TYPE_CHECKING:
    from ..rules.compiled import CompiledRuleSet


def initial_state(compiled: "CompiledRuleSet") -> GameState:
    """The initial game state of a compiled ruleset."""
    pos = compiled.initial_position
    key = position_key(pos, compiled)
    counts = ((key, 1),)
    status = _terminal_from_parts(pos, 0, counts, compiled)
    return GameState(position=pos, ply_count=0, repetition_counts=counts, terminal_status=status)


def apply_action(state: GameState, action: Action, compiled: "CompiledRuleSet") -> GameState:
    """Apply one action, returning a brand-new immutable GameState.

    The action is validated against the ruleset (fingerprint match) and the
    full legal-action set before any state is changed.  Uncallable actions
    raise :class:`IllegalActionError`; a state/ruleset mismatch raises
    :class:`RuleSetMismatchError`.
    """
    ensure_ruleset_match(state.position, compiled)
    if state.terminal_status.status is not TerminalStatus.ONGOING:
        raise IllegalActionError(
            f"cannot apply an action to a terminal state ({state.terminal_status})"
        )
    if action not in legal_actions_from_position(state.position, compiled):
        raise IllegalActionError(f"action is not legal in the current state: {action}")
    new_pos = _apply_action_unchecked(state.position, action, compiled)
    ply = state.ply_count + 1
    key = position_key(new_pos, compiled)
    counts = update_repetition_counts(state.repetition_counts, key)
    status = _terminal_from_parts(new_pos, ply, counts, compiled)
    return GameState(position=new_pos, ply_count=ply, repetition_counts=counts, terminal_status=status)
