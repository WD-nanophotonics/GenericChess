"""Experimental native iterative search engine.

The engine is persistent and reusable: compile rules and evaluation once,
create the engine once, then call :meth:`NativeSearchEngine.search` per move
(full GameSession history replay + one native iterative call).  It is *not*
the production SearchBackend and is not wired into the UI.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..ai.cancellation import CancellationToken
from ..ai.limits import SearchLimits
from ..core.actions import Action
from ..core.transition import apply_action
from . import _module, native_available
from .adapter import (
    pack_native_search_position,
    to_python_action,
)
from .compiler import GC_MAX_PLY, NativeActionError
from .reference import python_legal_actions


@dataclass(frozen=True, slots=True)
class NativeIterativeSearchResult:
    score: int
    action: Action | None
    principal_variation: tuple[Action, ...]
    completed_depth: int
    selective_depth: int
    nodes: int
    qnodes: int
    elapsed_seconds: float
    termination_reason: str
    used_fallback: bool
    tt_probes: int
    tt_hits: int
    tt_cutoffs: int
    tt_stores: int
    tt_replacements: int
    beta_cutoffs: int


class NativeSearchEngine:
    """Persistent fixed-depth+iterative native engine (experimental)."""

    def __init__(
        self,
        compiled,
        native_rules,
        native_evaluation,
        tt_megabytes: int = 64,
    ) -> None:
        if not native_available():
            raise RuntimeError("native extension is not built")
        if not (0 <= tt_megabytes <= 1024):
            raise ValueError("tt_megabytes must be in [0, 1024]")
        if compiled.ruleset_fingerprint != native_rules.fingerprint:
            raise ValueError("ruleset fingerprint mismatch for the engine")
        self._compiled = compiled
        self._native_rules = native_rules
        self._evaluation = native_evaluation
        self._capsule = _module().create_search_engine(
            native_rules.capsule, native_evaluation.capsule, tt_megabytes
        )

    # ------------------------------------------------------------------ api

    def search(
        self,
        session,
        limits: SearchLimits,
        cancel_token: CancellationToken | None = None,
    ) -> NativeIterativeSearchResult:
        if self._compiled.ruleset_fingerprint != session.compiled.ruleset_fingerprint:
            raise ValueError("session ruleset fingerprint does not match engine")
        if limits.max_depth is None:
            raise ValueError("NativeSearchEngine requires max_depth")
        if not (0 <= limits.max_depth <= GC_MAX_PLY):
            raise ValueError(f"max_depth must be in [0, {GC_MAX_PLY}]")
        if limits.max_nodes is not None and limits.max_nodes < 0:
            raise ValueError("max_nodes must be >= 0")
        if limits.max_time_seconds is not None and not (
            0 <= limits.max_time_seconds
            and limits.max_time_seconds == limits.max_time_seconds
            and abs(limits.max_time_seconds) != float("inf")
        ):
            raise ValueError("max_time_seconds must be a finite non-negative value")
        if (
            limits.quiescence_max_depth != 0
            or limits.quiescence_max_nodes not in (None, 0)
        ):
            raise ValueError(
                "NativeSearchEngine does not implement qsearch; pass "
                "quiescence_max_depth=0"
            )
        if session.result.status.value == "resignation":
            return NativeIterativeSearchResult(
                score=0,
                action=None,
                principal_variation=(),
                completed_depth=0,
                selective_depth=0,
                nodes=0,
                qnodes=0,
                elapsed_seconds=0.0,
                termination_reason="terminal_position",
                used_fallback=False,
                tt_probes=0,
                tt_hits=0,
                tt_cutoffs=0,
                tt_stores=0,
                tt_replacements=0,
                beta_cutoffs=0,
            )

        pos = pack_native_search_position(
            self._compiled, self._native_rules, session
        )
        flag = _module().create_cancel_flag()
        unregister = None
        if cancel_token is not None:
            unregister = cancel_token.register_callback(
                lambda: _module().request_cancel(flag)
            )
        try:
            raw = _module().native_iterative_search(
                self._capsule,
                pos,
                limits.max_depth,
                limits.max_nodes,
                limits.max_time_seconds,
                flag,
            )
        finally:
            if unregister is not None:
                unregister()

        best_packed = raw["best_action"]
        action = (
            to_python_action(self._native_rules, best_packed)
            if best_packed is not None
            else None
        )
        pv = tuple(
            to_python_action(self._native_rules, a)
            for a in raw["principal_variation"]
        )
        legal = python_legal_actions(session.state, self._compiled)
        if action is not None and action not in legal:
            raise NativeActionError(
                "native iterative search returned an action outside the "
                f"Python legal set: {action}",
                {
                    "status": -1,
                    "reason": "best_action_not_legal",
                    "packed": best_packed,
                    "fingerprint": self._compiled.ruleset_fingerprint,
                },
            )
        state = session.state
        for pv_action in pv:
            state = apply_action(state, pv_action, self._compiled)

        return NativeIterativeSearchResult(
            score=int(raw["score"]),
            action=action,
            principal_variation=pv,
            completed_depth=int(raw["completed_depth"]),
            selective_depth=int(raw["selective_depth"]),
            nodes=int(raw["nodes"]),
            qnodes=int(raw["qnodes"]),
            elapsed_seconds=float(raw["elapsed_seconds"]),
            termination_reason=str(raw["termination_reason"]),
            used_fallback=bool(raw["used_fallback"]),
            tt_probes=int(raw["tt_probes"]),
            tt_hits=int(raw["tt_hits"]),
            tt_cutoffs=int(raw["tt_cutoffs"]),
            tt_stores=int(raw["tt_stores"]),
            tt_replacements=int(raw["tt_replacements"]),
            beta_cutoffs=int(raw["beta_cutoffs"]),
        )

    def clear_tt(self) -> None:
        _module().search_engine_clear_tt(self._capsule)

    def tt_info(self) -> dict:
        return dict(_module().search_engine_tt_info(self._capsule))
