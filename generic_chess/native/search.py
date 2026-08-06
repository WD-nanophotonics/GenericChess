"""Experimental fixed-depth native search wrapper.

This is *not* the production SearchBackend: it accepts only a fixed depth,
uses the material-only native-compatible evaluator, and performs a debug
correctness pass (best action in the Python legal set + full PV legality
replay) on every call.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.actions import Action
from ..core.transition import apply_action
from .adapter import (
    native_fixed_depth_search as _c_search,
    pack_native_position,
    pack_native_search_position,
    to_python_action,
)
from .compiler import GC_MAX_PLY, NativeActionError
from .reference import python_legal_actions


@dataclass(frozen=True, slots=True)
class NativeFixedDepthResult:
    score: int
    action: Action | None
    principal_variation: tuple[Action, ...]
    nodes: int
    completed_depth: int
    termination_reason: str


def native_fixed_depth_search(
    compiled,
    native_rules,
    native_evaluation,
    session,
    depth: int,
) -> NativeFixedDepthResult:
    """Run the fixed-depth native search over a session root.

    The session history is replayed natively first (root equality enforced),
    then the C kernel searches.  The debug layer verifies that the returned
    best action belongs to the Python root legal set and that the PV replays
    through Python Core legality.
    """
    if depth < 0 or depth > GC_MAX_PLY:
        raise ValueError(f"search depth must be in [0, {GC_MAX_PLY}]")
    if session.result.status.value == "resignation":
        # Resignation is a session-level end, never a native board terminal.
        return NativeFixedDepthResult(
            score=0,
            action=None,
            principal_variation=(),
            nodes=0,
            completed_depth=0,
            termination_reason="terminal",
        )
    pos = pack_native_search_position(compiled, native_rules, session)
    raw = _c_search(native_rules, native_evaluation.capsule, pos, depth)

    best_packed = raw["best_action"]
    action = to_python_action(native_rules, best_packed) if best_packed is not None else None
    pv = tuple(to_python_action(native_rules, a) for a in raw["principal_variation"])

    legal = session.legal_actions()
    if action is not None and action not in legal:
        raise NativeActionError(
            "native fixed-depth search returned an action outside the Python "
            f"legal set: {action}",
            {
                "status": -1,
                "reason": "best_action_not_legal",
                "packed": best_packed,
                "fingerprint": compiled.ruleset_fingerprint,
            },
        )
    # Replay the PV through Python Core to prove every step is legal.
    state = session.state
    for pv_action in pv:
        state = apply_action(state, pv_action, compiled)

    return NativeFixedDepthResult(
        score=int(raw["score"]),
        action=action,
        principal_variation=pv,
        nodes=int(raw["nodes"]),
        completed_depth=int(raw["completed_depth"]),
        termination_reason=str(raw["termination_reason"]),
    )


def native_fixed_depth_search_state(
    compiled,
    native_rules,
    native_evaluation,
    state,
    depth: int,
) -> NativeFixedDepthResult:
    """Fixed-depth search over an arbitrary packed GameState (no history
    replay).  Test/debug entry for crafted positions; the replay-based
    :func:`native_fixed_depth_search` remains the search-root entry point."""
    if depth < 0 or depth > GC_MAX_PLY:
        raise ValueError(f"search depth must be in [0, {GC_MAX_PLY}]")
    pos = pack_native_position(compiled, native_rules, state)
    raw = _c_search(native_rules, native_evaluation.capsule, pos, depth)

    best_packed = raw["best_action"]
    action = to_python_action(native_rules, best_packed) if best_packed is not None else None
    pv = tuple(to_python_action(native_rules, a) for a in raw["principal_variation"])

    legal = python_legal_actions(state, compiled)
    if action is not None and action not in legal:
        raise NativeActionError(
            "native fixed-depth search returned an action outside the Python "
            f"legal set: {action}",
            {
                "status": -1,
                "reason": "best_action_not_legal",
                "packed": best_packed,
                "fingerprint": compiled.ruleset_fingerprint,
            },
        )
    child_state = state
    for pv_action in pv:
        child_state = apply_action(child_state, pv_action, compiled)

    return NativeFixedDepthResult(
        score=int(raw["score"]),
        action=action,
        principal_variation=pv,
        nodes=int(raw["nodes"]),
        completed_depth=int(raw["completed_depth"]),
        termination_reason=str(raw["termination_reason"]),
    )
