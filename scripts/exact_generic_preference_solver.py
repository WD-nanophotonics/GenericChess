"""Bounded, evaluator-free game-theoretic solver for tiny GenericChess roots."""

from __future__ import annotations

import json
import hashlib
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
    max_proof_ply: int = 0
    min_distinguishing_ply: int | None = None


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
    stats = Counter(states_expanded=0, terminal_leaves=0, cycle_edges=0, cap_hits=0, transposition_hits=0, repetition_adjudications=0)
    unresolved = Counter()
    cache: dict[str, tuple[str, int] | None] = {}
    active: set[str] = set()

    def visit(node, depth: int) -> tuple[str, int] | None:
        if stats["states_expanded"] >= max_nodes:
            stats["cap_hits"] += 1
            unresolved["REFERENCE_SOLVE_UNRESOLVED:node_cap"] += 1
            return None
        terminal = _terminal_value(node, compiled, root_actor)
        if terminal is not None:
            stats["terminal_leaves"] += 1
            if terminal_result(node, compiled).status in (TerminalStatus.REPETITION, TerminalStatus.PERPETUAL_CHECK):
                stats["repetition_adjudications"] += 1
            return terminal, 0
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
            stats["transposition_hits"] += 1
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
        best_score = (max if maximizing else min)(VALUE_SCORE[value[0]] for value in values)
        chosen = [value for value in values if VALUE_SCORE[value[0]] == best_score]
        result = next(value for value in VALUES if VALUE_SCORE[value] == best_score)
        solved = result, 1 + max(value[1] for value in chosen)
        cache[key] = solved
        return solved

    root_terminal = _terminal_value(state, compiled, root_actor)
    if root_terminal is not None:
        return SolveResult(False, None, (), (), {**dict(stats), "root_terminal": root_terminal}, "ROOT_ALREADY_TERMINAL")
    root_successors = legal_successors(state, compiled)
    action_values = []
    for action, child in root_successors:
        solved = visit(child, 1)
        action_values.append({"action": action_to_dict(action), "value": solved[0] if solved else None, "proof_depth": solved[1] + 1 if solved else None})
    if any(item["value"] is None for item in action_values):
        reason = next(iter(unresolved), "REFERENCE_SOLVE_UNRESOLVED:unknown")
        return SolveResult(False, None, (), tuple(action_values), {**dict(stats), "unresolved": dict(unresolved)}, reason)
    best_score = max(VALUE_SCORE[item["value"]] for item in action_values)
    root_value = next(value for value in VALUES if VALUE_SCORE[value] == best_score)
    optimal = tuple(item["action"] for item in action_values if item["value"] == root_value)
    proof_depths = [item["proof_depth"] for item in action_values]
    optimal_depths = [item["proof_depth"] for item in action_values if item["value"] == root_value]
    inferior_depths = [item["proof_depth"] for item in action_values if item["value"] != root_value]
    return SolveResult(
        True,
        root_value,
        optimal,
        tuple(action_values),
        {**dict(stats), "unresolved": dict(unresolved), "root_actions": len(action_values)},
        None,
        max(proof_depths, default=0),
        min([depth for depth in optimal_depths for other in inferior_depths if depth != other] or [None]),
    )


def decision_subtree_fingerprint(compiled, state, *, max_nodes: int, max_depth: int) -> str:
    """Return a behavior-only fingerprint for an exactly solved decision tree.

    The fingerprint intentionally omits corpus/provenance/state-identity
    payload, including inert hand counters.  It retains actor role, terminal
    W/D/L outcome, canonical public action signatures, child fingerprints, and
    proof depths.  A bounded or cyclic tree is refused rather than assigned a
    guessed fingerprint.
    """
    root_actor = state.position.side_to_move
    stats = Counter(states_expanded=0)
    cache: dict[str, tuple[str, int, str] | None] = {}
    active: set[str] = set()

    def visit(node, depth: int) -> tuple[str, int, str] | None:
        if stats["states_expanded"] >= max_nodes:
            return None
        terminal = _terminal_value(node, compiled, root_actor)
        key = _state_key(node)
        if terminal is not None:
            payload = {"role": node.position.side_to_move, "terminal_value": terminal, "proof_depth": 0, "actions": []}
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            return terminal, 0, hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        if depth >= max_depth or key in active:
            return None
        if key in cache:
            return cache[key]
        stats["states_expanded"] += 1
        active.add(key)
        children = []
        for action, child in legal_successors(node, compiled):
            solved = visit(child, depth + 1)
            if solved is None:
                active.remove(key)
                cache[key] = None
                return None
            value, child_depth, child_fp = solved
            children.append({
                "action": action_to_dict(action),
                "value": value,
                "proof_depth": child_depth + 1,
                "child": child_fp,
            })
        active.remove(key)
        if not children:
            cache[key] = None
            return None
        maximizing = node.position.side_to_move == root_actor
        best_score = (max if maximizing else min)(VALUE_SCORE[item["value"]] for item in children)
        chosen = [item for item in children if VALUE_SCORE[item["value"]] == best_score]
        value = next(name for name in VALUES if VALUE_SCORE[name] == best_score)
        proof_depth = 1 + max(item["proof_depth"] - 1 for item in chosen)
        payload = {
            "role": node.position.side_to_move,
            "terminal_value": None,
            "value": value,
            "proof_depth": proof_depth,
            "actions": children,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        result = value, proof_depth, hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        cache[key] = result
        return result

    solved = visit(state, 0)
    if solved is None:
        raise ValueError("REFERENCE_SOLVE_UNRESOLVED:decision_subtree_fingerprint")
    return solved[2]
