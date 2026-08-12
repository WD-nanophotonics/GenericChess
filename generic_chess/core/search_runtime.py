"""Mutable, collision-aware search-path state owned by Core.

The immutable :class:`GameState` and its SHA-256 identity remain the public
and cross-process boundary.  This module is the private DFS data plane used by
AlphaBeta.  Successful child pushes use a process-local 128-bit hash and an
exact in-memory position guard; they never need to manufacture an external
stable key.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .actions import Action, BoardMove, DropMove, action_to_dict
from .attacks import is_in_check
from .errors import IllegalActionError, ensure_ruleset_match
from .identity import ExternalStableKey, RuntimeHash, position_identity_key
from .movegen import _apply_action_unchecked, iter_legal_actions_from_position
from .position import GameState, HistoryRecord, Position
from .semantic_executor import _semantic_public_action, semantic_engine_for
from .terminal import TerminalResult, TerminalStatus, terminal_from_search_runtime


MASK64 = (1 << 64) - 1


@dataclass(frozen=True, slots=True)
class RuntimePositionIdentity:
    """Exact in-process position identity used after the root import."""

    position: Position


@dataclass(frozen=True, slots=True)
class _ImportedIdentity:
    """Opaque identity for a historical position supplied only as a SHA."""

    external_key: str


@dataclass(frozen=True, slots=True)
class RuntimeHistoryRecord:
    identity: object
    actor: int
    action_signature: str
    gave_check: bool = False
    runtime_hash: RuntimeHash | None = None
    external_key: str | None = None

    @property
    def position_key(self):
        """Compatibility view; new child records intentionally have no SHA."""
        return self.external_key


@dataclass(frozen=True, slots=True)
class RuntimeSearchState:
    """Read-only search view backed by a mutable ``SearchPathRuntime``."""

    _runtime: "SearchPathRuntime"

    @property
    def position(self):
        return self._runtime.position

    @property
    def ply_count(self):
        return self._runtime.ply_count

    @property
    def terminal_status(self):
        return self._runtime.terminal_status


def _identity_sort_key(identity: object) -> str:
    if isinstance(identity, RuntimePositionIdentity):
        return "position:" + repr(identity.position)
    if isinstance(identity, _ImportedIdentity):
        return "imported:" + identity.external_key
    return repr(identity)


def _identity_equal(left: object, right: object) -> bool:
    if isinstance(left, RuntimePositionIdentity) and isinstance(right, RuntimePositionIdentity):
        return left.position == right.position
    if isinstance(left, _ImportedIdentity) and isinstance(right, _ImportedIdentity):
        return left.external_key == right.external_key
    return left == right


def _identity_token(identity: object) -> bytes:
    return _token(("identity", _identity_sort_key(identity))).lo.to_bytes(8, "little") + _token(("identity-hi", _identity_sort_key(identity))).hi.to_bytes(8, "little")


@dataclass(frozen=True, slots=True)
class RuntimeCountsSnapshot:
    """Persistent repetition counts with an order-independent fast digest.

    Updates retain a parent pointer, so pop restores the parent in O(1).  The
    exact map is materialized only for explicit inspection or a digest
    collision; normal TT hashing/probing uses only ``digest``.
    """

    parent: "RuntimeCountsSnapshot | None"
    key: object | None
    count: int
    previous_count: int
    digest: bytes
    root_items: tuple[tuple[object, int], ...] = ()

    @staticmethod
    def _entry_digest(key: object, count: int) -> bytes:
        return hashlib.blake2b(
            b"generic-chess-runtime-count\0" + _identity_token(key) + str(count).encode("ascii"),
            digest_size=16,
        ).digest()

    @classmethod
    def from_counts(cls, counts: Mapping[object, int]):
        raw = tuple(sorted(((key, int(count)) for key, count in counts.items() if int(count)), key=lambda item: _identity_sort_key(item[0])))
        digest = bytes(16)
        for key, count in raw:
            digest = _xor_bytes(digest, cls._entry_digest(key, count))
        return cls(None, None, 0, 0, digest, raw)

    def items(self) -> tuple[tuple[object, int], ...]:
        values: dict[object, int] = {}
        if self.parent is None:
            values.update(dict(self.root_items))
        else:
            values.update(dict(self.parent.items()))
            if self.key is not None:
                if self.count:
                    values[self.key] = self.count
                else:
                    values.pop(self.key, None)
        return tuple(sorted(values.items(), key=lambda item: _identity_sort_key(item[0])))

    def count_for(self, key: object) -> int:
        if self.parent is None:
            return dict(self.root_items).get(key, 0)
        if self.key is not None and _identity_equal(self.key, key):
            return self.count
        return self.parent.count_for(key)

    def __hash__(self):
        return int.from_bytes(self.digest[:8], "big")

    def __eq__(self, other):
        if not isinstance(other, RuntimeCountsSnapshot):
            return NotImplemented
        if self.digest != other.digest:
            return False
        return self.items() == other.items()

    def updated(self, key: object, count: int, previous_count: int | None = None):
        if previous_count is None:
            previous_count = self.count_for(key)
        digest = self.digest
        if previous_count:
            digest = _xor_bytes(digest, self._entry_digest(key, previous_count))
        if count:
            digest = _xor_bytes(digest, self._entry_digest(key, count))
        return RuntimeCountsSnapshot(self, key, int(count), int(previous_count), digest)


@dataclass(frozen=True, slots=True)
class RuntimeSearchKey:
    """Exact path-aware key for the runtime's optional TT boundary."""

    ruleset_fingerprint: str
    runtime_hash: RuntimeHash
    position_key: RuntimePositionIdentity
    repetition: RuntimeCountsSnapshot
    ply_count: int


@dataclass(slots=True)
class _Frame:
    position: Position
    ply_count: int
    terminal_status: TerminalResult
    identity: RuntimePositionIdentity
    runtime_hash: RuntimeHash
    snapshot: RuntimeCountsSnapshot
    cache: tuple[Action, ...] | None
    bindings: dict[Action, object]


@dataclass(slots=True)
class _Occurrence:
    identity: object
    count: int


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))


def _token(value: Any) -> RuntimeHash:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=list).encode()
    digest = hashlib.blake2b(b"generic-chess-runtime-token\0" + raw, digest_size=16).digest()
    return RuntimeHash(int.from_bytes(digest[:8], "little"), int.from_bytes(digest[8:], "little"))


def _xor(left: RuntimeHash, right: RuntimeHash) -> RuntimeHash:
    return RuntimeHash((left.lo ^ right.lo) & MASK64, (left.hi ^ right.hi) & MASK64)


def _component_map(position: Position, compiled) -> dict[tuple, object]:
    """Build the exact F1 identity component map for root/oracle/fallback use."""
    values: dict[tuple, object] = {
        ("ruleset",): compiled.ruleset_fingerprint,
        ("side",): position.side_to_move,
    }
    for index, piece in enumerate(position.board):
        values[("board", index)] = None if piece is None else (
            piece.owner, piece.base_type_id, piece.current_type_id, piece.promoted
        )
    for owner, hand in enumerate(position.hands):
        values[("hand", owner)] = tuple(hand.counts)
    engine = semantic_engine_for(compiled)
    if engine is not None:
        physical = dict(position.aux_state)
        covered = set()
        for slot in engine.ir.aux_slots:
            owners = (-1,) if slot.scope == "global" else (0, 1)
            for owner in owners:
                address = (slot.slot_id, owner)
                covered.add(address)
                values[("aux", address)] = physical.get(address, slot.initial)
        for address, value in position.aux_state:
            if address not in covered:
                values[("aux_unknown", address)] = value
    return values


def _component_token(address: tuple, value: object) -> RuntimeHash:
    return _token((address, value))


def _full_runtime_hash(position: Position, compiled) -> RuntimeHash:
    value = RuntimeHash(0, 0)
    for address, component in _component_map(position, compiled).items():
        value = _xor(value, _component_token(address, component))
    return value


def _legacy_incremental_hash(parent: Position, child: Position, action: Action, compiled, current: RuntimeHash) -> RuntimeHash:
    """Update only side, touched cells, and changed hand components."""
    value = current
    changed_cells: set[int] = set()
    changed_hands: set[int] = set()
    if isinstance(action, BoardMove):
        size = compiled.board_size
        changed_cells.update({action.from_square.rank * size + action.from_square.file, action.to_square.rank * size + action.to_square.file})
        changed_hands.update(owner for owner in (0, 1) if parent.hands[owner] != child.hands[owner])
    elif isinstance(action, DropMove):
        size = compiled.board_size
        changed_cells.add(action.to_square.rank * size + action.to_square.file)
        changed_hands.add(parent.side_to_move)
    else:
        raise TypeError("semantic action requires component-diff fallback")
    value = _xor(value, _component_token(("side",), parent.side_to_move))
    value = _xor(value, _component_token(("side",), child.side_to_move))
    for index in changed_cells:
        old = _component_map_cell(parent, index)
        new = _component_map_cell(child, index)
        if old != new:
            value = _xor(value, _component_token(("board", index), old))
            value = _xor(value, _component_token(("board", index), new))
    for owner in changed_hands:
        old = tuple(parent.hands[owner].counts)
        new = tuple(child.hands[owner].counts)
        if old != new:
            value = _xor(value, _component_token(("hand", owner), old))
            value = _xor(value, _component_token(("hand", owner), new))
    return value


def _component_map_cell(position: Position, index: int):
    piece = position.board[index]
    return None if piece is None else (piece.owner, piece.base_type_id, piece.current_type_id, piece.promoted)


def _semantic_component_diff_hash(parent: Position, child: Position, compiled, current: RuntimeHash) -> RuntimeHash:
    before = _component_map(parent, compiled)
    after = _component_map(child, compiled)
    value = current
    for address in before.keys() | after.keys():
        old = before.get(address)
        new = after.get(address)
        if old != new:
            if address in before:
                value = _xor(value, _component_token(address, old))
            if address in after:
                value = _xor(value, _component_token(address, new))
    return value


class SearchPathRuntime:
    """Core-owned mutable DFS context with strict exception-safe undo."""

    def __init__(self, state: GameState, compiled, *, hash_override=None):
        ensure_ruleset_match(state.position, compiled)
        self.compiled = compiled
        self.position = state.position
        self.ply_count = state.ply_count
        self.terminal_status = state.terminal_status
        self._external_root_key = ExternalStableKey(position_identity_key(self.position, compiled))
        self._identity = RuntimePositionIdentity(self.position)
        self._counts_external = dict(state.repetition_counts)
        self._history_complete = bool(state.history)
        if self._counts_external and any(int(count) <= 0 for count in self._counts_external.values()):
            raise ValueError("malformed imported repetition counts")
        if state.history:
            occurrences: dict[str, int] = {}
            for record in state.history:
                occurrences[record.position_key] = occurrences.get(record.position_key, 0) + 1
            if (
                state.history[-1].position_key != self._external_root_key
                or set(occurrences) != {key for key, count in self._counts_external.items() if count > 0}
                or any(self._counts_external.get(key) != count for key, count in occurrences.items())
            ):
                raise ValueError("malformed imported history/repetition counts")
        self._history: list[RuntimeHistoryRecord] = []
        if state.history:
            for record in state.history:
                identity = self._identity if record.position_key == self._external_root_key else _ImportedIdentity(record.position_key)
                runtime_hash = self._runtime_hash_for_identity(identity)
                self._history.append(RuntimeHistoryRecord(identity, record.actor, record.action_signature, record.gave_check, runtime_hash, record.position_key))
        else:
            self._history.append(RuntimeHistoryRecord(self._identity, -1, "", False, None, self._external_root_key))
        self._forced_hash = hash_override
        self.runtime_hash = self._coerce_hash(hash_override) if hash_override is not None else _full_runtime_hash(self.position, compiled)
        self._occurrences: dict[RuntimeHash, list[_Occurrence]] = {}
        self._seed_occurrences()
        self._snapshot = self._snapshot_from_occurrences()
        self._frames: list[_Frame] = []
        self._legal_cache: tuple[Action, ...] | None = None
        self._bindings: dict[Action, object] = {}
        self._view = RuntimeSearchState(self)
        self.stats = None
        self.pushes = 0
        self.pops = 0
        self.hash_updates = 0
        self.exact_key_computations = 1
        self.child_external_key_computations = 0
        self.exact_position_comparisons = 0
        self.legacy_incremental_updates = 0
        self.semantic_full_diff_fallbacks = 0
        self.snapshot_exact_comparisons = 0
        self.collision_checks = 0
        self.collision_fallbacks = 0
        self.peak_depth = 0

    @staticmethod
    def _coerce_hash(value) -> RuntimeHash:
        if isinstance(value, RuntimeHash):
            return value
        return RuntimeHash(int(value), int(value))

    def _runtime_hash_for_identity(self, identity: object) -> RuntimeHash:
        if isinstance(identity, RuntimePositionIdentity) and identity.position == self.position:
            return self.runtime_hash if hasattr(self, "runtime_hash") else _full_runtime_hash(identity.position, self.compiled)
        return _token(("imported", _identity_sort_key(identity)))

    def _seed_occurrences(self):
        for key, count in self._counts_external.items():
            identity = self._identity if key == self._external_root_key else _ImportedIdentity(key)
            runtime_hash = self.runtime_hash if identity is self._identity else _token(("imported", key))
            self._occurrence_add(identity, runtime_hash, int(count), count_collision=False)
        if not self._counts_external:
            self._occurrence_add(self._identity, self.runtime_hash, 1, count_collision=False)
        elif self._external_root_key not in self._counts_external:
            self._occurrence_add(self._identity, self.runtime_hash, 1, count_collision=False)

    def _snapshot_from_occurrences(self):
        values = {}
        for bucket in self._occurrences.values():
            for entry in bucket:
                values[entry.identity] = entry.count
        return RuntimeCountsSnapshot.from_counts(values)

    @classmethod
    def from_state(cls, state: GameState, compiled, *, hash_override=None):
        return cls(state, compiled, hash_override=hash_override)

    @property
    def state(self):
        return self._view

    @property
    def history(self):
        return self._history

    @property
    def repetition_counts(self):
        # Compatibility projection only.  Search/terminal use the private
        # collision-aware occurrence table and never request this projection.
        if not self._frames:
            return dict(self._counts_external)
        return {entry.identity: entry.count for bucket in self._occurrences.values() for entry in bucket}

    @property
    def current_key(self):
        return self._identity

    @property
    def current_identity(self):
        return self._identity

    @property
    def depth(self):
        return len(self._frames)

    def search_key(self):
        return RuntimeSearchKey(self.compiled.ruleset_fingerprint, self.runtime_hash, self._identity, self._snapshot, self.ply_count)

    def attach_stats(self, stats):
        self.stats = stats
        self._sync_stats()

    def _sync_stats(self):
        if self.stats is None:
            return
        self.stats.runtime_pushes = self.pushes
        self.stats.runtime_pops = self.pops
        self.stats.runtime_hash_updates = self.hash_updates
        self.stats.runtime_exact_key_computations = self.exact_key_computations
        self.stats.runtime_child_external_key_computations = self.child_external_key_computations
        self.stats.runtime_exact_position_comparisons = self.exact_position_comparisons
        self.stats.runtime_legacy_incremental_updates = self.legacy_incremental_updates
        self.stats.runtime_semantic_full_diff_fallbacks = self.semantic_full_diff_fallbacks
        self.stats.runtime_snapshot_exact_comparisons = self.snapshot_exact_comparisons
        self.stats.runtime_collision_checks = self.collision_checks
        self.stats.runtime_collision_fallbacks = self.collision_fallbacks
        self.stats.runtime_root_imports = 1
        self.stats.runtime_peak_depth = self.peak_depth
        self.stats.runtime_depth_balanced = not self._frames and self.pushes == self.pops

    def legal_actions(self, checkpoint=None) -> tuple[Action, ...]:
        if self._legal_cache is not None:
            return self._legal_cache
        if self.terminal_status.status is not TerminalStatus.ONGOING:
            self._legal_cache = ()
            return self._legal_cache
        engine = semantic_engine_for(self.compiled)
        if engine is not None:
            actions = []
            bindings = {}
            for semantic_action, binding in engine.iter_legal_action_bindings(self.position, checkpoint=checkpoint):
                public = _semantic_public_action(engine, semantic_action)
                actions.append(public)
                bindings[public] = (semantic_action, binding)
            self._bindings = bindings
        else:
            actions = list(iter_legal_actions_from_position(self.position, self.compiled, checkpoint=checkpoint))
            self._bindings = {}
        self._legal_cache = tuple(actions)
        return self._legal_cache

    def _gave_check(self, position, checkpoint=None):
        engine = semantic_engine_for(self.compiled)
        return engine.in_check(position, position.side_to_move, checkpoint=checkpoint) if engine is not None else is_in_check(position, position.side_to_move, self.compiled)

    def _find_occurrence(self, identity: object, runtime_hash: RuntimeHash, *, instrument: bool = True):
        bucket = self._occurrences.setdefault(runtime_hash, [])
        if instrument:
            self.collision_checks += 1
        for entry in bucket:
            if instrument:
                self.exact_position_comparisons += 1
            if _identity_equal(entry.identity, identity):
                return bucket, entry
        if instrument and bucket:
            self.collision_fallbacks += 1
        return bucket, None

    def _occurrence_add(self, identity: object, runtime_hash: RuntimeHash, count: int = 1, *, count_collision: bool = True) -> int:
        bucket, entry = self._find_occurrence(identity, runtime_hash) if count_collision else (self._occurrences.setdefault(runtime_hash, []), None)
        if entry is None:
            entry = _Occurrence(identity, int(count))
            bucket.append(entry)
            return 0
        previous = entry.count
        entry.count += int(count)
        return previous

    def _occurrence_remove(self, identity: object, runtime_hash: RuntimeHash):
        bucket, entry = self._find_occurrence(identity, runtime_hash)
        if entry is None:
            raise AssertionError("runtime occurrence underflow")
        entry.count -= 1
        if entry.count <= 0:
            bucket.remove(entry)
        if not bucket:
            self._occurrences.pop(runtime_hash, None)

    def occurrence_count(self, identity: object | None = None, runtime_hash: RuntimeHash | None = None) -> int:
        identity = identity or self._identity
        runtime_hash = runtime_hash or self.runtime_hash
        _, entry = self._find_occurrence(identity, runtime_hash, instrument=False)
        return 0 if entry is None else entry.count

    def history_occurrences(self, identity: object) -> list[int]:
        return [index for index, record in enumerate(self._history) if _identity_equal(record.identity, identity)]

    def push(self, action: Action, checkpoint=None) -> RuntimeSearchState:
        before_depth = len(self._frames)
        before_history_len = len(self._history)
        before_identity = self._identity
        before_position = self.position
        before_ply = self.ply_count
        before_status = self.terminal_status
        before_hash = self.runtime_hash
        before_snapshot = self._snapshot
        before_cache = self._legal_cache
        before_bindings = self._bindings
        try:
            return self._push_impl(action, checkpoint)
        except BaseException:
            while len(self._history) > before_history_len:
                record = self._history.pop()
                self._occurrence_remove(record.identity, record.runtime_hash or self.runtime_hash)
            del self._frames[before_depth:]
            self.position = before_position
            self.ply_count = before_ply
            self.terminal_status = before_status
            self._identity = before_identity
            self.runtime_hash = before_hash
            self._snapshot = before_snapshot
            self._legal_cache = before_cache
            self._bindings = before_bindings
            self._sync_stats()
            raise

    def _push_impl(self, action: Action, checkpoint=None) -> RuntimeSearchState:
        if action not in self.legal_actions(checkpoint):
            raise IllegalActionError(f"action is not legal in the current state: {action}")
        self._frames.append(_Frame(self.position, self.ply_count, self.terminal_status, self._identity, self.runtime_hash, self._snapshot, self._legal_cache, self._bindings))
        parent = self.position
        engine = semantic_engine_for(self.compiled)
        if engine is not None:
            semantic_action, binding = self._bindings[action]
            child = engine._transition(parent, semantic_action, binding, checkpoint=checkpoint)
        else:
            child = _apply_action_unchecked(parent, action, self.compiled)
        gave_check = self._gave_check(child, checkpoint)
        child_identity = RuntimePositionIdentity(child)
        if self._forced_hash is not None:
            child_hash = self.runtime_hash
        elif engine is None:
            child_hash = _legacy_incremental_hash(parent, child, action, self.compiled, self.runtime_hash)
            self.legacy_incremental_updates += 1
        else:
            child_hash = _semantic_component_diff_hash(parent, child, self.compiled, self.runtime_hash)
            self.semantic_full_diff_fallbacks += 1
        self.position = child
        self.ply_count += 1
        self._identity = child_identity
        previous_count = self._occurrence_add(child_identity, child_hash)
        self._snapshot = self._snapshot.updated(child_identity, previous_count + 1, previous_count)
        signature = json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))
        self._history.append(RuntimeHistoryRecord(child_identity, parent.side_to_move, signature, gave_check, child_hash, None))
        self.runtime_hash = child_hash
        self._legal_cache = None
        self._bindings = {}
        self.terminal_status = terminal_from_search_runtime(self, checkpoint)
        self.hash_updates += 1
        self.pushes += 1
        self.peak_depth = max(self.peak_depth, len(self._frames))
        self._sync_stats()
        return self._view

    def pop(self) -> RuntimeSearchState:
        if not self._frames:
            raise RuntimeError("search runtime pop underflow")
        current = self._history.pop()
        self._occurrence_remove(current.identity, current.runtime_hash or self.runtime_hash)
        frame = self._frames.pop()
        self.position = frame.position
        self.ply_count = frame.ply_count
        self.terminal_status = frame.terminal_status
        self._identity = frame.identity
        self.runtime_hash = frame.runtime_hash
        self._snapshot = frame.snapshot
        self._legal_cache = frame.cache
        self._bindings = frame.bindings
        self.pops += 1
        self._sync_stats()
        return self._view

    @contextmanager
    def pushed(self, action: Action, checkpoint=None):
        self.push(action, checkpoint)
        try:
            yield self._view
        finally:
            self.pop()

    def assert_balanced(self):
        if self._frames or self.pushes != self.pops:
            raise AssertionError("search runtime push/pop imbalance")


__all__ = [
    "RuntimeHistoryRecord",
    "RuntimePositionIdentity",
    "RuntimeSearchState",
    "RuntimeCountsSnapshot",
    "RuntimeSearchKey",
    "SearchPathRuntime",
    "_component_map",
    "_full_runtime_hash",
]
