"""Exact threshold/runtime proof solver V3 with no heuristic scoring."""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any

from generic_chess.core.actions import action_to_dict
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalStatus


PROVED_TRUE = "PROVED_TRUE"
PROVED_FALSE = "PROVED_FALSE"
UNRESOLVED = "UNRESOLVED"
THRESHOLDS = (0, 1)
SOLVER_VERSION = "exact_generic_preference_solver_v3@F23M-CORRECTIVE-R1"


@dataclass(frozen=True)
class ThresholdResult:
    status: str
    value: int | None = None


@dataclass(frozen=True)
class ThresholdSolveResult:
    strong: bool
    root_value: str | None
    optimal_actions: tuple[dict[str, Any], ...]
    action_values: tuple[dict[str, Any], ...]
    stats: dict[str, Any]
    unresolved_reason: str | None = None
    max_proof_ply: int = 0


def _combine_threshold_children(maximizing: bool, children: list[ThresholdResult]) -> ThresholdResult:
    """Combine threshold certificates without treating UNRESOLVED as a value."""
    saw_unresolved = False
    for child in children:
        if child.status == UNRESOLVED:
            saw_unresolved = True
            continue
        if maximizing and child.status == PROVED_TRUE:
            return ThresholdResult(PROVED_TRUE)
        if not maximizing and child.status == PROVED_FALSE:
            return ThresholdResult(PROVED_FALSE)
    if saw_unresolved:
        return ThresholdResult(UNRESOLVED)
    return ThresholdResult(PROVED_FALSE if maximizing else PROVED_TRUE)


def _runtime_key(runtime, *, policy: str):
    key = runtime.search_key()
    repetition = tuple(sorted(runtime.repetition_counts.items(), key=lambda item: repr(item[0])))
    if policy == "continuous_check_loss":
        history = tuple((record.identity, record.actor, record.gave_check) for record in runtime.history)
        return (key.ruleset_fingerprint, key.runtime_hash, key.position_key, repetition, key.ply_count, history)
    return (key.ruleset_fingerprint, key.runtime_hash, key.position_key, repetition, key.ply_count)


def _status_for_terminal(runtime, root_actor: int, threshold: int) -> ThresholdResult | None:
    terminal = runtime.terminal_status
    if terminal.status is TerminalStatus.ONGOING:
        return None
    if terminal.winner is None:
        value = 0
    else:
        value = 1 if terminal.winner == root_actor else -1
    return ThresholdResult(PROVED_TRUE if value >= threshold else PROVED_FALSE, value)


def solve_root_threshold_v3(compiled, state, *, max_nodes: int, max_depth: int | None = None, use_tt: bool = True) -> ThresholdSolveResult:
    """Certify every root action using exact threshold predicates."""
    root_actor = state.position.side_to_move
    configured_max_ply = getattr(compiled, "max_ply", None)
    if configured_max_ply is None:
        configured_max_ply = compiled.support.max_ply
    horizon = max(0, configured_max_ply - state.ply_count)
    runtime = SearchPathRuntime.from_state(state, compiled)
    policy = getattr(compiled, "repetition_policy", None)
    if policy is None:
        support = getattr(compiled, "support", None)
        policy = getattr(support, "repetition_policy", "draw")
    stats = Counter(states_expanded=0, legal_actions_enumerated=0, pushes=0, pops=0, threshold_tt_hits=0, unresolved_cap_hits=0, cycle_refusals=0, proof_short_circuits=0, repetition_adjudications=0, perpetual_check_adjudications=0)
    table: dict[tuple[object, int], str] = {}
    active: set[tuple[object, int]] = set()
    unresolved = Counter()
    proof_peak = 0
    started_at = time.perf_counter()
    profile = Counter()

    def _store(key, value):
        started = time.perf_counter()
        table[key] = value
        profile["tt_store_seconds"] += time.perf_counter() - started

    def prove_ge(threshold: int, depth: int) -> ThresholdResult:
        nonlocal proof_peak
        proof_peak = max(proof_peak, runtime.depth)
        started = time.perf_counter()
        terminal = _status_for_terminal(runtime, root_actor, threshold)
        profile["terminal_seconds"] += time.perf_counter() - started
        if terminal is not None:
            if runtime.terminal_status.status is TerminalStatus.REPETITION:
                stats["repetition_adjudications"] += 1
            if runtime.terminal_status.status is TerminalStatus.PERPETUAL_CHECK:
                stats["perpetual_check_adjudications"] += 1
            return terminal
        if stats["states_expanded"] >= max_nodes:
            stats["unresolved_cap_hits"] += 1; unresolved["REFERENCE_SOLVE_UNRESOLVED:node_cap"] += 1
            return ThresholdResult(UNRESOLVED)
        if max_depth is not None and depth >= max_depth:
            stats["unresolved_cap_hits"] += 1; unresolved["REFERENCE_SOLVE_UNRESOLVED:depth_cap"] += 1
            return ThresholdResult(UNRESOLVED)
        started = time.perf_counter()
        key = (_runtime_key(runtime, policy=policy), threshold)
        profile["tt_key_seconds"] += time.perf_counter() - started
        if key in active:
            stats["cycle_refusals"] += 1; unresolved["REFERENCE_SOLVE_UNRESOLVED:cycle"] += 1
            return ThresholdResult(UNRESOLVED)
        started = time.perf_counter()
        cached = table.get(key) if use_tt else None
        profile["tt_lookup_seconds"] += time.perf_counter() - started
        if cached is not None:
            stats["threshold_tt_hits"] += 1
            return ThresholdResult(cached)
        active.add(key)
        stats["states_expanded"] += 1
        started = time.perf_counter()
        actions = runtime.legal_actions()
        profile["legal_actions_seconds"] += time.perf_counter() - started
        stats["legal_actions_enumerated"] += len(actions)
        if not actions:
            active.remove(key); unresolved["REFERENCE_SOLVE_UNRESOLVED:no_successors"] += 1
            return ThresholdResult(UNRESOLVED)
        maximizing = runtime.position.side_to_move == root_actor
        children: list[ThresholdResult] = []
        for action in sorted(actions, key=lambda candidate: json.dumps(action_to_dict(candidate), sort_keys=True, separators=(",", ":"))):
            started = time.perf_counter()
            runtime.push(action)
            stats["pushes"] += 1
            profile["runtime_push_transition_seconds"] += time.perf_counter() - started
            try:
                child = prove_ge(threshold, depth + 1)
            finally:
                started = time.perf_counter()
                runtime.pop()
                profile["runtime_pop_seconds"] += time.perf_counter() - started
                stats["pops"] = runtime.pops
            children.append(child)
            if maximizing and child.status == PROVED_TRUE:
                stats["proof_short_circuits"] += 1; active.remove(key)
                if use_tt: _store(key, PROVED_TRUE)
                return ThresholdResult(PROVED_TRUE)
            if not maximizing and child.status == PROVED_FALSE:
                stats["proof_short_circuits"] += 1; active.remove(key)
                if use_tt: _store(key, PROVED_FALSE)
                return ThresholdResult(PROVED_FALSE)
        active.remove(key)
        combined = _combine_threshold_children(maximizing, children)
        if combined.status == UNRESOLVED:
            return ThresholdResult(UNRESOLVED)
        if use_tt: _store(key, combined.status)
        return combined

    initial_terminal = _status_for_terminal(runtime, root_actor, 0)
    if initial_terminal is not None:
        return ThresholdSolveResult(False, None, (), (), {"history_key_mode": "FULL_HISTORY_REQUIRED" if policy == "continuous_check_loss" else "REPETITION_COUNTS_SUFFICIENT"}, "ROOT_ALREADY_TERMINAL")
    root_actions = runtime.legal_actions()
    stats["legal_actions_enumerated"] += len(root_actions)
    stats["root_actions"] = len(root_actions)
    values = []
    for action in sorted(root_actions, key=lambda candidate: json.dumps(action_to_dict(candidate), sort_keys=True, separators=(",", ":"))):
        exact_value = None
        proof_peak = 0
        started = time.perf_counter()
        runtime.push(action)
        stats["pushes"] += 1
        profile["runtime_push_transition_seconds"] += time.perf_counter() - started
        try:
            win = prove_ge(1, 1)
            if win.status == PROVED_TRUE:
                exact_value = "WIN"
            else:
                draw = prove_ge(0, 1)
                if draw.status == PROVED_FALSE:
                    exact_value = "LOSS"
                elif draw.status == PROVED_TRUE and win.status == PROVED_FALSE:
                    exact_value = "DRAW"
        finally:
            started = time.perf_counter()
            runtime.pop()
            profile["runtime_pop_seconds"] += time.perf_counter() - started
            stats["pops"] = runtime.pops
        values.append({"action": action_to_dict(action), "value": exact_value, "proof_depth": proof_peak if exact_value else None})
    runtime.assert_balanced()
    profile["total_seconds"] = time.perf_counter() - started_at
    measured = sum(profile[key] for key in ("terminal_seconds", "tt_key_seconds", "tt_lookup_seconds", "tt_store_seconds", "legal_actions_seconds", "runtime_push_transition_seconds", "runtime_pop_seconds"))
    profile["proof_bookkeeping_seconds"] = max(0.0, profile["total_seconds"] - measured)
    total = profile["total_seconds"] or 1.0
    profile_proportions = {key: value / total for key, value in profile.items() if key != "total_seconds"}
    stats_dict = dict(stats)
    stats_dict.update({"tt_entries": len(table) if use_tt else 0, "threshold_tt_enabled": use_tt, "history_key_mode": "FULL_HISTORY_REQUIRED" if policy == "continuous_check_loss" else "REPETITION_COUNTS_SUFFICIENT", "authoritative_horizon": max_depth is None, "effective_max_depth": horizon, "runtime_pushes": runtime.pushes, "runtime_pops": runtime.pops, "peak_depth": runtime.peak_depth, "unresolved": dict(unresolved)})
    stats_dict.update({"solver_version": SOLVER_VERSION, "final_runtime_depth": runtime.depth, "profile_seconds": dict(profile), "profile_proportions": profile_proportions})
    if any(row["value"] is None for row in values):
        return ThresholdSolveResult(False, None, (), tuple(values), stats_dict, next(iter(unresolved), "REFERENCE_SOLVE_UNRESOLVED:unknown"))
    rank = {"LOSS": -1, "DRAW": 0, "WIN": 1}
    root_value = max((row["value"] for row in values), key=rank.get)
    optimal = tuple(row["action"] for row in values if row["value"] == root_value)
    return ThresholdSolveResult(True, root_value, optimal, tuple(values), stats_dict, None, max((row["proof_depth"] or 0) for row in values))


__all__ = ["PROVED_TRUE", "PROVED_FALSE", "UNRESOLVED", "SOLVER_VERSION", "ThresholdResult", "ThresholdSolveResult", "_combine_threshold_children", "solve_root_threshold_v3"]
