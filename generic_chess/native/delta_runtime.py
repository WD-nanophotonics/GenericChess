"""Opt-in Native semantic delta runtime for F17 certification."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass

from ..core.actions import SemanticBoardMove, SemanticDropMove
from ..core.coordinates import square_to_index
from .mirror import MirrorUnavailable, _position_payload
from .semantic import (
    delta_runtime_in_check, delta_runtime_info, delta_runtime_is_square_attacked,
    delta_runtime_layout, delta_runtime_new, delta_runtime_new_transient, delta_runtime_pop,
    delta_runtime_position_key, delta_runtime_push, delta_runtime_snapshot,
    pack_action, pack_position,
)


@dataclass(slots=True)
class DeltaRuntimeCounters:
    root_packs: int = 0
    action_packs: int = 0
    push_count: int = 0
    pop_count: int = 0
    root_pack_seconds: float = 0.0
    action_pack_seconds: float = 0.0
    push_seconds: float = 0.0
    pop_seconds: float = 0.0


class _PrecomputedActionPacker:
    __slots__ = ("type_map", "pattern_map", "geometry_map")

    def __init__(self, native_rules):
        self.type_map = {value: index for index, value in enumerate(native_rules.type_ids)}
        self.pattern_map = {value: index for index, value in enumerate(native_rules.pattern_ids)}
        self.geometry_map = {value: index for index, value in enumerate(native_rules.geometry_ids)}

    def pack(self, parent, action) -> int:
        if isinstance(action, SemanticBoardMove):
            source = square_to_index(action.from_square, parent.board_size())
            target = square_to_index(action.to_square, parent.board_size())
            piece = parent.board[source]
            if piece is None or piece.current_type_id != action.actor_type_id or piece.owner != parent.side_to_move:
                raise MirrorUnavailable("semantic action disagrees with Python parent")
            fields = {
                "to": target, "from": source,
                "promotion": 255 if action.promotion_target_id is None else self.type_map[action.promotion_target_id],
                "base": self.type_map[piece.base_type_id], "kind": 2,
                "pattern": self.pattern_map[action.pattern_id], "geometry": self.geometry_map[action.geometry_id],
                "actor_current": self.type_map[action.actor_type_id],
            }
        elif isinstance(action, SemanticDropMove):
            base = self.type_map[action.base_type_id]
            fields = {
                "to": square_to_index(action.to_square, parent.board_size()), "from": 255,
                "promotion": 255, "base": base, "kind": 3,
                "pattern": self.pattern_map[action.pattern_id], "geometry": self.geometry_map[action.geometry_id],
                "actor_current": base,
            }
        else:
            raise MirrorUnavailable("delta runtime requires a lossless semantic action")
        return pack_action(fields)


class NativeSemanticDeltaRuntime:
    """One C-owned current position plus bounded transactional delta frames."""

    __slots__ = ("compiled", "native_rules", "_capsule", "_packer", "counters", "history_certified", "history_policy")

    def __init__(self, compiled, native_rules, capsule, *, history_certified: bool, history_policy: str = "EXACT_APPEND"):
        self.compiled = compiled
        self.native_rules = native_rules
        self._capsule = capsule
        self._packer = _PrecomputedActionPacker(native_rules)
        self.counters = DeltaRuntimeCounters()
        self.history_certified = bool(history_certified)
        self.history_policy = history_policy

    @classmethod
    def from_position(cls, native_rules, position_capsule, *, history_policy: str = "EXACT_APPEND"):
        factory = delta_runtime_new_transient if history_policy == "TRANSIENT_NONE" else delta_runtime_new
        return cls(None, native_rules, factory(native_rules, position_capsule), history_certified=history_policy == "EXACT_APPEND", history_policy=history_policy)

    @classmethod
    def from_state(cls, compiled, native_rules, state, *, history_certified: bool, history_policy: str = "EXACT_APPEND"):
        if not getattr(native_rules, "native_executable", False):
            raise MirrorUnavailable("ruleset is not Native executable")
        if native_rules.fingerprint != compiled.ruleset_fingerprint or (history_policy == "EXACT_APPEND" and not history_certified):
            raise MirrorUnavailable("Native/Python root or history is not certified")
        started = time.perf_counter()
        payload = _position_payload(compiled, native_rules, state)
        position = pack_position(native_rules, payload)
        factory = delta_runtime_new_transient if history_policy == "TRANSIENT_NONE" else delta_runtime_new
        runtime = cls(compiled, native_rules, factory(native_rules, position), history_certified=history_policy == "EXACT_APPEND", history_policy=history_policy)
        runtime.counters.root_packs = 1
        runtime.counters.root_pack_seconds = time.perf_counter() - started
        return runtime

    @property
    def capsule(self):
        return self._capsule

    @property
    def depth(self) -> int:
        return delta_runtime_info(self._capsule)["depth"]

    def info(self) -> dict:
        return delta_runtime_info(self._capsule)

    def direct_pack(self, action, parent_position) -> int:
        started = time.perf_counter()
        packed = self._packer.pack(parent_position, action)
        self.counters.action_packs += 1
        self.counters.action_pack_seconds += time.perf_counter() - started
        return packed

    def push_packed(self, packed_action: int) -> None:
        started = time.perf_counter()
        delta_runtime_push(self._capsule, packed_action)
        self.counters.push_count += 1
        self.counters.push_seconds += time.perf_counter() - started

    def push(self, action, parent_position) -> int:
        packed = self.direct_pack(action, parent_position)
        self.push_packed(packed)
        return packed

    def pop(self) -> None:
        started = time.perf_counter()
        delta_runtime_pop(self._capsule)
        self.counters.pop_count += 1
        self.counters.pop_seconds += time.perf_counter() - started

    def snapshot(self) -> dict:
        return delta_runtime_snapshot(self._capsule)

    def position_key(self) -> str:
        return delta_runtime_position_key(self._capsule)

    def is_square_attacked(self, square: int, by_owner: int) -> bool:
        return delta_runtime_is_square_attacked(self._capsule, square, by_owner)

    def in_check(self, side: int) -> bool:
        return delta_runtime_in_check(self._capsule, side)

    def summary(self) -> dict:
        out = self.info()
        out.update(asdict(self.counters))
        out["history_certified"] = self.history_certified
        out["history_policy"] = self.history_policy
        return out


__all__ = ["NativeSemanticDeltaRuntime", "DeltaRuntimeCounters", "MirrorUnavailable", "delta_runtime_layout"]
