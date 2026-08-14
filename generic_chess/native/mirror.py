"""Opt-in Native semantic position mirror for AI-layer audits.

The mirror is deliberately outside ``generic_chess.core``.  Core owns the
authoritative Python position and DFS lifecycle; this module only maintains a
Native shadow for certification and future routing experiments.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass

from ..core.actions import SemanticBoardMove, SemanticDropMove
from ..core.coordinates import square_to_index
from ..core.identity import position_identity_key
from .semantic import make_checked, pack_action, pack_position, snapshot, unpack_action


class MirrorUnavailable(ValueError):
    """Raised when a Python root cannot be represented as an exact mirror."""


@dataclass(slots=True)
class MirrorCounters:
    root_packs: int = 0
    action_packs: int = 0
    native_makes: int = 0
    mirror_pushes: int = 0
    mirror_pops: int = 0
    root_pack_seconds: float = 0.0
    action_pack_seconds: float = 0.0
    native_make_seconds: float = 0.0
    push_seconds: float = 0.0
    pop_seconds: float = 0.0

    def summary(self) -> dict:
        return {
            "root_packs": self.root_packs,
            "action_packs": self.action_packs,
            "native_makes": self.native_makes,
            "mirror_pushes": self.mirror_pushes,
            "mirror_pops": self.mirror_pops,
            "root_pack_seconds": self.root_pack_seconds,
            "action_pack_seconds": self.action_pack_seconds,
            "native_make_seconds": self.native_make_seconds,
            "push_seconds": self.push_seconds,
            "pop_seconds": self.pop_seconds,
        }


def _history_words(key: str) -> tuple[int, int, int, int]:
    if not isinstance(key, str) or len(key) != 64:
        raise MirrorUnavailable("history record is not a full SHA-256 hex key")
    try:
        return tuple(int(key[offset:offset + 16], 16) for offset in range(0, 64, 16))
    except ValueError as exc:
        raise MirrorUnavailable("history record contains non-hex data") from exc


def _position_payload(compiled, native_rules, state) -> dict:
    type_ids = tuple(native_rules.type_ids)
    type_map = {type_id: index for index, type_id in enumerate(type_ids)}
    board = []
    for piece in state.position.board:
        if piece is None:
            board.append(None)
            continue
        try:
            board.append([
                type_map[piece.base_type_id],
                type_map[piece.current_type_id],
                int(piece.owner),
                int(bool(piece.promoted)),
            ])
        except KeyError as exc:
            raise MirrorUnavailable("Python piece type is absent from Native mapping") from exc
    hands = []
    for hand in state.position.hands:
        counts = [0] * len(type_ids)
        for type_id, count in hand.counts:
            if type_id not in type_map:
                raise MirrorUnavailable("Python hand type is absent from Native mapping")
            counts[type_map[type_id]] = int(count)
        hands.append(counts)

    history = tuple(_history_words(record.position_key) for record in state.history)
    if not history:
        raise MirrorUnavailable("opaque or absent root history")
    expected_current = str(position_identity_key(state.position, compiled))
    if state.history[-1].position_key != expected_current:
        raise MirrorUnavailable("root history does not terminate at the Python position")
    return {
        "side": int(state.position.side_to_move),
        "ply": int(state.ply_count),
        "board": board,
        "hands": hands,
        "aux_state": tuple(state.position.aux_state),
        "history": history,
    }


def _semantic_action_fields(native_rules, parent_position, action) -> dict:
    type_map = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    pattern_map = {pattern_id: index for index, pattern_id in enumerate(native_rules.pattern_ids)}
    geometry_map = {geometry_id: index for index, geometry_id in enumerate(native_rules.geometry_ids)}
    n = parent_position.board_size()
    if isinstance(action, SemanticBoardMove):
        source = square_to_index(action.from_square, n)
        target = square_to_index(action.to_square, n)
        piece = parent_position.board[source]
        if piece is None:
            raise MirrorUnavailable("semantic board action source is empty")
        if piece.current_type_id != action.actor_type_id:
            raise MirrorUnavailable("semantic action actor current type disagrees with Python parent")
        if piece.owner != parent_position.side_to_move:
            raise MirrorUnavailable("semantic action actor owner disagrees with Python side")
        try:
            return {
                "to": target,
                "from": source,
                "promotion": 255 if action.promotion_target_id is None else type_map[action.promotion_target_id],
                "base": type_map[piece.base_type_id],
                "kind": 2,
                "pattern": pattern_map[action.pattern_id],
                "geometry": geometry_map[action.geometry_id],
                "actor_current": type_map[action.actor_type_id],
            }
        except KeyError as exc:
            raise MirrorUnavailable("semantic board action identity is absent from Native mapping") from exc
    if isinstance(action, SemanticDropMove):
        try:
            base = type_map[action.base_type_id]
            return {
                "to": square_to_index(action.to_square, n),
                "from": 255,
                "promotion": 255,
                "base": base,
                "kind": 3,
                "pattern": pattern_map[action.pattern_id],
                "geometry": geometry_map[action.geometry_id],
                "actor_current": base,
            }
        except KeyError as exc:
            raise MirrorUnavailable("semantic drop action identity is absent from Native mapping") from exc
    raise MirrorUnavailable("Native semantic mirror requires a lossless semantic public action")


def pack_semantic_action(native_rules, parent_position, action) -> int:
    """Directly pack one public semantic action without legal-action enumeration."""
    return pack_action(_semantic_action_fields(native_rules, parent_position, action))


def expected_snapshot(position, native_rules, compiled=None) -> dict:
    type_map = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    board = []
    for piece in position.board:
        board.append(None if piece is None else (
            type_map[piece.base_type_id],
            type_map[piece.current_type_id],
            int(piece.owner),
            int(bool(piece.promoted)),
        ))
    hands = []
    for hand in position.hands:
        counts = [0] * len(native_rules.type_ids)
        for type_id, count in hand.counts:
            counts[type_map[type_id]] = int(count)
        hands.append(counts)
    physical_aux = dict(position.aux_state)
    if compiled is not None:
        aux = {}
        covered = set()
        for slot in compiled.ir.aux_slots:
            owners = (-1,) if slot.scope == "global" else (0, 1)
            for owner in owners:
                address = (slot.slot_id, owner)
                covered.add(address)
                aux[address] = physical_aux.get(address, slot.initial)
        for address, value in physical_aux.items():
            if address not in covered:
                aux[address] = value
        aux_state = tuple(sorted(aux.items()))
    else:
        aux_state = tuple(position.aux_state)
    return {
        "side": int(position.side_to_move),
        "ply": None,
        "board": tuple(board),
        "hands": tuple(tuple(row) for row in hands),
        "aux_state": aux_state,
    }


def snapshot_matches(native_snapshot, position, native_rules, compiled=None) -> bool:
    expected = expected_snapshot(position, native_rules, compiled)
    return (
        int(native_snapshot["side"]) == expected["side"]
        and tuple(native_snapshot["board"]) == expected["board"]
        and tuple(tuple(row) for row in native_snapshot["hands"]) == expected["hands"]
        and tuple(native_snapshot.get("aux_state", ())) == expected["aux_state"]
    )


class NativeSemanticPositionMirror:
    """O(depth) stack of Native semantic position capsules."""

    __slots__ = (
        "compiled", "native_rules", "_position", "_parents", "counters",
        "history_certified", "_root_position_key",
    )

    def __init__(self, compiled, native_rules, position, *, history_certified: bool):
        self.compiled = compiled
        self.native_rules = native_rules
        self._position = position
        self._parents = []
        self.counters = MirrorCounters(root_packs=1)
        self.history_certified = bool(history_certified)
        self._root_position_key = None

    @classmethod
    def from_state(cls, compiled, native_rules, state, *, history_certified: bool):
        if not getattr(native_rules, "native_executable", False):
            raise MirrorUnavailable("ruleset is not Native executable")
        if native_rules.fingerprint != compiled.ruleset_fingerprint:
            raise MirrorUnavailable("Native/Python ruleset fingerprint mismatch")
        if not history_certified:
            raise MirrorUnavailable("root history is opaque or not certified by Python runtime")
        started = time.perf_counter()
        payload = _position_payload(compiled, native_rules, state)
        position = pack_position(native_rules, payload)
        mirror = cls(compiled, native_rules, position, history_certified=True)
        mirror.counters.root_pack_seconds = time.perf_counter() - started
        mirror._root_position_key = str(position_identity_key(state.position, compiled))
        return mirror

    @property
    def position(self):
        return self._position

    @property
    def depth(self) -> int:
        return len(self._parents)

    def direct_pack(self, action, python_parent_position) -> int:
        started = time.perf_counter()
        packed = pack_semantic_action(self.native_rules, python_parent_position, action)
        self.counters.action_packs += 1
        self.counters.action_pack_seconds += time.perf_counter() - started
        return packed

    def push(self, action, python_parent_position):
        started = time.perf_counter()
        packed = self.direct_pack(action, python_parent_position)
        child_started = time.perf_counter()
        child = make_checked(self.native_rules, self._position, packed)
        self.counters.native_makes += 1
        self.counters.native_make_seconds += time.perf_counter() - child_started
        self._parents.append(self._position)
        self._position = child
        self.counters.mirror_pushes += 1
        self.counters.push_seconds += time.perf_counter() - started
        return child

    def pop(self):
        if not self._parents:
            raise RuntimeError("Native semantic mirror pop underflow")
        started = time.perf_counter()
        self._position = self._parents.pop()
        self.counters.mirror_pops += 1
        self.counters.pop_seconds += time.perf_counter() - started
        return self._position

    def snapshot(self) -> dict:
        return snapshot(self.native_rules, self._position)

    def assert_balanced(self):
        if self._parents:
            raise AssertionError("Native semantic mirror push/pop imbalance")

    def action_fields(self, action, python_parent_position) -> dict:
        return _semantic_action_fields(self.native_rules, python_parent_position, action)

    def summary(self) -> dict:
        values = self.counters.summary()
        values.update({"depth": self.depth, "history_certified": self.history_certified})
        return values


@contextmanager
def mirrored_pushed(runtime, mirror: NativeSemanticPositionMirror, action, checkpoint=None):
    """Atomically advance Python and Native DFS state for an opt-in shadow."""
    parent_position = runtime.position
    runtime.push(action, checkpoint=checkpoint)
    try:
        mirror.push(action, parent_position)
    except BaseException:
        runtime.pop()
        raise
    try:
        yield runtime.state
    finally:
        try:
            mirror.pop()
        finally:
            runtime.pop()


__all__ = [
    "MirrorUnavailable",
    "MirrorCounters",
    "NativeSemanticPositionMirror",
    "expected_snapshot",
    "pack_semantic_action",
    "snapshot_matches",
    "mirrored_pushed",
]
