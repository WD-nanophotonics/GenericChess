"""Mutable, undoable search-path state owned by Core.

``GameState`` remains the immutable public state container.  This module is
the private DFS data plane used by AlphaBeta: a node is entered with
``push(action)`` and left with ``pop()``.  No runtime object is serialized or
shared with Session, replay, UI, or records.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from dataclasses import dataclass

from .actions import Action, action_to_dict
from .attacks import is_in_check
from .errors import IllegalActionError, ensure_ruleset_match
from .identity import ExternalStableKey, RuntimeHash, position_identity_key
from .movegen import _apply_action_unchecked, iter_legal_actions_from_position
from .position import GameState, HistoryRecord, Position
from .semantic_executor import _semantic_public_action, semantic_engine_for
from .terminal import TerminalResult, TerminalStatus, terminal_from_search_runtime


MASK64 = (1 << 64) - 1


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


@dataclass(frozen=True, slots=True)
class RuntimeCountsSnapshot:
    """Persistent repetition-count update; equality has an exact guard."""

    parent: "RuntimeCountsSnapshot | None"
    key: str | None
    count: int
    digest: bytes
    root_items: tuple[tuple[str, int], ...] = ()

    @classmethod
    def from_counts(cls, counts: dict[str, int]):
        raw = tuple(sorted(counts.items()))
        digest = hashlib.blake2b(repr(raw).encode(), digest_size=16).digest()
        return cls(None, None, 0, digest, raw)

    def items(self) -> tuple[tuple[str, int], ...]:
        if self.parent is None:
            return self.root_items
        values = dict(self.parent.items())
        if self.count:
            values[self.key] = self.count
        return tuple(sorted(values.items()))

    def __hash__(self):
        return int.from_bytes(self.digest[:8], "big")

    def __eq__(self, other):
        if not isinstance(other, RuntimeCountsSnapshot):
            return NotImplemented
        return self.digest == other.digest and self.items() == other.items()

    def updated(self, key: str, count: int):
        raw = self.digest + key.encode() + b"\0" + str(count).encode()
        digest = hashlib.blake2b(raw, digest_size=16).digest()
        return RuntimeCountsSnapshot(self, key, count, digest)


@dataclass(frozen=True, slots=True)
class RuntimeSearchKey:
    """Exact path-aware key for the runtime's optional TT boundary."""

    ruleset_fingerprint: str
    position_key: ExternalStableKey
    repetition: RuntimeCountsSnapshot
    ply_count: int


@dataclass(slots=True)
class _Frame:
    position: Position
    ply_count: int
    terminal_status: TerminalResult
    key: ExternalStableKey
    runtime_hash: RuntimeHash
    snapshot: RuntimeCountsSnapshot
    cache: tuple[Action, ...] | None
    bindings: dict[Action, object]


def _component_values(position: Position, compiled):
    """Canonical component values matching the F1 identity inputs."""
    values = [("ruleset", compiled.ruleset_fingerprint), ("side", position.side_to_move)]
    for index, piece in enumerate(position.board):
        values.append(("board", index, None if piece is None else (
            piece.owner, piece.base_type_id, piece.current_type_id, piece.promoted
        )))
    for owner, hand in enumerate(position.hands):
        values.append(("hand", owner, tuple(hand.counts)))
    engine = semantic_engine_for(compiled)
    if engine is not None:
        slots = engine.ir.aux_slots
        covered = set()
        logical = {}
        for slot in slots:
            owners = (-1,) if slot.scope == "global" else (0, 1)
            for owner in owners:
                key = (slot.slot_id, owner)
                covered.add(key)
                value = slot.initial
                for physical, candidate in position.aux_state:
                    if physical == key:
                        value = candidate
                        break
                logical[key] = value
        for key, value in sorted(logical.items()):
            values.append(("aux", key, value))
        for key, value in position.aux_state:
            if key not in covered:
                values.append(("aux_unknown", key, value))
    return tuple(values)


def _token(component) -> RuntimeHash:
    raw = json.dumps(component, sort_keys=True, separators=(",", ":"), default=list).encode()
    digest = hashlib.blake2b(raw, digest_size=16).digest()
    return RuntimeHash(
        int.from_bytes(digest[:8], "little"),
        int.from_bytes(digest[8:], "little"),
    )


def _xor(a: RuntimeHash, b: RuntimeHash) -> RuntimeHash:
    return RuntimeHash((a.lo ^ b.lo) & MASK64, (a.hi ^ b.hi) & MASK64)


def _full_runtime_hash(position: Position, compiled) -> RuntimeHash:
    value = RuntimeHash(0, 0)
    for component in _component_values(position, compiled):
        value = _xor(value, _token(component))
    return value


def _delta_runtime_hash(parent: Position, child: Position, compiled, current: RuntimeHash):
    before = _component_values(parent, compiled)
    after = _component_values(child, compiled)
    value = current
    for old, new in zip(before, after):
        if old != new:
            value = _xor(value, _token(old))
            value = _xor(value, _token(new))
    return value


class SearchPathRuntime:
    """Core-owned mutable DFS context with strict exception-safe undo."""

    def __init__(self, state: GameState, compiled, *, hash_override=None):
        ensure_ruleset_match(state.position, compiled)
        self.compiled = compiled
        self.position = state.position
        self.ply_count = state.ply_count
        self.terminal_status = state.terminal_status
        self._key = ExternalStableKey(position_identity_key(self.position, compiled))
        self._counts = dict(state.repetition_counts)
        self._history = list(state.history)
        self._history_complete = bool(self._history)
        if self._history:
            occurrences: dict[str, int] = {}
            for record in self._history:
                occurrences[record.position_key] = occurrences.get(record.position_key, 0) + 1
            if self._history[-1].position_key != self._key or any(
                self._counts.get(key, 0) != count for key, count in occurrences.items()
            ):
                raise ValueError("malformed imported history/repetition counts")
        else:
            # A few legacy callers construct a synthetic GameState without
            # history.  Preserve that compatibility for imported SFEN roots;
            # continuous-check adjudication is disabled for this synthesized
            # one-record history because the omitted prior cycle is unknown.
            self._history.append(HistoryRecord(self._key, -1, "", False))
            self._history_complete = False
        self._snapshot = RuntimeCountsSnapshot.from_counts(self._counts)
        self._forced_hash = hash_override
        self.runtime_hash = (
            hash_override if isinstance(hash_override, RuntimeHash)
            else RuntimeHash(int(hash_override), int(hash_override))
            if hash_override is not None else _full_runtime_hash(self.position, compiled)
        )
        self._frames: list[_Frame] = []
        self._legal_cache: tuple[Action, ...] | None = None
        self._bindings: dict[Action, object] = {}
        self._view = RuntimeSearchState(self)
        self.stats = None
        self.pushes = 0
        self.pops = 0
        self.hash_updates = 0
        self.exact_key_computations = 1
        self.collision_checks = 0
        self.collision_fallbacks = 0
        self._hash_buckets: dict[RuntimeHash, set[str]] = {self.runtime_hash: {self._key}}
        self.peak_depth = 0

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
        return self._counts

    @property
    def current_key(self):
        return self._key

    @property
    def depth(self):
        return len(self._frames)

    def search_key(self):
        return RuntimeSearchKey(
            self.compiled.ruleset_fingerprint,
            self._key,
            self._snapshot,
            self.ply_count,
        )

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
            for semantic_action, binding in engine.iter_legal_action_bindings(
                self.position, checkpoint=checkpoint
            ):
                public = _semantic_public_action(engine, semantic_action)
                actions.append(public)
                bindings[public] = (semantic_action, binding)
            self._bindings = bindings
        else:
            actions = list(iter_legal_actions_from_position(
                self.position, self.compiled, checkpoint=checkpoint
            ))
            self._bindings = {}
        self._legal_cache = tuple(actions)
        return self._legal_cache

    def _gave_check(self, position, checkpoint=None):
        engine = semantic_engine_for(self.compiled)
        return (
            engine.in_check(position, position.side_to_move, checkpoint=checkpoint)
            if engine is not None else is_in_check(position, position.side_to_move, self.compiled)
        )

    def push(self, action: Action, checkpoint=None) -> RuntimeSearchState:
        """Push one legal action and restore the parent on any exception."""
        before_depth = len(self._frames)
        before_history_len = len(self._history)
        before_key = self._key
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
            # A failed transition/terminal callback may have incremented only
            # the current child's occurrence.  Undo that single delta, then
            # restore the saved parent view without copying the path on the
            # successful hot path.
            if self._key != before_key or len(self._history) > before_history_len:
                current_count = self._counts.get(self._key, 0)
                if current_count <= 1:
                    self._counts.pop(self._key, None)
                else:
                    self._counts[self._key] = current_count - 1
            del self._history[before_history_len:]
            del self._frames[before_depth:]
            self.position = before_position
            self.ply_count = before_ply
            self.terminal_status = before_status
            self._key = before_key
            self.runtime_hash = before_hash
            self._snapshot = before_snapshot
            self._legal_cache = before_cache
            self._bindings = before_bindings
            self._sync_stats()
            raise

    def _push_impl(self, action: Action, checkpoint=None) -> RuntimeSearchState:
        if action not in self.legal_actions(checkpoint):
            raise IllegalActionError(f"action is not legal in the current state: {action}")
        frame = _Frame(
            self.position, self.ply_count, self.terminal_status, self._key,
            self.runtime_hash, self._snapshot, self._legal_cache, self._bindings,
        )
        self._frames.append(frame)
        parent = self.position
        engine = semantic_engine_for(self.compiled)
        if engine is not None:
            semantic_action, binding = self._bindings[action]
            child = engine._transition(parent, semantic_action, binding, checkpoint=checkpoint)
        else:
            child = _apply_action_unchecked(parent, action, self.compiled)
        child_key = ExternalStableKey(position_identity_key(child, self.compiled))
        self.exact_key_computations += 1
        signature = json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))
        self.position = child
        self.ply_count += 1
        self._key = child_key
        self._counts[child_key] = self._counts.get(child_key, 0) + 1
        self._snapshot = self._snapshot.updated(child_key, self._counts[child_key])
        self._history.append(HistoryRecord(
            child_key, parent.side_to_move, signature, self._gave_check(child, checkpoint)
        ))
        self.runtime_hash = (
            self._forced_hash if self._forced_hash is not None
            else _delta_runtime_hash(parent, child, self.compiled, self.runtime_hash)
        )
        self.hash_updates += 1
        bucket = self._hash_buckets.setdefault(self.runtime_hash, set())
        self.collision_checks += 1
        if child_key not in bucket and bucket:
            self.collision_fallbacks += 1
        bucket.add(child_key)
        self._legal_cache = None
        self._bindings = {}
        self.terminal_status = terminal_from_search_runtime(self, checkpoint)
        self.pushes += 1
        self.peak_depth = max(self.peak_depth, len(self._frames))
        self._sync_stats()
        return self._view

    def pop(self) -> RuntimeSearchState:
        if not self._frames:
            raise RuntimeError("search runtime pop underflow")
        current_key = self._key
        self._counts[current_key] -= 1
        if self._counts[current_key] == 0:
            del self._counts[current_key]
        self._history.pop()
        frame = self._frames.pop()
        self.position = frame.position
        self.ply_count = frame.ply_count
        self.terminal_status = frame.terminal_status
        self._key = frame.key
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
    "RuntimeSearchState",
    "RuntimeCountsSnapshot",
    "RuntimeSearchKey",
    "SearchPathRuntime",
]
