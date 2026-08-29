"""Correctness-first exact W/D/L solver v2 for tiny GenericChess games.

The historical solver remains the oracle.  This version adds generic terminal
winner mapping, deterministic proof-oriented move ordering, and a bounded
transposition table whose entries retain EXACT/LOWER/UPPER semantics.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from typing import Any

from generic_chess.core.actions import action_to_dict
from generic_chess.core.terminal import TerminalStatus, terminal_result
from generic_chess.core.transition import legal_successors


VALUE_SCORE = {"LOSS": -1, "DRAW": 0, "WIN": 1}
SCORE_VALUE = {-1: "LOSS", 0: "DRAW", 1: "WIN"}


@dataclass(frozen=True)
class ProofSolveResult:
    strong: bool
    root_value: str | None
    optimal_actions: tuple[dict[str, Any], ...]
    action_values: tuple[dict[str, Any], ...]
    stats: dict[str, Any]
    unresolved_reason: str | None = None
    max_proof_ply: int = 0
    min_distinguishing_ply: int | None = None


@dataclass(frozen=True)
class _TTEntry:
    value: int
    flag: str
    proof_depth: int


def _state_key(state) -> str:
    """Full-history identity; no board-only merge is attempted."""
    return repr((state.position, state.ply_count, state.repetition_counts, state.history))


def _terminal_value(state, compiled, root_actor: int):
    result = terminal_result(state, compiled)
    if result.status is TerminalStatus.ONGOING:
        return None, result.status
    if result.winner is not None:
        return ("WIN" if result.winner == root_actor else "LOSS"), result.status
    return "DRAW", result.status


def _action_order(item):
    action, child = item
    terminal = terminal_result(child, item[2]) if len(item) > 2 else None
    status = terminal.status.value if terminal is not None else ""
    encoded = json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))
    return (0 if terminal is not None and terminal.status is not TerminalStatus.ONGOING else 1, status, encoded)


def solve_root_proof_v2(compiled, state, *, max_nodes: int, max_depth: int) -> ProofSolveResult:
    """Solve every root action exactly, or explicitly refuse certification."""

    root_actor = state.position.side_to_move
    stats = Counter(
        states_expanded=0,
        legal_successors_generated=0,
        terminal_leaves=0,
        cycle_edges=0,
        cap_hits=0,
        depth_cap_hits=0,
        node_cap_hits=0,
        exact_tt_hits=0,
        lower_bound_hits=0,
        upper_bound_hits=0,
        proof_cutoffs=0,
        repetition_adjudications=0,
        perpetual_check_adjudications=0,
    )
    terminal_statuses = Counter()
    unresolved = Counter()
    table: dict[tuple[str, int], _TTEntry] = {}
    active: set[str] = set()

    def visit(node, depth: int, alpha: int, beta: int):
        terminal, status = _terminal_value(node, compiled, root_actor)
        if terminal is not None:
            stats["terminal_leaves"] += 1
            terminal_statuses[status.value] += 1
            if status is TerminalStatus.REPETITION:
                stats["repetition_adjudications"] += 1
            if status is TerminalStatus.PERPETUAL_CHECK:
                stats["perpetual_check_adjudications"] += 1
            return VALUE_SCORE[terminal], 0
        if stats["states_expanded"] >= max_nodes:
            stats["cap_hits"] += 1; stats["node_cap_hits"] += 1
            unresolved["REFERENCE_SOLVE_UNRESOLVED:node_cap"] += 1
            return None
        if depth >= max_depth:
            stats["cap_hits"] += 1; stats["depth_cap_hits"] += 1
            unresolved["REFERENCE_SOLVE_UNRESOLVED:depth_cap"] += 1
            return None
        key = (_state_key(node), max_depth - depth)
        state_key = key[0]
        if state_key in active:
            stats["cycle_edges"] += 1
            unresolved["REFERENCE_SOLVE_UNRESOLVED:cycle"] += 1
            return None
        original_alpha, original_beta = alpha, beta
        cached = table.get(key)
        if cached is not None:
            if cached.flag == "EXACT":
                stats["exact_tt_hits"] += 1
                return cached.value, cached.proof_depth
            if cached.flag == "LOWER" and cached.value >= beta:
                stats["lower_bound_hits"] += 1; stats["proof_cutoffs"] += 1
                return cached.value, cached.proof_depth
            if cached.flag == "UPPER" and cached.value <= alpha:
                stats["upper_bound_hits"] += 1; stats["proof_cutoffs"] += 1
                return cached.value, cached.proof_depth
            if cached.flag == "LOWER": alpha = max(alpha, cached.value)
            elif cached.flag == "UPPER": beta = min(beta, cached.value)
            if alpha >= beta:
                stats["proof_cutoffs"] += 1
                return cached.value, cached.proof_depth
        stats["states_expanded"] += 1
        active.add(state_key)
        successors = list(legal_successors(node, compiled))
        stats["legal_successors_generated"] += len(successors)
        if not successors:
            active.remove(state_key)
            unresolved["REFERENCE_SOLVE_UNRESOLVED:no_successors"] += 1
            return None
        maximizing = node.position.side_to_move == root_actor
        ordered = sorted(successors, key=lambda item: (json.dumps(action_to_dict(item[0]), sort_keys=True, separators=(",", ":"))))
        best = -2 if maximizing else 2
        best_depth = 0
        complete = True
        for action, child in ordered:
            solved = visit(child, depth + 1, alpha, beta)
            if solved is None:
                complete = False
                break
            value, proof_depth = solved
            if (maximizing and value > best) or ((not maximizing) and value < best):
                best, best_depth = value, proof_depth
            best_depth = max(best_depth, proof_depth)
            if maximizing:
                alpha = max(alpha, best)
                if best == 1 or alpha >= beta:
                    stats["proof_cutoffs"] += 1
                    break
            else:
                beta = min(beta, best)
                if best == -1 or alpha >= beta:
                    stats["proof_cutoffs"] += 1
                    break
        active.remove(state_key)
        if not complete:
            table[key] = _TTEntry(0, "UPPER" if maximizing else "LOWER", best_depth)
            return None
        if best <= original_alpha:
            flag = "UPPER"
        elif best >= original_beta:
            flag = "LOWER"
        else:
            flag = "EXACT"
        # Extremal proof cutoffs establish the exact node value, even though
        # siblings were skipped; non-extremal bounds retain their flag.
        if (maximizing and best == 1) or ((not maximizing) and best == -1):
            flag = "EXACT"
        table[key] = _TTEntry(best, flag, 1 + best_depth)
        return best, 1 + best_depth

    root_terminal, root_status = _terminal_value(state, compiled, root_actor)
    if root_terminal is not None:
        return ProofSolveResult(False, None, (), (), {**dict(stats), "terminal_statuses": dict(terminal_statuses), "root_terminal": root_status.value}, "ROOT_ALREADY_TERMINAL")
    root_successors = list(legal_successors(state, compiled))
    stats["legal_successors_generated"] += len(root_successors)
    action_values = []
    for action, child in root_successors:
        solved = visit(child, 1, -1, 1)
        action_values.append({"action": action_to_dict(action), "value": SCORE_VALUE[solved[0]] if solved else None, "proof_depth": solved[1] + 1 if solved else None})
    stats["terminal_statuses"] = dict(sorted(terminal_statuses.items()))
    if any(item["value"] is None for item in action_values):
        reason = next(iter(unresolved), "REFERENCE_SOLVE_UNRESOLVED:unknown")
        return ProofSolveResult(False, None, (), tuple(action_values), {**dict(stats), "unresolved": dict(unresolved), "root_actions": len(root_successors)}, reason)
    root_value = SCORE_VALUE[max(VALUE_SCORE[item["value"]] for item in action_values)]
    optimal = tuple(item["action"] for item in action_values if item["value"] == root_value)
    depths = [item["proof_depth"] for item in action_values]
    optimal_depths = [item["proof_depth"] for item in action_values if item["value"] == root_value]
    inferior_depths = [item["proof_depth"] for item in action_values if item["value"] != root_value]
    return ProofSolveResult(True, root_value, optimal, tuple(action_values), {**dict(stats), "unresolved": dict(unresolved), "root_actions": len(root_successors), "tt_entries": len(table), "history_key_mode": "full_state_and_history"}, None, max(depths, default=0), min([depth for depth in optimal_depths for other in inferior_depths if depth != other] or [None]))


__all__ = ["ProofSolveResult", "solve_root_proof_v2"]
