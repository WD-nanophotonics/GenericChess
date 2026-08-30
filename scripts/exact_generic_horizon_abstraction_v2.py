"""Proof-local MAX_PLY abstraction for the F23R corrective checkpoint."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from typing import Any

from generic_chess.core.actions import action_to_dict
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalStatus


PROVED_TRUE = "PROVED_TRUE"
PROVED_FALSE = "PROVED_FALSE"
UNRESOLVED = "UNRESOLVED"
MAX_PLY_ABSTRACT_LEAF = "MAX_PLY_ABSTRACT_LEAF"
ABSTRACT_NODE_CAP = "ABSTRACT_NODE_CAP"
ABSTRACT_CYCLE_REFUSAL = "ABSTRACT_CYCLE_REFUSAL"
ABSTRACT_NO_SUCCESSORS = "ABSTRACT_NO_SUCCESSORS"
ABSTRACT_TIME_CAP = "ABSTRACT_TIME_CAP"
ABSTRACT_WORKER_FAILURE = "ABSTRACT_WORKER_FAILURE"
OTHER_ABSTRACT_UNRESOLVED = "OTHER_ABSTRACT_UNRESOLVED"
CAUSES = frozenset({
    MAX_PLY_ABSTRACT_LEAF,
    ABSTRACT_NODE_CAP,
    ABSTRACT_CYCLE_REFUSAL,
    ABSTRACT_NO_SUCCESSORS,
    ABSTRACT_TIME_CAP,
    ABSTRACT_WORKER_FAILURE,
    OTHER_ABSTRACT_UNRESOLVED,
})


@dataclass(frozen=True)
class ThresholdProof:
    status: str
    necessary_unresolved_causes: frozenset[str] = frozenset()
    proof_depth: int = 0


@dataclass(frozen=True)
class AbstractResult:
    strong: bool
    root_value: str | None
    optimal_actions: tuple[dict[str, Any], ...]
    action_values: tuple[dict[str, Any], ...]
    stats: dict[str, Any]
    unresolved_reason: str | None = None
    root_unresolved_causes: frozenset[str] = frozenset()
    max_proof_ply: int = 0


def _combine(maximizing: bool, children: list[ThresholdProof]) -> ThresholdProof:
    unresolved = frozenset().union(*(child.necessary_unresolved_causes for child in children if child.status == UNRESOLVED))
    for child in children:
        if maximizing and child.status == PROVED_TRUE:
            return ThresholdProof(PROVED_TRUE, proof_depth=max((item.proof_depth for item in children), default=0))
        if not maximizing and child.status == PROVED_FALSE:
            return ThresholdProof(PROVED_FALSE, proof_depth=max((item.proof_depth for item in children), default=0))
    if unresolved:
        return ThresholdProof(UNRESOLVED, unresolved, max((item.proof_depth for item in children), default=0))
    return ThresholdProof(PROVED_FALSE if maximizing else PROVED_TRUE, proof_depth=max((item.proof_depth for item in children), default=0))


def _runtime_key(runtime, policy: str):
    key = runtime.search_key()
    repetition = tuple(sorted(runtime.repetition_counts.items(), key=lambda item: repr(item[0])))
    if policy == "continuous_check_loss":
        history = tuple((record.identity, record.actor, record.gave_check) for record in runtime.history)
        return (key.ruleset_fingerprint, key.runtime_hash, key.position_key, repetition, key.ply_count, history)
    return (key.ruleset_fingerprint, key.runtime_hash, key.position_key, repetition, key.ply_count)


def _status(proof: ThresholdProof) -> str:
    return proof.status


def solve_root_horizon_abstract_v2(compiled, state, *, max_nodes: int, use_tt: bool = True, reverse_actions: bool = False) -> AbstractResult:
    """Return action-level threshold proofs with necessary unresolved causes."""
    root_actor = state.position.side_to_move
    policy = getattr(compiled, "repetition_policy", None)
    if policy is None:
        policy = getattr(getattr(compiled, "support", None), "repetition_policy", "draw")
    stats = Counter(states_expanded=0, legal_actions_enumerated=0, pushes=0, pops=0,
                    threshold_tt_hits=0, unresolved_cap_hits=0, cycle_refusals=0,
                    max_ply_abstract_leaves=0)
    terminal_statuses = Counter()
    table: dict[tuple[object, int], str] = {}
    active: set[tuple[object, int]] = set()
    proof_peak = 0

    def prove_ge(runtime, threshold: int, depth: int) -> ThresholdProof:
        nonlocal proof_peak
        proof_peak = max(proof_peak, runtime.depth)
        terminal = runtime.terminal_status
        if terminal.status is not TerminalStatus.ONGOING:
            terminal_statuses[terminal.status.value] += 1
            if terminal.status is TerminalStatus.MAX_PLY:
                stats["max_ply_abstract_leaves"] += 1
                return ThresholdProof(UNRESOLVED, frozenset({MAX_PLY_ABSTRACT_LEAF}), runtime.depth)
            value = 0 if terminal.winner is None else (1 if terminal.winner == root_actor else -1)
            return ThresholdProof(PROVED_TRUE if value >= threshold else PROVED_FALSE, proof_depth=runtime.depth)
        if stats["states_expanded"] >= max_nodes:
            stats["unresolved_cap_hits"] += 1
            return ThresholdProof(UNRESOLVED, frozenset({ABSTRACT_NODE_CAP}), runtime.depth)
        key = (_runtime_key(runtime, policy), threshold)
        if key in active:
            stats["cycle_refusals"] += 1
            return ThresholdProof(UNRESOLVED, frozenset({ABSTRACT_CYCLE_REFUSAL}), runtime.depth)
        cached = table.get(key) if use_tt else None
        if cached is not None:
            stats["threshold_tt_hits"] += 1
            return ThresholdProof(cached, proof_depth=runtime.depth)
        active.add(key)
        stats["states_expanded"] += 1
        actions = runtime.legal_actions()
        stats["legal_actions_enumerated"] += len(actions)
        if not actions:
            active.remove(key)
            return ThresholdProof(UNRESOLVED, frozenset({ABSTRACT_NO_SUCCESSORS}), runtime.depth)
        ordered = sorted(actions, key=lambda item: json.dumps(action_to_dict(item), sort_keys=True, separators=(",", ":")), reverse=reverse_actions)
        maximizing = runtime.position.side_to_move == root_actor
        children: list[ThresholdProof] = []
        for action in ordered:
            runtime.push(action)
            stats["pushes"] += 1
            try:
                child = prove_ge(runtime, threshold, depth + 1)
            finally:
                runtime.pop()
                stats["pops"] = runtime.pops
            children.append(child)
            if maximizing and child.status == PROVED_TRUE:
                active.remove(key)
                if use_tt:
                    table[key] = PROVED_TRUE
                return ThresholdProof(PROVED_TRUE, proof_depth=max(item.proof_depth for item in children))
            if not maximizing and child.status == PROVED_FALSE:
                active.remove(key)
                if use_tt:
                    table[key] = PROVED_FALSE
                return ThresholdProof(PROVED_FALSE, proof_depth=max(item.proof_depth for item in children))
        active.remove(key)
        result = _combine(maximizing, children)
        if result.status != UNRESOLVED and use_tt:
            table[key] = result.status
        return result

    runtime = SearchPathRuntime.from_state(state, compiled)
    if runtime.terminal_status.status is not TerminalStatus.ONGOING:
        reason = frozenset({MAX_PLY_ABSTRACT_LEAF}) if runtime.terminal_status.status is TerminalStatus.MAX_PLY else frozenset({OTHER_ABSTRACT_UNRESOLVED})
        return AbstractResult(False, None, (), (), {"terminal_statuses": {runtime.terminal_status.status.value: 1}}, UNRESOLVED, reason)
    root_actions = sorted(runtime.legal_actions(), key=lambda item: json.dumps(action_to_dict(item), sort_keys=True, separators=(",", ":")), reverse=reverse_actions)
    stats["legal_actions_enumerated"] += len(root_actions)
    rows = []
    for action in root_actions:
        runtime.push(action)
        stats["pushes"] += 1
        try:
            ge_win = prove_ge(runtime, 1, 1)
            ge_draw = ThresholdProof(PROVED_TRUE) if ge_win.status == PROVED_TRUE else prove_ge(runtime, 0, 1)
        finally:
            runtime.pop()
            stats["pops"] = runtime.pops
        if ge_win.status == PROVED_TRUE:
            value = "WIN"
        elif ge_draw.status == PROVED_FALSE:
            value = "LOSS"
        elif ge_draw.status == PROVED_TRUE and ge_win.status == PROVED_FALSE:
            value = "DRAW"
        else:
            value = None
        causes = frozenset().union(ge_win.necessary_unresolved_causes, ge_draw.necessary_unresolved_causes)
        rows.append({
            "action": action_to_dict(action),
            "value": value,
            "ge_win": {"status": _status(ge_win), "necessary_unresolved_causes": sorted(ge_win.necessary_unresolved_causes)},
            "ge_draw": {"status": _status(ge_draw), "necessary_unresolved_causes": sorted(ge_draw.necessary_unresolved_causes)},
            "necessary_unresolved_causes": sorted(causes),
            "max_ply_dependency": MAX_PLY_ABSTRACT_LEAF in causes,
            "proof_depth": max(ge_win.proof_depth, ge_draw.proof_depth),
        })
    runtime.assert_balanced()
    strong = all(row["value"] is not None for row in rows)
    rank = {"LOSS": -1, "DRAW": 0, "WIN": 1}
    root_value = max((row["value"] for row in rows), key=rank.get) if strong else None
    optimal = tuple(row["action"] for row in rows if row["value"] == root_value) if strong else ()
    root_causes = frozenset().union(*(row["necessary_unresolved_causes"] for row in rows if row["value"] is None))
    stats_dict = dict(stats)
    stats_dict.update({
        "terminal_statuses": dict(sorted(terminal_statuses.items())),
        "threshold_tt_entries": len(table) if use_tt else 0,
        "threshold_tt_enabled": use_tt,
        "history_key_mode": "FULL_HISTORY_REQUIRED" if policy == "continuous_check_loss" else "REPETITION_COUNTS_SUFFICIENT",
        "abstract_horizon": True,
        "max_proof_ply": proof_peak,
    })
    reason = next(iter(sorted(root_causes)), None) if root_causes else None
    return AbstractResult(strong, root_value, optimal, tuple(rows), stats_dict, reason, root_causes, proof_peak)


def _is_unknown(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("U")


def _tree_values(node) -> set[int]:
    if node[0] == "leaf":
        return {-1, 0, 1} if _is_unknown(node[1]) else {node[1]}
    maximizing, children = node[1], node[2]
    values = [_tree_values(child) for child in children]
    result = set()
    for combination in __import__("itertools").product(*values):
        result.add((max if maximizing else min)(combination))
    return result


def tree_threshold(node, threshold: int) -> bool | None:
    """Complete finite-tree threshold oracle for independently named U leaves."""
    outcomes = {_value >= threshold for _value in _tree_values(node)}
    if outcomes == {True}:
        return True
    if outcomes == {False}:
        return False
    return None


def concrete_tree_value(node, assignments: dict[str, int]) -> int:
    if node[0] == "leaf":
        return assignments[node[1]] if _is_unknown(node[1]) else node[1]
    values = [concrete_tree_value(child, assignments) for child in node[2]]
    return (max if node[1] else min)(values)


__all__ = [
    "PROVED_TRUE", "PROVED_FALSE", "UNRESOLVED", "MAX_PLY_ABSTRACT_LEAF",
    "ABSTRACT_NODE_CAP", "ABSTRACT_CYCLE_REFUSAL", "ABSTRACT_NO_SUCCESSORS",
    "ABSTRACT_TIME_CAP", "ABSTRACT_WORKER_FAILURE", "OTHER_ABSTRACT_UNRESOLVED",
    "ThresholdProof", "AbstractResult", "solve_root_horizon_abstract_v2",
    "tree_threshold", "concrete_tree_value",
]
