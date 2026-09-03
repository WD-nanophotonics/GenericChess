"""Persistent semantic Native search engine.

The one-shot semantic search remains available as a reference path.  This
engine owns one compiled semantic RuleSet, one evaluator profile, and one TT
across searches so self-play does not allocate and clear a large table on
every move.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping

from ..ai.cancellation import CancellationToken
from ..ai.limits import SearchLimits
from ..core.actions import Action
from ..core.transition import apply_action
from . import _module, native_available
from .adapter import pack_semantic_search_position
from .compiler import GC_SEM_MAX_PLY
from .semantic import public_action

DYNAMIC_FEATURE_NAMES = ("mobility", "promotion_potential", "anchor_safety")
SPATIAL_CELL_COUNT = 9


DECLARATION_ACTION_TAG = 1 << 63


@dataclass(frozen=True, slots=True)
class SemanticIterativeSearchResult:
    score: int
    action: Action | None
    declaration_id: str | None
    principal_variation: tuple[Action, ...]
    decision_line: tuple[Action | str, ...]
    completed_depth: int
    selective_depth: int
    nodes: int
    qnodes: int
    elapsed_seconds: float
    termination_reason: str
    used_fallback: bool
    tt_status: str
    tt_probes: int
    tt_hits: int
    tt_cutoffs: int
    tt_stores: int
    tt_replacements: int
    tt_entry_bytes: int
    tt_allocated_bytes: int
    dynamic_features: tuple[int, int, int] = ()


def _profile_tuple(native_rules, values):
    if values is None:
        return None
    if isinstance(values, Mapping):
        expected = tuple(native_rules.type_ids)
        if set(values) != set(expected):
            raise ValueError("semantic evaluator profile must cover exactly native type IDs")
        return tuple(int(values[type_id]) for type_id in expected)
    result = tuple(int(value) for value in values)
    if len(result) != len(native_rules.type_ids):
        raise ValueError("semantic evaluator profile length must match native type count")
    return result


def _dynamic_tuple(values):
    if values is None:
        return None
    if isinstance(values, Mapping):
        if set(values) != set(DYNAMIC_FEATURE_NAMES):
            raise ValueError("semantic dynamic evaluator profile must cover exactly the dynamic feature names")
        return tuple(int(values[name]) for name in DYNAMIC_FEATURE_NAMES)
    result = tuple(int(value) for value in values)
    if len(result) != len(DYNAMIC_FEATURE_NAMES):
        raise ValueError("semantic dynamic evaluator profile must contain three values")
    return result


def _spatial_tuple(native_rules, values):
    if values is None:
        return None
    type_ids = tuple(native_rules.type_ids)
    if isinstance(values, Mapping):
        expected = {f"{owner}:{type_id}" for owner in (0, 1) for type_id in type_ids}
        if set(values) != expected:
            raise ValueError("semantic spatial evaluator profile must cover every owner/current type")
        rows = [values[f"{owner}:{type_id}"] for owner in (0, 1) for type_id in type_ids]
        result = tuple(int(value) for row in rows for value in row)
    else:
        result = tuple(int(value) for value in values)
    if len(result) != len(type_ids) * SPATIAL_CELL_COUNT:
        raise ValueError("semantic spatial evaluator profile length must match type_count * 9")
    for offset in range(0, len(result), SPATIAL_CELL_COUNT):
        if sum(result[offset:offset + SPATIAL_CELL_COUNT]) != 0:
            raise ValueError("semantic spatial evaluator rows must have zero sum")
    return result


def _localized_control_tuple(values):
    if values is None:
        return None
    result = tuple(int(value) for value in values)
    if len(result) != SPATIAL_CELL_COUNT:
        raise ValueError("semantic localized control profile must contain nine values")
    if sum(result) != 0:
        raise ValueError("semantic localized control profile must have zero sum")
    return result


class SemanticSearchEngine:
    """Reusable, single-thread semantic Native search engine."""

    def __init__(
        self,
        compiled,
        native_rules,
        *,
        board_values=None,
        hand_values=None,
        dynamic_values=None,
        spatial_occupancy_values=None,
        localized_control_values=None,
        checkpoint=None,
        evaluator_scale: int = 1,
        tt_megabytes: int = 64,
    ) -> None:
        if not native_available():
            raise RuntimeError("native extension is not built")
        if compiled.ruleset_fingerprint != native_rules.fingerprint:
            raise ValueError("ruleset fingerprint mismatch for semantic engine")
        if isinstance(tt_megabytes, bool) or not isinstance(tt_megabytes, int) or not 0 <= tt_megabytes <= 1024:
            raise ValueError("tt_megabytes must be an integer in [0, 1024]")
        if isinstance(evaluator_scale, bool) or not isinstance(evaluator_scale, int) or not 1 <= evaluator_scale <= 1024:
            raise ValueError("evaluator_scale must be an integer in [1, 1024]")
        self._compiled = compiled
        self._native_rules = native_rules
        self._checkpoint_id = None
        self._board_values = _profile_tuple(native_rules, board_values)
        self._hand_values = _profile_tuple(native_rules, hand_values)
        self._dynamic_values = _dynamic_tuple(dynamic_values)
        self._spatial_values = _spatial_tuple(native_rules, spatial_occupancy_values)
        self._localized_control_values = _localized_control_tuple(localized_control_values)
        self._evaluator_scale = evaluator_scale
        if (self._board_values is None) != (self._hand_values is None):
            raise ValueError("board_values and hand_values must be supplied together")
        self._tt_megabytes = tt_megabytes
        if checkpoint is not None:
            self._set_checkpoint_values(checkpoint)
        self._capsule = self._new_capsule()

    def _set_checkpoint_values(self, checkpoint) -> None:
        checkpoint.validate_ruleset(self._compiled)
        type_ids = tuple(self._native_rules.type_ids)
        self._board_values = tuple(checkpoint.semantic_quantized_board(type_ids))
        self._hand_values = tuple(checkpoint.semantic_quantized_hand(type_ids))
        dynamic = checkpoint.semantic_quantized_dynamic()
        self._dynamic_values = None if dynamic is None else tuple(dynamic)
        spatial = checkpoint.semantic_quantized_spatial(type_ids)
        self._spatial_values = None if spatial is None else tuple(spatial)
        control = checkpoint.semantic_quantized_localized_control()
        self._localized_control_values = None if control is None else tuple(control)
        self._evaluator_scale = checkpoint.semantic_native_scale
        self._checkpoint_id = checkpoint.checkpoint_id

    def _new_capsule(self):
        return _module().create_semantic_search_engine(
            self._native_rules.capsule,
            self._board_values,
            self._hand_values,
            self._dynamic_values,
            self._spatial_values,
            self._localized_control_values,
            self._tt_megabytes,
            self._evaluator_scale,
        )

    @property
    def ruleset_fingerprint(self) -> str:
        return self._native_rules.fingerprint

    @property
    def checkpoint_id(self):
        return self._checkpoint_id

    def bind_checkpoint(self, checkpoint) -> None:
        """Rebind learned material without recompiling the semantic RuleSet.

        A changed checkpoint gets a new evaluator binding and a fresh TT, so
        entries can never be reused under a different value function.
        """
        checkpoint.validate_ruleset(self._compiled)
        if checkpoint.checkpoint_id == self._checkpoint_id:
            return
        self._set_checkpoint_values(checkpoint)
        self._capsule = self._new_capsule()

    def bind_evaluator(
        self, board_values, hand_values, dynamic_values=None,
        spatial_occupancy_values=None, localized_control_values=None,
        *, evaluator_scale: int = 1,
    ) -> None:
        board = _profile_tuple(self._native_rules, board_values)
        hand = _profile_tuple(self._native_rules, hand_values)
        if (board is None) != (hand is None):
            raise ValueError("board_values and hand_values must be supplied together")
        self._board_values, self._hand_values = board, hand
        self._dynamic_values = _dynamic_tuple(dynamic_values)
        self._spatial_values = _spatial_tuple(self._native_rules, spatial_occupancy_values)
        self._localized_control_values = _localized_control_tuple(localized_control_values)
        if isinstance(evaluator_scale, bool) or not isinstance(evaluator_scale, int) or not 1 <= evaluator_scale <= 1024:
            raise ValueError("evaluator_scale must be an integer in [1, 1024]")
        self._evaluator_scale = evaluator_scale
        self._checkpoint_id = None
        self._capsule = self._new_capsule()

    @property
    def native_evaluator_values(self) -> dict:
        """Return the exact fixed-point values bound to the Native engine."""
        return {
            "scale": self._evaluator_scale,
            "board": tuple(self._board_values or ()),
            "hand": tuple(self._hand_values or ()),
            "dynamic": tuple(self._dynamic_values or ()),
            "spatial_occupancy": tuple(self._spatial_values or ()),
            "localized_control": tuple(self._localized_control_values or ()),
        }

    def clear_tt(self) -> None:
        _module().semantic_engine_clear_tt(self._capsule)

    def tt_info(self) -> dict:
        return {
            key: int(value)
            for key, value in dict(_module().semantic_engine_tt_info(self._capsule)).items()
        }

    def search(
        self,
        session,
        limits: SearchLimits,
        cancel_token: CancellationToken | None = None,
    ) -> SemanticIterativeSearchResult:
        if self._compiled.ruleset_fingerprint != session.compiled.ruleset_fingerprint:
            raise ValueError("session ruleset fingerprint does not match semantic engine")
        if limits.max_depth is None:
            raise ValueError("SemanticSearchEngine requires max_depth")
        if not 0 <= limits.max_depth <= GC_SEM_MAX_PLY:
            raise ValueError(f"max_depth must be in [0, {GC_SEM_MAX_PLY}]")
        if limits.max_nodes is not None and limits.max_nodes < 0:
            raise ValueError("max_nodes must be >= 0")
        if limits.max_time_seconds is not None and not (
            0 <= limits.max_time_seconds
            and limits.max_time_seconds == limits.max_time_seconds
            and abs(limits.max_time_seconds) != float("inf")
        ):
            raise ValueError("max_time_seconds must be a finite non-negative value")
        if limits.quiescence_max_depth != 0 or limits.quiescence_max_nodes not in (None, 0):
            raise ValueError("SemanticSearchEngine does not implement qsearch")
        if session.result.status.value != "ongoing":
            return SemanticIterativeSearchResult(
                0, None, None, (), (), 0, 0, 0, 0, 0.0,
                "terminal_position", False, "NOT_STARTED", 0, 0, 0, 0, 0, 0, 0,
            )

        position = pack_semantic_search_position(self._compiled, self._native_rules, session)
        flag = None
        unregister = None
        if cancel_token is not None:
            flag = _module().create_cancel_flag()
            unregister = cancel_token.register_callback(
                lambda: _module().request_cancel(flag)
            )
        try:
            raw = dict(_module().semantic_engine_search(
                self._capsule,
                position,
                int(limits.max_depth),
                None if limits.max_nodes is None else int(limits.max_nodes),
                None if limits.max_time_seconds is None else float(limits.max_time_seconds),
                flag,
            ))
        finally:
            if unregister is not None:
                unregister()

        declaration_id = raw.get("declaration_id")
        declaration_id = None if declaration_id is None else str(declaration_id)
        packed_best = raw.get("best_action")
        action = None if packed_best is None else public_action(
            self._native_rules, int(packed_best)
        )
        decision_line = []
        for packed in raw.get("principal_variation", ()):
            packed = int(packed)
            if packed & DECLARATION_ACTION_TAG:
                index = packed & 0xFF
                if index >= len(self._native_rules.declarations):
                    raise ValueError("semantic search returned invalid declaration decision")
                decision_line.append(self._native_rules.declarations[index].declaration_id)
            else:
                decision_line.append(public_action(self._native_rules, packed))
        if declaration_id is not None and not decision_line:
            decision_line.append(declaration_id)
        pv = tuple(item for item in decision_line if not isinstance(item, str))
        state = session.state
        for pv_action in pv:
            state = apply_action(state, pv_action, self._compiled)

        leaf_dynamic: tuple[int, int, int] = ()
        if pv:
            leaf_position = position
            for packed in raw.get("principal_variation", ()):
                packed = int(packed)
                if packed & DECLARATION_ACTION_TAG:
                    break
                leaf_position = _module().semantic_make_checked(
                    self._native_rules.capsule, leaf_position, packed
                )
            from .semantic import dynamic_features as native_dynamic_features
            leaf_dynamic = native_dynamic_features(self._native_rules, leaf_position)

        return SemanticIterativeSearchResult(
            score=int(raw["score"]),
            action=action,
            declaration_id=declaration_id,
            principal_variation=pv,
            decision_line=tuple(decision_line),
            completed_depth=int(raw["completed_depth"]),
            selective_depth=int(raw["selective_depth"]),
            nodes=int(raw["nodes"]),
            qnodes=int(raw.get("qnodes", 0)),
            elapsed_seconds=int(raw["elapsed_nanoseconds"]) / 1e9,
            termination_reason=str(raw["termination_reason"]),
            used_fallback=bool(raw["used_fallback"]),
            tt_status=str(raw.get("tt_status", "NOT_STARTED")),
            tt_probes=int(raw.get("tt_probes", 0)),
            tt_hits=int(raw.get("tt_hits", 0)),
            tt_cutoffs=int(raw.get("tt_cutoffs", 0)),
            tt_stores=int(raw.get("tt_stores", 0)),
            tt_replacements=int(raw.get("tt_replacements", 0)),
            tt_entry_bytes=int(raw.get("tt_entry_bytes", 0)),
            tt_allocated_bytes=int(raw.get("tt_allocated_bytes", 0)),
            dynamic_features=leaf_dynamic,
        )


NativeSemanticSearchEngine = SemanticSearchEngine
NativeSemanticSearchResult = SemanticIterativeSearchResult
