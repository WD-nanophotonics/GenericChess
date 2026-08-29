"""Bounded, evaluator-free game-theoretic solver for tiny GenericChess roots."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from typing import Any

from generic_chess.core.actions import action_to_dict
from generic_chess.core.terminal import TerminalStatus, terminal_result
from generic_chess.core.transition import legal_successors


VALUES = ("LOSS", "DRAW", "WIN")
VALUE_SCORE = {value: index - 1 for index, value in enumerate(VALUES)}


@dataclass(frozen=True)
class SolveResult:
    strong: bool
    root_value: str | None
    optimal_actions: tuple[dict[str, Any], ...]
    action_values: tuple[dict[str, Any], ...]
    stats: dict[str, Any]
    unresolved_reason: str | None = None


def _state_key(state) -> str:
    # Includes the complete history context rather than only board material.
    return repr((state.position, state.ply_count, state.repetition_counts, state.history))


def _terminal_value(state, compiled, root_actor: int) -> str | None:
    status = terminal_result(state, compiled)
    if status.status is TerminalStatus.CHECKMATE:
        return "WIN" if status.winner == root_actor else "LOSS"
    if status.status is not TerminalStatus.ONGOING:
        return "DRAW"
    return None


def solve_root(compiled, state, *, max_nodes: int, max_depth: int) -> SolveResult:
    """Exhaustively solve a finite bounded tree, or explicitly refuse it.

    Every root action is evaluated.  A back-edge is unresolved rather than
    guessed as a draw; only authoritative terminal adjudication may produce a
    draw.  W/D/L ties are preserved without distance tie-breaking.
    """
    root_actor = state.position.side_to_move
    stats = Counter(states_expanded=0, terminal_leaves=0, cycle_edges=0, cap_hits=0)
    unresolved = Counter()
    cache: dict[str, str | None] = {}
    active: set[str] = set()

    def visit(node, depth: int) -> str | None:
        if stats["states_expanded"] >= max_nodes:
            stats["cap_hits"] += 1
            unresolved["REFERENCE_SOLVE_UNRESOLVED:node_cap"] += 1
            return None
        terminal = _terminal_value(node, compiled, root_actor)
        if terminal is not None:
            stats["terminal_leaves"] += 1
            return terminal
        if depth >= max_depth:
            stats["cap_hits"] += 1
            unresolved["REFERENCE_SOLVE_UNRESOLVED:depth_cap"] += 1
            return None
        key = _state_key(node)
        if key in active:
            stats["cycle_edges"] += 1
            unresolved["REFERENCE_SOLVE_UNRESOLVED:cycle"] += 1
            return None
        if key in cache:
            return cache[key]
        stats["states_expanded"] += 1
        active.add(key)
        successors = legal_successors(node, compiled)
        values = [visit(child, depth + 1) for _action, child in successors]
        active.remove(key)
        if not values or any(value is None for value in values):
            cache[key] = None
            return None
        maximizing = node.position.side_to_move == root_actor
        best_score = (max if maximizing else min)(VALUE_SCORE[value] for value in values)
        result = next(value for value in VALUES if VALUE_SCORE[value] == best_score)
        cache[key] = result
        return result

    root_terminal = _terminal_value(state, compiled, root_actor)
    if root_terminal is not None:
        return SolveResult(False, None, (), (), {**dict(stats), "root_terminal": root_terminal}, "ROOT_ALREADY_TERMINAL")
    root_successors = legal_successors(state, compiled)
    action_values = []
    for action, child in root_successors:
        value = visit(child, 1)
        action_values.append({"action": action_to_dict(action), "value": value})
    if any(item["value"] is None for item in action_values):
        reason = next(iter(unresolved), "REFERENCE_SOLVE_UNRESOLVED:unknown")
        return SolveResult(False, None, (), tuple(action_values), {**dict(stats), "unresolved": dict(unresolved)}, reason)
    best_score = max(VALUE_SCORE[item["value"]] for item in action_values)
    root_value = next(value for value in VALUES if VALUE_SCORE[value] == best_score)
    optimal = tuple(item["action"] for item in action_values if item["value"] == root_value)
    return SolveResult(
        True,
        root_value,
        optimal,
        tuple(action_values),
        {**dict(stats), "unresolved": dict(unresolved), "root_actions": len(action_values)},
    )
