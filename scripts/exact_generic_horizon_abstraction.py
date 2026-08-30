"""Conservative exact threshold proofs with MAX_PLY treated as unknown.

This module is intentionally separate from the authoritative V3 solver.  It
does not assign a value to MAX_PLY; a proof succeeds only when its result is
invariant for every possible continuation beyond that boundary.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from typing import Any

from generic_chess.core.actions import action_to_dict
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalStatus


UNKNOWN = "UNRESOLVED_MAX_PLY"
TRUE = True
FALSE = False


@dataclass(frozen=True)
class AbstractResult:
    strong: bool
    root_value: str | None
    optimal_actions: tuple[dict[str, Any], ...]
    action_values: tuple[dict[str, Any], ...]
    stats: dict[str, Any]
    unresolved_reason: str | None = None
    max_proof_ply: int = 0


def _combine(maximizing: bool, children: list[bool | None]) -> bool | None:
    if maximizing:
        if any(child is TRUE for child in children):
            return TRUE
        return None if any(child is None for child in children) else FALSE
    if any(child is FALSE for child in children):
        return FALSE
    return None if any(child is None for child in children) else TRUE


def _runtime_key(runtime, policy: str):
    key = runtime.search_key()
    repetition = tuple(sorted(runtime.repetition_counts.items(), key=lambda item: repr(item[0])))
    if policy == "continuous_check_loss":
        history = tuple((record.identity, record.actor, record.gave_check) for record in runtime.history)
        return (key.ruleset_fingerprint, key.runtime_hash, key.position_key, repetition, key.ply_count, history)
    return (key.ruleset_fingerprint, key.runtime_hash, key.position_key, repetition, key.ply_count)


def solve_root_horizon_abstract(compiled, state, *, max_nodes: int) -> AbstractResult:
    """Certify every root action while abstracting MAX_PLY continuations."""
    root_actor = state.position.side_to_move
    policy = getattr(compiled, "repetition_policy", None)
    if policy is None:
        policy = getattr(getattr(compiled, "support", None), "repetition_policy", "draw")
    stats = Counter(states_expanded=0, legal_actions_enumerated=0, pushes=0, pops=0,
                    threshold_tt_hits=0, unresolved_cap_hits=0, cycle_refusals=0,
                    abstract_no_successors=0, max_ply_abstract_leaves=0)
    terminal_statuses = Counter()
    unresolved = Counter()
    table: dict[tuple[object, int], bool] = {}
    active: set[tuple[object, int]] = set()
    proof_peak = 0

    def terminal_value(runtime, threshold: int):
        nonlocal proof_peak
        proof_peak = max(proof_peak, runtime.depth)
        terminal = runtime.terminal_status
        if terminal.status is TerminalStatus.ONGOING:
            return "not_terminal"
        terminal_statuses[terminal.status.value] += 1
        if terminal.status is TerminalStatus.MAX_PLY:
            stats["max_ply_abstract_leaves"] += 1
            unresolved[UNKNOWN] += 1
            return UNKNOWN
        if terminal.winner is None:
            value = 0
        else:
            value = 1 if terminal.winner == root_actor else -1
        return TRUE if value >= threshold else FALSE

    def prove_ge(threshold: int, depth: int):
        status = terminal_value(runtime, threshold)
        if status != "not_terminal":
            return None if status == UNKNOWN else status
        if stats["states_expanded"] >= max_nodes:
            stats["unresolved_cap_hits"] += 1
            unresolved["ABSTRACT_NODE_CAP"] += 1
            return None
        key = (_runtime_key(runtime, policy), threshold)
        if key in active:
            stats["cycle_refusals"] += 1
            unresolved["ABSTRACT_CYCLE_REFUSAL"] += 1
            return None
        cached = table.get(key)
        if cached is not None:
            stats["threshold_tt_hits"] += 1
            return cached
        active.add(key)
        stats["states_expanded"] += 1
        actions = runtime.legal_actions()
        stats["legal_actions_enumerated"] += len(actions)
        if not actions:
            active.remove(key)
            stats["abstract_no_successors"] += 1
            unresolved["ABSTRACT_NO_SUCCESSORS"] += 1
            return None
        maximizing = runtime.position.side_to_move == root_actor
        children = []
        for action in sorted(actions, key=lambda item: json.dumps(action_to_dict(item), sort_keys=True, separators=(",", ":"))):
            runtime.push(action)
            stats["pushes"] += 1
            try:
                children.append(prove_ge(threshold, depth + 1))
            finally:
                runtime.pop()
                stats["pops"] = runtime.pops
            if maximizing and children[-1] is TRUE:
                active.remove(key)
                table[key] = TRUE
                return TRUE
            if not maximizing and children[-1] is FALSE:
                active.remove(key)
                table[key] = FALSE
                return FALSE
        active.remove(key)
        result = _combine(maximizing, children)
        if result is not None:
            table[key] = result
        return result

    runtime = SearchPathRuntime.from_state(state, compiled)
    if runtime.terminal_status.status is not TerminalStatus.ONGOING:
        reason = UNKNOWN if runtime.terminal_status.status is TerminalStatus.MAX_PLY else "ROOT_ALREADY_TERMINAL"
        return AbstractResult(False, None, (), (), {"terminal_statuses": {runtime.terminal_status.status.value: 1}, "unresolved": {reason: 1}}, reason)
    root_actions = sorted(runtime.legal_actions(), key=lambda item: json.dumps(action_to_dict(item), sort_keys=True, separators=(",", ":")))
    stats["legal_actions_enumerated"] += len(root_actions)
    rows = []
    for action in root_actions:
        encoded = action_to_dict(action)
        runtime.push(action)
        stats["pushes"] += 1
        try:
            ge_win = prove_ge(1, 1)
            ge_draw = None if ge_win is TRUE else prove_ge(0, 1)
        finally:
            runtime.pop()
            stats["pops"] = runtime.pops
        value = "WIN" if ge_win is TRUE else "LOSS" if ge_draw is FALSE else "DRAW" if ge_draw is TRUE and ge_win is FALSE else None
        rows.append({"action": encoded, "value": value, "ge_win": ge_win, "ge_draw": ge_draw})
    runtime.assert_balanced()
    values = [row["value"] for row in rows]
    strong = all(value is not None for value in values)
    rank = {"LOSS": -1, "DRAW": 0, "WIN": 1}
    root_value = max(values, key=rank.get) if strong else None
    optimal = tuple(row["action"] for row in rows if row["value"] == root_value) if strong else ()
    stats_dict = dict(stats)
    stats_dict.update({"terminal_statuses": dict(sorted(terminal_statuses.items())), "unresolved": dict(sorted(unresolved.items())), "threshold_tt_entries": len(table), "history_key_mode": "FULL_HISTORY_REQUIRED" if policy == "continuous_check_loss" else "REPETITION_COUNTS_SUFFICIENT", "abstract_horizon": True, "max_proof_ply": proof_peak})
    reason = next(iter(unresolved), None) if not strong else None
    return AbstractResult(strong, root_value, optimal, tuple(rows), stats_dict, reason, proof_peak)


def tree_threshold(node, threshold: int) -> bool | None:
    """Pure finite-tree three-valued threshold oracle used by tests."""
    if node[0] == "leaf":
        return None if node[1] == UNKNOWN else node[1] >= threshold
    maximizing, children = node[1], node[2]
    return _combine(maximizing, [tree_threshold(child, threshold) for child in children])


def concrete_tree_value(node, assignments: dict[str, int]) -> int:
    if node[0] == "leaf":
        return assignments.get(node[1], node[1])
    values = [concrete_tree_value(child, assignments) for child in node[2]]
    return (max if node[1] else min)(values)


__all__ = ["UNKNOWN", "AbstractResult", "solve_root_horizon_abstract", "tree_threshold", "concrete_tree_value"]
