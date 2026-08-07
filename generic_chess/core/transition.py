"""State-level transitions: initial state and action application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .actions import Action
from .errors import IllegalActionError, ensure_ruleset_match
from .keys import position_key, semantic_position_key
from .movegen import _apply_action_unchecked, legal_actions_from_position
from .position import GameState
from .repetition import update_repetition_counts
from .terminal import _terminal_from_parts, TerminalStatus

if TYPE_CHECKING:
    from ..rules.compiled import CompiledRuleSet


def initial_state(compiled: "CompiledRuleSet") -> GameState:
    """The initial game state of a compiled ruleset."""
    from .semantic_executor import semantic_engine_for

    engine = semantic_engine_for(compiled)
    if engine is not None:
        from .keys import semantic_position_key

        pos = engine._initial_position()
        key = semantic_position_key(pos, compiled.support, compiled.ir.aux_slots)
        counts = ((key, 1),)
        status = engine.terminal_result(pos, 0, counts)
        return GameState(
            position=pos, ply_count=0, repetition_counts=counts, terminal_status=status
        )
    pos = compiled.initial_position
    key = position_key(pos, compiled)
    counts = ((key, 1),)
    status = _terminal_from_parts(pos, 0, counts, compiled)
    return GameState(position=pos, ply_count=0, repetition_counts=counts, terminal_status=status)


def _transition(state: GameState, action: Action, compiled: "CompiledRuleSet") -> GameState:
    """Mechanically apply an already-validated action and build the child state.

    Shared by :func:`apply_action` and :func:`legal_successors` so the child
    state construction (ply, repetition counts, terminal status) has a single
    source of truth. Callers must ensure the action is legal.
    """
    new_pos = _apply_action_unchecked(state.position, action, compiled)
    ply = state.ply_count + 1
    key = position_key(new_pos, compiled)
    counts = update_repetition_counts(state.repetition_counts, key)
    status = _terminal_from_parts(new_pos, ply, counts, compiled)
    return GameState(position=new_pos, ply_count=ply, repetition_counts=counts, terminal_status=status)


def apply_action(state: GameState, action: Action, compiled: "CompiledRuleSet") -> GameState:
    """Apply one action, returning a brand-new immutable GameState.

    The action is validated against the ruleset (fingerprint match) and the
    full legal-action set before any state is changed.  Uncallable actions
    raise :class:`IllegalActionError`; a state/ruleset mismatch raises
    :class:`RuleSetMismatchError`.
    """
    from .semantic_executor import semantic_action_for, semantic_engine_for

    engine = semantic_engine_for(compiled)
    if engine is not None:
        ensure_ruleset_match(state.position, compiled)
        if state.terminal_status.status is not TerminalStatus.ONGOING:
            raise IllegalActionError(
                f"cannot apply an action to a terminal state ({state.terminal_status})"
            )
        binding = semantic_action_for(engine, state.position, action)
        new_pos = engine.apply(state.position, binding)
        ply = state.ply_count + 1
        key = semantic_position_key(new_pos, compiled.support, compiled.ir.aux_slots)
        counts = update_repetition_counts(state.repetition_counts, key)
        status = engine.terminal_result(new_pos, ply, counts)
        return GameState(
            position=new_pos,
            ply_count=ply,
            repetition_counts=counts,
            terminal_status=status,
        )
    ensure_ruleset_match(state.position, compiled)
    if state.terminal_status.status is not TerminalStatus.ONGOING:
        raise IllegalActionError(
            f"cannot apply an action to a terminal state ({state.terminal_status})"
        )
    if action not in legal_actions_from_position(state.position, compiled):
        raise IllegalActionError(f"action is not legal in the current state: {action}")
    return _transition(state, action, compiled)


def legal_successors(
    state: GameState,
    compiled: "CompiledRuleSet",
) -> tuple[tuple[Action, GameState], ...]:
    """All legal ``(action, child_state)`` pairs for the side to move.

    The actions are exactly the set returned by :func:`legal_actions`; each
    child is the fully validated successor state (fingerprint checked,
    mechanically applied, repetition/terminal updated). Terminal states yield
    an empty tuple. This is the single-source transition path for search
    loops that need both the move and the resulting state without re-running
    move generation for every child.
    """
    from .semantic_executor import (
        _semantic_public_action,
        semantic_engine_for,
    )

    engine = semantic_engine_for(compiled)
    if engine is not None:
        ensure_ruleset_match(state.position, compiled)
        if state.terminal_status.status is not TerminalStatus.ONGOING:
            return ()
        actions = engine.legal_actions(state.position)
        out = []
        for binding in actions:
            new_pos = engine.apply(state.position, binding)
            ply = state.ply_count + 1
            key = semantic_position_key(
                new_pos, compiled.support, compiled.ir.aux_slots
            )
            counts = update_repetition_counts(state.repetition_counts, key)
            status = engine.terminal_result(new_pos, ply, counts)
            out.append(
                (
                    _semantic_public_action(engine, binding),
                    GameState(
                        position=new_pos,
                        ply_count=ply,
                        repetition_counts=counts,
                        terminal_status=status,
                    ),
                )
            )
        return tuple(out)
    ensure_ruleset_match(state.position, compiled)
    if state.terminal_status.status is not TerminalStatus.ONGOING:
        return ()
    actions = legal_actions_from_position(state.position, compiled)
    return tuple((action, _transition(state, action, compiled)) for action in actions)
