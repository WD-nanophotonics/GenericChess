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
from functools import lru_cache
from dataclasses import dataclass, field, fields, replace
from typing import Any, Callable, Iterable, Mapping

from .actions import Action, BoardMove, DropMove, PassAction, SemanticBoardMove, action_from_dict, action_to_dict
from .attacks import is_in_check
from .errors import IllegalActionError, ensure_ruleset_match
from .identity import ExternalStableKey, RuntimeHash, position_identity_key
from .movegen import (
    _apply_action_unchecked,
    _pass_action_is_legal,
    iter_legal_actions_from_position,
)
from .position import GameState, HistoryRecord, Position
from .no_progress_context import NoProgressContext
from .semantic_executor import _semantic_public_action, semantic_engine_for
from .terminal import TerminalResult, TerminalStatus, terminal_from_search_runtime


MASK64 = (1 << 64) - 1


def _aux_value_equal(left: object, right: object) -> bool:
    """Match the scalar types retained by the public semantic identity."""
    if left is right:
        return True
    if type(left) is not type(right) or left != right:
        return False
    if isinstance(left, tuple):
        return all(_aux_value_equal(a, b) for a, b in zip(left, right))
    return True


@dataclass(frozen=True, slots=True, eq=False)
class RuntimePositionIdentity:
    """Exact in-process position identity used after the root import."""

    position: Position

    def __hash__(self):
        return hash(self.position)

    def __eq__(self, other):
        if not isinstance(other, RuntimePositionIdentity):
            return NotImplemented
        return (
            self.position == other.position
            and _aux_value_equal(self.position.aux_state, other.position.aux_state)
        )


@dataclass(frozen=True, slots=True, eq=False)
class _CachedRuntimePositionIdentity(RuntimePositionIdentity):
    """Lazily reuse the SAME Python hash; exact base equality stays authoritative.

    Position and its board, hands and aux payload are immutable. The memo is
    process-local and never an external key, equality shortcut or serialized ID.
    """
    _cached_hash: int | None = field(default=None, init=False, repr=False)

    def __hash__(self):
        value = self._cached_hash
        if value is None:
            value = hash(self.position)
            object.__setattr__(self, '_cached_hash', value)
        return value


def _runtime_position_identity(position: Position, compiled, *, cache_hash=False) -> RuntimePositionIdentity:
    """Keep semantic default omission equal in the exact collision guard.

    F1 already treats an absent compiled aux slot as its declared default.
    Transitions can materialize that default without changing the logical
    position. Normalize only the private identity; actual state/witnesses and
    external record keys remain unchanged. Foreign aux entries stay present.
    """
    identity_type = _CachedRuntimePositionIdentity if cache_hash else RuntimePositionIdentity
    engine = semantic_engine_for(compiled)
    if engine is None or not position.aux_state:
        return identity_type(position)
    defaults = {
        (slot.slot_id, owner): slot.initial
        for slot in engine.ir.aux_slots
        for owner in ((-1,) if slot.scope == "global" else (0, 1))
    }
    aux = tuple(sorted(
        (item for item in position.aux_state
         if item[0] not in defaults
         or not _aux_value_equal(item[1], defaults[item[0]])),
        key=lambda item: item[0],
    ))
    if aux != position.aux_state:
        position = replace(position, aux_state=aux)
    return identity_type(position)


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
        return left == right
    if isinstance(left, _ImportedIdentity) and isinstance(right, _ImportedIdentity):
        return left.external_key == right.external_key
    return left == right


def _identity_token(identity: object) -> bytes:
    return _token(("identity", _identity_sort_key(identity))).lo.to_bytes(8, "little") + _token(("identity-hi", _identity_sort_key(identity))).hi.to_bytes(8, "little")


@dataclass(frozen=True, slots=True)
class RuntimeCountsSnapshot:
    """Persistent repetition counts with an order-independent fast digest.

    Updates retain a parent pointer, so pop restores the parent in O(1).  The
    exact map is materialized for inspection or exact equality after matching
    digests (including TT hits); hashing uses only ``digest``.
    """

    parent: "RuntimeCountsSnapshot | None"
    key: object | None
    count: int
    previous_count: int
    digest: bytes
    root_items: tuple[tuple[object, int], ...] = ()

    @staticmethod
    def _entry_digest(
        key: object,
        count: int,
        fast_hash: RuntimeHash | None = None,
    ) -> bytes:
        """Return a fast entry discriminator without weakening exact equality.

        Child runtime updates already have the canonical process-local
        ``RuntimeHash``.  Use it here instead of formatting the full Position
        representation.  ``key`` remains the exact identity stored in the
        persistent snapshot, and ``items()`` remains the collision guard.
        Imported/test identities without a runtime hash retain the old
        deterministic fallback.
        """
        if fast_hash is not None:
            token = (
                fast_hash.lo.to_bytes(8, "little", signed=False)
                + fast_hash.hi.to_bytes(8, "little", signed=False)
            )
        else:
            token = _identity_token(key)
        return hashlib.blake2b(
            b"generic-chess-runtime-count\0" + token + str(count).encode("ascii"),
            digest_size=16,
        ).digest()

    @classmethod
    def from_counts(
        cls,
        counts: Mapping[object, int],
        fast_hashes: Mapping[object, RuntimeHash] | None = None,
    ):
        raw = tuple(sorted(((key, int(count)) for key, count in counts.items() if int(count)), key=lambda item: _identity_sort_key(item[0])))
        digest = bytes(16)
        for key, count in raw:
            fast_hash = fast_hashes.get(key) if fast_hashes is not None else None
            entry_digest = (
                cls._entry_digest(key, count, fast_hash)
                if fast_hash is not None
                else cls._entry_digest(key, count)
            )
            digest = _xor_bytes(digest, entry_digest)
        return cls(None, None, 0, 0, digest, raw)

    def items(self) -> tuple[tuple[object, int], ...]:
        # A matching digest still needs the exact map (including real TT hits).
        # Rebuilding/sorting every ancestor makes that check quadratic in path
        # length and repeatedly formats full Position identities. Apply the
        # same persistent updates once, oldest first, then keep the canonical
        # sort and exact equality guard unchanged.
        path = []
        ancestor = self
        while ancestor.parent is not None:
            path.append(ancestor)
            ancestor = ancestor.parent
        values: dict[object, int] = dict(ancestor.root_items)
        for update in reversed(path):
            if update.key is not None:
                if update.count:
                    values[update.key] = update.count
                else:
                    values.pop(update.key, None)
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

    def updated(
        self,
        key: object,
        count: int,
        previous_count: int | None = None,
        fast_hash: RuntimeHash | None = None,
    ):
        if previous_count is None:
            previous_count = self.count_for(key)
        digest = self.digest
        if previous_count:
            entry_digest = (
                self._entry_digest(key, previous_count, fast_hash)
                if fast_hash is not None
                else self._entry_digest(key, previous_count)
            )
            digest = _xor_bytes(digest, entry_digest)
        if count:
            entry_digest = (
                self._entry_digest(key, count, fast_hash)
                if fast_hash is not None
                else self._entry_digest(key, count)
            )
            digest = _xor_bytes(digest, entry_digest)
        return RuntimeCountsSnapshot(self, key, int(count), int(previous_count), digest)


@dataclass(frozen=True, slots=True)
class RuntimeSearchKey:
    """Exact path-aware key for the runtime's optional TT boundary."""

    ruleset_fingerprint: str
    runtime_hash: RuntimeHash
    position_key: RuntimePositionIdentity
    repetition: RuntimeCountsSnapshot
    ply_count: int
    history_context: "RuntimeHistoryContext | None" = None


@dataclass(frozen=True, slots=True)
class RuntimeHistoryContext:
    """Persistent exact history evidence for continuous-check TT reuse.

    The digest is only a fast discriminator.  Equality walks the persistent
    parent chain and compares exact identities plus actor/check evidence, so
    forced digest collisions cannot make two histories equivalent.
    """

    parent: "RuntimeHistoryContext | None"
    identity: object
    runtime_hash: RuntimeHash
    actor: int
    gave_check: bool
    length: int
    digest: bytes
    action_signature: str = ""

    @staticmethod
    def _record_digest(
        parent_digest: bytes,
        runtime_hash: RuntimeHash,
        actor: int,
        gave_check: bool,
        action_signature: str = "",
    ) -> bytes:
        return hashlib.blake2b(
            b"generic-chess-runtime-history-context\0"
            + parent_digest
            + runtime_hash.lo.to_bytes(8, "little")
            + runtime_hash.hi.to_bytes(8, "little")
            + int(actor).to_bytes(4, "little", signed=True)
            + bytes((int(bool(gave_check)),))
            + action_signature.encode("utf-8"),
            digest_size=16,
        ).digest()

    @classmethod
    def from_records(cls, records: Iterable[RuntimeHistoryRecord], *, include_actions: bool = False):
        context = None
        for record in records:
            context = cls.append(
                context,
                record.identity,
                record.runtime_hash or RuntimeHash(0, 0),
                record.actor,
                record.gave_check,
                record.action_signature if include_actions else "",
            )
        return context

    @classmethod
    def append(
        cls,
        parent: "RuntimeHistoryContext | None",
        identity: object,
        runtime_hash: RuntimeHash,
        actor: int,
        gave_check: bool,
        action_signature: str = "",
    ) -> "RuntimeHistoryContext":
        parent_digest = parent.digest if parent is not None else bytes(16)
        return cls(
            parent,
            identity,
            runtime_hash,
            int(actor),
            bool(gave_check),
            (parent.length if parent is not None else 0) + 1,
            cls._record_digest(parent_digest, runtime_hash, actor, gave_check, action_signature),
            action_signature,
        )

    def _records_reversed(self):
        current = self
        while current is not None:
            yield current
            current = current.parent

    def __hash__(self):
        return int.from_bytes(self.digest[:8], "big")

    def __eq__(self, other):
        if not isinstance(other, RuntimeHistoryContext):
            return NotImplemented
        if self.length != other.length or self.digest != other.digest:
            return False
        left = self
        right = other
        while left is not None and right is not None:
            if (
                left.actor != right.actor
                or left.gave_check != right.gave_check
                or left.action_signature != right.action_signature
                or not _identity_equal(left.identity, right.identity)
            ):
                return False
            left = left.parent
            right = right.parent
        return left is None and right is None


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
    bridge_key: str | None = None
    bridge_identity: RuntimePositionIdentity | None = None
    bridge_runtime_hash: RuntimeHash | None = None
    bridge_old_hash: RuntimeHash | None = None
    bridge_old_count: int = 0
    child_identity: RuntimePositionIdentity | None = None
    child_runtime_hash: RuntimeHash | None = None
    child_occurrence_added: bool = False
    history_context: RuntimeHistoryContext | None = None
    child_in_check: bool | None = None
    no_progress_context: NoProgressContext | None = None


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
    values = _nonboard_component_map(position, compiled)
    for index, piece in enumerate(position.board):
        values[("board", index)] = None if piece is None else (
            piece.owner, piece.base_type_id, piece.current_type_id, piece.promoted
        )
    return values


def _nonboard_component_map(position: Position, compiled) -> dict[tuple, object]:
    """Project every hand/auxiliary component, including logical defaults."""
    values: dict[tuple, object] = {
        ("ruleset",): compiled.ruleset_fingerprint,
        ("side",): position.side_to_move,
    }
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


def _uncached_component_token(address: tuple, value: object) -> RuntimeHash:
    return _token((address, value))


@lru_cache(maxsize=4096, typed=True)
def _board_component_token(index, owner, base, current, promoted) -> RuntimeHash:
    return _uncached_component_token(("board", index), (owner, base, current, promoted))


@lru_cache(maxsize=256, typed=True)
def _empty_board_component_token(index) -> RuntimeHash:
    return _uncached_component_token(("board", index), None)


@lru_cache(maxsize=4, typed=True)
def _side_component_token(value) -> RuntimeHash:
    return _uncached_component_token(("side",), value)


def _component_token(address: tuple, value: object) -> RuntimeHash:
    # Complete immutable fields, with bool/int kept distinct just as JSON does.
    # Aux/hand/ruleset inputs retain the original serialization and identity.
    if type(address) is tuple and len(address) == 2 and address[0] == "board" and type(address[1]) is int:
        if value is None:
            return _empty_board_component_token(address[1])
        if (type(value) is tuple and len(value) == 4
                and type(value[0]) in (int, bool)
                and type(value[1]) is str and type(value[2]) is str
                and type(value[3]) is bool):
            return _board_component_token(address[1], *value)
    if address == ("side",) and type(value) in (int, bool):
        return _side_component_token(value)
    return _uncached_component_token(address, value)


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
    elif isinstance(action, PassAction):
        pass
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
    """Scan the whole board, avoiding maps/tuples for unchanged cells.

    Compound actions and transition triggers can affect arbitrary cells; the
    action's source/target is deliberately not used as a footprint bound.
    """
    value = current
    for index, (left, right) in enumerate(zip(parent.board, child.board)):
        if left is right:
            continue
        old = _component_map_cell(parent, index)
        new = _component_map_cell(child, index)
        if old != new:
            value = _xor(value, _component_token(("board", index), old))
            value = _xor(value, _component_token(("board", index), new))
    before = _nonboard_component_map(parent, compiled)
    after = _nonboard_component_map(child, compiled)
    for address in before.keys() | after.keys():
        old = before.get(address)
        new = after.get(address)
        if (
            (address in before) != (address in after)
            or old != new
            or (address[0] in ("aux", "aux_unknown")
                and not _aux_value_equal(old, new))
        ):
            if address in before:
                value = _xor(value, _component_token(address, old))
            if address in after:
                value = _xor(value, _component_token(address, new))
    return value


def _plain_leaper_hash_patterns(compiled):
    """Certify a narrow two-cell transition footprint from executable IR.

    This does not certify legal actions or skip Core transition/adjudication.
    Unknown schema fields, arbitrary effects, triggers and promotion fail closed.
    """
    from ..rules.ir import (
        CompiledEffect, CompiledGeometry, CompiledMovePattern,
        CompiledSemanticIR, CompiledSquareRef,
    )
    ir = getattr(compiled, 'ir', None)
    if type(ir) is not CompiledSemanticIR or ir.ir_version != 2:
        return None
    reviewed_fields = {
        Position: 'board hands side_to_move ruleset_fingerprint aux_state board_width board_height',
        CompiledSemanticIR: 'ir_version ruleset_fingerprint geometry zones patterns aux_slots triggers automatic_adjudications declarations capabilities consecutive_action_adjudications repeated_cycle_target_conditions',
        CompiledGeometry: 'geometry_id kind owner_relative offset direction min_steps max_steps atom_source paths',
        CompiledMovePattern: 'pattern_id name type_ids geometry_ids target path guards slot_guards effects invariants postconditions promotion_mode explicit_promotion_type composition replaced_pattern_ids cost_class stratum square_zone_guards',
        CompiledEffect: 'kind from_ref to_ref square_ref piece_owner piece_type_ref disposition slot_id type_ref count value',
        CompiledSquareRef: 'kind square offset owner_relative step slot_id',
    }
    if any({f.name for f in fields(cls)} != set(names.split())
           for cls, names in reviewed_fields.items()):
        return None
    size = compiled.board_size
    if (type(size) is not int or size <= 0
            or compiled.board_shape.width != size
            or compiled.board_shape.height != size):
        return None
    if (not ir.patterns or not ir.geometry or ir.aux_slots or ir.triggers
            or ir.declarations or ir.automatic_adjudications
            or ir.consecutive_action_adjudications or ir.repeated_cycle_target_conditions
            or compiled.pass_enabled or compiled.no_progress_draw is not None):
        return None
    if any(t.is_promotable or t.promotion_target_ids for t in compiled.piece_types):
        return None
    if any(any(owners) for owners in compiled.promotion_allowed.values()):
        return None
    if any(any(owners) for owners in compiled.promotion_forced.values()):
        return None
    if any(type(g) is not CompiledGeometry
           for g in ir.geometry.values()):
        return None
    move = CompiledEffect('move', from_ref=CompiledSquareRef('source'),
                          to_ref=CompiledSquareRef('target'))
    remove = CompiledEffect('remove', square_ref=CompiledSquareRef('target'),
                            piece_owner='opponent', disposition='remove_from_game')
    pairs = set()
    for pattern in ir.patterns:
        if (type(pattern) is not CompiledMovePattern or not pattern.type_ids
                or not pattern.geometry_ids or pattern.path or pattern.guards
                or pattern.slot_guards or pattern.square_zone_guards
                or pattern.postconditions or pattern.explicit_promotion_type is not None
                or pattern.promotion_mode not in ('none', 'inherit_compiled_masks')
                or pattern.composition != 'augment' or pattern.replaced_pattern_ids
                or any(i.kind != 'own_anchor_safe' or i.square_refs
                       for i in pattern.invariants)):
            return None
        # Legacy lowering retains drop patterns even when every allowed mask
        # is false. Core's _iter_drop_candidates cannot produce such an action.
        # Never include them in the certified board-action pairs.
        if all(g in ir.geometry and ir.geometry[g].kind == 'drop'
               for g in pattern.geometry_ids):
            masks = compiled.drop_allowed
            if any(t not in masks or any(any(row) for row in masks[t])
                   for t in pattern.type_ids):
                return None
            continue
        expected = ((move,) if pattern.target.kind == 'target_empty' else
                    (remove, move) if pattern.target.kind == 'target_enemy' else None)
        if expected is None or pattern.effects != expected:
            return None
        for geometry_id in pattern.geometry_ids:
            if geometry_id not in ir.geometry or ir.geometry[geometry_id].kind != 'leap':
                return None
            pairs.add((pattern.pattern_id, geometry_id))
    return frozenset(pairs)


def _plain_leaper_local_hash(parent, child, action, compiled, current, patterns):
    """Same component tokens as full hashing, on a certified two-cell move."""
    if (not isinstance(action, SemanticBoardMove)
            or (action.pattern_id, action.geometry_id) not in patterns
            or action.promotion_target_id is not None
            or parent.hands != child.hands or parent.aux_state or child.aux_state
            or parent.ruleset_fingerprint != child.ruleset_fingerprint
            or parent.board_width != child.board_width
            or parent.board_height != child.board_height
            or len(parent.board) != compiled.board_size ** 2
            or len(parent.board) != len(child.board)
            or parent.board_width not in (None, compiled.board_size)
            or parent.board_height not in (None, compiled.board_size)):
        return None
    size = compiled.board_size
    source = action.from_square.rank * size + action.from_square.file
    target = action.to_square.rank * size + action.to_square.file
    value = _xor(current, _component_token(('side',), parent.side_to_move))
    value = _xor(value, _component_token(('side',), child.side_to_move))
    for index in (source,) if source == target else (source, target):
        old = _component_map_cell(parent, index)
        new = _component_map_cell(child, index)
        if old != new:
            value = _xor(value, _component_token(('board', index), old))
            value = _xor(value, _component_token(('board', index), new))
    return value


class SearchPathRuntime:
    """Core-owned mutable DFS context with strict exception-safe undo."""

    def __init__(
        self,
        state: GameState,
        compiled,
        *,
        hash_override=None,
        history_witnesses=None,
        legal_binding_provider: Callable | None = None,
        availability_provider: Callable | None = None,
        check_provider: Callable | None = None,
        use_plain_leaper_local_hash: bool = False,
        use_cached_position_identity_hash: bool = False,
    ):
        ensure_ruleset_match(state.position, compiled)
        self.compiled = compiled
        admitted = (
            _plain_leaper_hash_patterns(compiled)
            if use_plain_leaper_local_hash or use_cached_position_identity_hash else None
        )
        self._plain_leaper_hash_patterns = admitted if use_plain_leaper_local_hash else None
        self._cache_position_identity_hash = bool(
            use_cached_position_identity_hash and admitted is not None
        )
        # Opaque Core-neutral callback: Core never imports Native and never
        # stores a Native capsule/rules object.
        self.availability_provider = availability_provider
        self._check_provider = check_provider
        self._legal_binding_provider = legal_binding_provider
        self._legal_provider_active = legal_binding_provider is not None
        self.position = state.position
        self.ply_count = state.ply_count
        self.terminal_status = state.terminal_status
        self._external_root_key = ExternalStableKey(position_identity_key(self.position, compiled))
        self._identity = _runtime_position_identity(self.position, compiled,
            cache_hash=self._cache_position_identity_hash)
        self._counts_external = dict(state.repetition_counts)
        if self._counts_external and any(int(count) <= 0 for count in self._counts_external.values()):
            raise ValueError("malformed imported repetition counts")

        self._forced_hash = hash_override
        self.runtime_hash = (
            self._coerce_hash(hash_override)
            if hash_override is not None
            else _full_runtime_hash(self.position, compiled)
        )
        self.history_reconstruction_attempts = 0
        self.history_reconstruction_key_computations = 0
        self.history_witness_hits = 0
        self.history_witness_misses = 0
        self.opaque_history_child_external_key_computations = 0
        self._history_witness_by_key: dict[str, Position] = {}
        self._history_complete = False

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
            witnesses = self._resolve_history_witnesses(state, history_witnesses)
            if witnesses is None:
                witnesses = (None,) * len(state.history)
                self.history_witness_misses = len(state.history)
            else:
                self.history_witness_hits = len(witnesses)
                self._history_witness_by_key = {
                    record.position_key: witness
                    for record, witness in zip(state.history, witnesses)
                }
            self._history_complete = True

        self._history: list[RuntimeHistoryRecord] = []
        # Core-produced history keys already bind each witness to its logical
        # position. Reuse their hashes only within this import, including the
        # occurrence seed; discard the map when construction returns.
        imported_hashes = {str(self._external_root_key): self.runtime_hash}
        if state.history:
            for record, witness in zip(state.history, witnesses):
                identity = self._identity_for_imported_key(record.position_key)
                if witness is not None:
                    identity = (
                        self._identity
                        if witness == self.position
                        and _aux_value_equal(witness.aux_state, self.position.aux_state)
                        else _runtime_position_identity(witness, compiled,
                            cache_hash=self._cache_position_identity_hash)
                    )
                runtime_hash = imported_hashes.get(record.position_key)
                if runtime_hash is None:
                    runtime_hash = self._runtime_hash_for_identity(identity)
                    imported_hashes[record.position_key] = runtime_hash
                self._history.append(
                    RuntimeHistoryRecord(
                        identity,
                        record.actor,
                        record.action_signature,
                        record.gave_check,
                        runtime_hash,
                        record.position_key,
                    )
                )
        else:
            self.history_witness_misses = sum(
                1 for key in self._counts_external if key != self._external_root_key
            )
            self._history.append(
                RuntimeHistoryRecord(
                    self._identity,
                    -1,
                    "",
                    False,
                    None,
                    self._external_root_key,
                )
            )

        self._opaque_imported_keys = {
            key
            for key in self._counts_external
            if key != self._external_root_key
            and key not in self._history_witness_by_key
        }
        if state.history and not self._history_witness_by_key:
            self.history_witness_misses = len(self._opaque_imported_keys)
        self._history_aliases: dict[str, RuntimePositionIdentity] = {}
        # Progress and consecutive-action rules distinguish action paths even
        # when every position/actor/check fact and repetition count is identical.
        self._history_action_sensitive = bool(
            getattr(compiled, "consecutive_action_adjudications", ())
            or getattr(compiled, "no_progress_draw", None)
        )
        self._history_context = RuntimeHistoryContext.from_records(
            self._history, include_actions=self._history_action_sensitive,
        )
        self._history_context_updates = 0
        self._history_context_exact_comparisons = 0
        self._occurrences: dict[RuntimeHash, list[_Occurrence]] = {}
        self._seed_occurrences(imported_hashes)
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
        self.semantic_local_hash_updates = 0
        self.snapshot_exact_comparisons = 0
        self.collision_checks = 0
        self.collision_fallbacks = 0
        self.snapshot_updates = 0
        self.snapshot_entry_digest_calls = 0
        self.search_key_calls = 0
        self.peak_depth = 0
        self.legal_provider_calls = 0
        self.legal_provider_actions = 0
        self.legal_provider_seconds = 0.0
        self.legal_provider_payload_seconds = 0.0
        self.legal_provider_decode_binding_seconds = 0.0
        self.legal_provider_fallbacks = 0
        self.legal_provider_operational_failures = 0
        from .no_progress_context import prepare

        self._no_progress_context = prepare(state, compiled, self._history)
        if getattr(compiled, "no_progress_draw", None) is not None:
            from .terminal import _repeated_cycle_target_history_projection
            _repeated_cycle_target_history_projection(self)
            from .adjudication import IncompleteAdjudicationHistoryError
            if terminal_from_search_runtime(self) != state.terminal_status:
                raise IncompleteAdjudicationHistoryError(
                    "no-progress imported terminal does not match exact rule result"
                )

    @staticmethod
    def _coerce_hash(value) -> RuntimeHash:
        if isinstance(value, RuntimeHash):
            return value
        return RuntimeHash(int(value), int(value))

    def _resolve_history_witnesses(self, state: GameState, supplied):
        if supplied is not None:
            witnesses = tuple(supplied)
            if len(witnesses) != len(state.history):
                raise ValueError("malformed imported history: witness length mismatch")
            for record, witness in zip(state.history, witnesses):
                ensure_ruleset_match(witness, self.compiled)
                # Session/replay witnesses are produced by Core transitions,
                # so the public key was already validated when each record
                # was created. Avoid recomputing every SHA on the search
                # entry hot path.
            return witnesses
        return self._reconstruct_history_witnesses(state)

    def _reconstruct_history_witnesses(self, state: GameState) -> tuple[Position, ...] | None:
        """Replay complete public history into exact private Position witnesses.

        HistoryRecord stays unchanged at the public boundary. Its existing
        canonical action signatures are sufficient to replay a complete,
        authoritative history from initial_state. Any mismatch fails closed
        instead of manufacturing an identity bridge.
        """
        self.history_reconstruction_attempts += 1
        from .transition import apply_action, initial_state

        # This import is only a witness reconstruction. The no-progress root
        # context below independently verifies exact replay and terminal status.
        # Re-adjudicating every prefix here would replay it quadratically.
        no_progress = getattr(self.compiled, "no_progress_draw", None)
        replay_compiled = self.compiled
        if no_progress is not None:
            if hasattr(self.compiled, "support"):
                replay_compiled = replace(
                    self.compiled,
                    support=replace(self.compiled.support, no_progress_draw=None),
                )
            else:
                replay_compiled = replace(self.compiled, no_progress_draw=None)
        try:
            replayed = initial_state(replay_compiled)
            self.history_reconstruction_key_computations += 1
            if not state.history:
                raise ValueError("empty history")
            first = state.history[0]
            if first.actor != -1 or first.action_signature != "" or first.gave_check:
                raise ValueError("invalid initial history record")
            if first.position_key != replayed.history[0].position_key:
                # Public GameState has no setup key. A declared alternate start
                # is still recoverable from its exact initial history record;
                # custom/imported roots retain the opaque-history fallback.
                engine = semantic_engine_for(replay_compiled)
                setups = (
                    engine.support.initial_setup_options
                    if engine is not None
                    else replay_compiled.initial_setup_positions
                )
                for setup_key in sorted(setups):
                    candidate = initial_state(replay_compiled, setup_key)
                    self.history_reconstruction_key_computations += 1
                    if candidate.history[0] == first:
                        replayed = candidate
                        break
                else:
                    raise ValueError("unknown initial history record")
            witnesses = [replayed.position]
            for record in state.history[1:]:
                action = action_from_dict(json.loads(record.action_signature))
                replayed = apply_action(replayed, action, replay_compiled)
                self.history_reconstruction_key_computations += 1
                produced = replayed.history[-1]
                if produced != record:
                    raise ValueError("history record does not replay exactly")
                witnesses.append(replayed.position)

            if (
                _runtime_position_identity(replayed.position, self.compiled)
                != _runtime_position_identity(state.position, self.compiled)
                or replayed.ply_count != state.ply_count
                or replayed.repetition_counts != tuple(state.repetition_counts)
                or (no_progress is None and replayed.terminal_status != state.terminal_status)
            ):
                raise ValueError("replayed history does not match imported state")

            by_key: dict[str, Position] = {}
            for record, witness in zip(state.history, witnesses):
                previous = by_key.get(record.position_key)
                if previous is not None and previous != witness and (
                    _runtime_position_identity(previous, self.compiled)
                    != _runtime_position_identity(witness, self.compiled)
                ):
                    raise ValueError("one external key maps to distinct positions")
                by_key[record.position_key] = witness
            return tuple(witnesses)
        except Exception:
            # A valid public state may have started from a custom/imported
            # root. Its SHA-only history is opaque, so use the conditional
            # child-key bridge instead of inventing exact Positions.
            self.history_witness_misses = len(state.history)
            return None

    def _identity_for_imported_key(self, key: str) -> object:
        if key == self._external_root_key:
            return self._identity
        witness = self._history_witness_by_key.get(key)
        if witness is not None:
            return _runtime_position_identity(witness, self.compiled,
                cache_hash=self._cache_position_identity_hash)
        return _ImportedIdentity(key)

    def _runtime_hash_for_identity(self, identity: object) -> RuntimeHash:
        if self._forced_hash is not None:
            return self.runtime_hash
        if isinstance(identity, RuntimePositionIdentity):
            if identity == self._identity:
                return self.runtime_hash
            return _full_runtime_hash(identity.position, self.compiled)
        return _token(("imported", _identity_sort_key(identity)))

    def _seed_occurrences(self, imported_hashes):
        for key, count in self._counts_external.items():
            identity = self._identity_for_imported_key(key)
            runtime_hash = imported_hashes.get(key)
            if runtime_hash is None:
                runtime_hash = self._runtime_hash_for_identity(identity)
            self._occurrence_add(identity, runtime_hash, int(count), count_collision=False)
        if not self._counts_external:
            self._occurrence_add(self._identity, self.runtime_hash, 1, count_collision=False)
        elif self._external_root_key not in self._counts_external:
            self._occurrence_add(self._identity, self.runtime_hash, 1, count_collision=False)

    def _snapshot_from_occurrences(self):
        values = {}
        fast_hashes = {}
        for runtime_hash, bucket in self._occurrences.items():
            for entry in bucket:
                values[entry.identity] = entry.count
                fast_hashes[entry.identity] = runtime_hash
        return RuntimeCountsSnapshot.from_counts(values, fast_hashes=fast_hashes)

    @classmethod
    def from_state(
        cls,
        state: GameState,
        compiled,
        *,
        hash_override=None,
        history_witnesses=None,
        legal_binding_provider: Callable | None = None,
        availability_provider: Callable | None = None,
        check_provider: Callable | None = None,
        use_plain_leaper_local_hash: bool = False,
        use_cached_position_identity_hash: bool = False,
    ):
        return cls(
            state,
            compiled,
            hash_override=hash_override,
            history_witnesses=history_witnesses,
            legal_binding_provider=legal_binding_provider,
            availability_provider=availability_provider,
            check_provider=check_provider,
            use_plain_leaper_local_hash=use_plain_leaper_local_hash,
            use_cached_position_identity_hash=use_cached_position_identity_hash,
        )

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
        self.search_key_calls += 1
        return RuntimeSearchKey(
            self.compiled.ruleset_fingerprint,
            self.runtime_hash,
            self._identity,
            self._snapshot,
            self.ply_count,
            self._history_context if self.tt_eligible else None,
        )

    @property
    def tt_eligible(self) -> bool:
        """Whether the current history-sensitive terminal rules permit TT use."""
        return bool(
            self._history_complete
            and self.history_witness_misses == 0
            and not self._opaque_imported_keys
            and self._history_context is not None
            and not getattr(
                self.compiled, "repeated_cycle_target_conditions", ()
            )
        )

    def attach_stats(self, stats):
        self.stats = stats
        if self.stats is not None:
            self.stats.runtime_position_identity_hash_cached = self._cache_position_identity_hash
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
        self.stats.runtime_semantic_local_hash_updates = self.semantic_local_hash_updates
        self.stats.runtime_snapshot_exact_comparisons = self.snapshot_exact_comparisons
        self.stats.runtime_collision_checks = self.collision_checks
        self.stats.runtime_collision_fallbacks = self.collision_fallbacks
        if hasattr(self.stats, "runtime_snapshot_updates"):
            self.stats.runtime_snapshot_updates = self.snapshot_updates
            self.stats.runtime_snapshot_entry_digest_calls = self.snapshot_entry_digest_calls
            self.stats.runtime_search_key_calls = self.search_key_calls
        self.stats.runtime_history_reconstruction_attempts = self.history_reconstruction_attempts
        self.stats.runtime_history_reconstruction_key_computations = self.history_reconstruction_key_computations
        self.stats.runtime_history_witness_hits = self.history_witness_hits
        self.stats.runtime_history_witness_misses = self.history_witness_misses
        self.stats.runtime_opaque_history_child_external_key_computations = self.opaque_history_child_external_key_computations
        if hasattr(self.stats, "runtime_history_context_updates"):
            self.stats.runtime_history_context_updates = self._history_context_updates
            self.stats.runtime_history_context_exact_comparisons = self._history_context_exact_comparisons
            self.stats.runtime_tt_eligible = int(self.tt_eligible)
        if hasattr(self.stats, "native_legality_enabled"):
            self.stats.native_legality_enabled = int(
                self._legal_binding_provider is not None and self._legal_provider_active
            )
            self.stats.native_legality_calls = self.legal_provider_calls
            self.stats.native_legality_actions = self.legal_provider_actions
            self.stats.native_legality_seconds = self.legal_provider_seconds
            self.stats.native_legality_payload_seconds = self.legal_provider_payload_seconds
            self.stats.native_legality_decode_binding_seconds = self.legal_provider_decode_binding_seconds
            self.stats.native_legality_fallbacks = self.legal_provider_fallbacks
            self.stats.native_legality_operational_failures = self.legal_provider_operational_failures
        self.stats.runtime_root_imports = 1
        self.stats.runtime_peak_depth = self.peak_depth
        self.stats.runtime_depth_balanced = not self._frames and self.pushes == self.pops

    def _provider_checkpoint(self, checkpoint):
        """Wrap the search checkpoint so cancellation is never swallowed."""
        aborted = False

        def checked():
            nonlocal aborted
            try:
                if checkpoint is not None:
                    checkpoint()
            except BaseException:
                aborted = True
                raise

        return checked, lambda: aborted

    def _legal_actions_from_provider(self, checkpoint):
        """Validate a complete result, honoring optional per-state capability.

        A callable may expose supports_position(position, ply_count). False
        selects Core for this state without marking an operational failure or
        disabling the provider for other states. Omitted capability preserves
        the existing callable contract.
        """
        import time

        provider = self._legal_binding_provider
        checked, was_aborted = self._provider_checkpoint(checkpoint)
        started = time.perf_counter()
        try:
            checked()
            provider_owner = getattr(provider, "__self__", None) or provider
            supports_position = getattr(provider_owner, "supports_position", None)
            if supports_position is not None and not supports_position(self.position, self.ply_count):
                # A declared per-state capability miss is normal Core fallback,
                # not an operational failure or a permanent provider disable.
                self.legal_provider_fallbacks += 1
                self._sync_stats()
                return None
            raw = provider(self.position, self.ply_count, checked)
            checked()
            pairs = tuple(raw)
            actions = []
            bindings = {}
            for index, pair in enumerate(pairs):
                if index and index % 64 == 0:
                    checked()
                if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                    raise ValueError("legal binding provider returned a malformed pair")
                public, binding = pair
                if public in bindings:
                    raise ValueError("legal binding provider returned a duplicate action")
                if binding is None:
                    raise ValueError("legal binding provider returned an empty binding")
                actions.append(public)
                bindings[public] = binding
            checked()
        except BaseException as exc:
            if was_aborted() or not isinstance(exc, Exception):
                raise
            provider_owner = getattr(provider, "__self__", None) or provider
            if bool(getattr(provider_owner, "strict", False)):
                raise
            self.legal_provider_fallbacks += 1
            self.legal_provider_operational_failures += 1
            self._legal_provider_active = False
            self._sync_stats()
            return None

        self.legal_provider_calls += 1
        self.legal_provider_actions += len(actions)
        self.legal_provider_seconds += time.perf_counter() - started
        provider_owner = getattr(provider, "__self__", None) or provider
        metrics = getattr(provider_owner, "last_call_metrics", {}) or {}
        self.legal_provider_payload_seconds += float(metrics.get("payload_seconds", 0.0))
        self.legal_provider_decode_binding_seconds += float(
            metrics.get("decode_binding_seconds", 0.0)
        )
        self._sync_stats()
        return tuple(actions), bindings

    def legal_actions(self, checkpoint=None) -> tuple[Action, ...]:
        if self._legal_cache is not None:
            return self._legal_cache
        if self.terminal_status.status is not TerminalStatus.ONGOING:
            self._legal_cache = ()
            return self._legal_cache
        engine = semantic_engine_for(self.compiled)
        if engine is not None:
            if self._legal_provider_active and self._legal_binding_provider is not None:
                provided = self._legal_actions_from_provider(checkpoint)
                if provided is not None:
                    actions, bindings = provided
                    if _pass_action_is_legal(self.position, self.compiled, checkpoint):
                        actions = (*actions, PassAction())
                    self._bindings = bindings
                    self._legal_cache = actions
                    return self._legal_cache
            actions = []
            bindings = {}
            for semantic_action, binding in engine.iter_legal_action_bindings(
                    self.position, checkpoint=checkpoint, full_frontier=True
                ):
                public = _semantic_public_action(engine, semantic_action)
                actions.append(public)
                bindings[public] = (semantic_action, binding)
            if _pass_action_is_legal(self.position, self.compiled, checkpoint):
                actions.append(PassAction())
            self._bindings = bindings
        else:
            actions = list(iter_legal_actions_from_position(self.position, self.compiled, checkpoint=checkpoint))
            self._bindings = {}
        self._legal_cache = tuple(actions)
        return self._legal_cache

    def _gave_check(self, position, checkpoint=None):
        # Optional readonly state-local query. None declines to Core; required
        # errors propagate through push's existing exception-safe undo.
        if self._check_provider is not None:
            value = self._check_provider(
                position, position.side_to_move, checkpoint=checkpoint
            )
            if value is not None:
                if not isinstance(value, bool):
                    raise TypeError("check provider must return bool or None")
                return value
        engine = semantic_engine_for(self.compiled)
        return engine.in_check(position, position.side_to_move, checkpoint=checkpoint) if engine is not None else is_in_check(position, position.side_to_move, self.compiled)

    def in_check(self, owner: int, checkpoint=None) -> bool:
        """Query current check, reusing an already computed nonpass push result.

        Imported/root history is not a check oracle. A pass records no checking
        responsibility, so it also needs a fresh query. Frame identity ties the
        reusable answer to the exact current child and naturally restores it
        after pop; the other owner's check is always queried independently.
        """
        if self._frames and owner == self.position.side_to_move:
            frame = self._frames[-1]
            if frame.child_identity is self._identity and frame.child_in_check is not None:
                if checkpoint is not None:
                    checkpoint()
                return frame.child_in_check
        engine = semantic_engine_for(self.compiled)
        return (engine.in_check(self.position, owner, checkpoint=checkpoint)
                if engine is not None else is_in_check(self.position, owner, self.compiled))

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

    def _resolve_opaque_history_key(
        self,
        key: str,
        identity: RuntimePositionIdentity,
        runtime_hash: RuntimeHash,
    ) -> None:
        """Bind one opaque imported key to a verified exact child identity."""
        if key not in self._opaque_imported_keys:
            return
        old_identity = _ImportedIdentity(key)
        old_hash = self._runtime_hash_for_identity(old_identity)
        old_bucket, old_entry = self._find_occurrence(old_identity, old_hash, instrument=False)
        if old_entry is None:
            raise AssertionError("opaque imported occurrence is missing")
        # Resolve the removal index before target mutation: dataclass equality
        # in list.remove/index can itself fail while allocating comparison tuples.
        old_index = old_bucket.index(old_entry)
        # Prepare target storage before journaling/removing the opaque entry.
        # A single target-constructor failure leaves the original counts intact.
        new_bucket = self._occurrences.get(runtime_hash)
        new_entry = next(
            (candidate for candidate in new_bucket or ()
             if _identity_equal(candidate.identity, identity)), None)
        if new_entry is None:
            prepared_entry = _Occurrence(identity, old_entry.count)
            if new_bucket is None:
                self._occurrences[runtime_hash] = [prepared_entry]
            else:
                new_bucket.append(prepared_entry)
        else:
            new_entry.count += old_entry.count

        frame = self._frames[-1]
        frame.bridge_key = key
        frame.bridge_identity = identity
        frame.bridge_runtime_hash = runtime_hash
        frame.bridge_old_hash = old_hash
        frame.bridge_old_count = old_entry.count
        del old_bucket[old_index]
        if not old_bucket:
            self._occurrences.pop(old_hash, None)

        self._opaque_imported_keys.remove(key)
        self._history_aliases[key] = identity
        self._snapshot = self._snapshot_from_occurrences()

    def _restore_bridge(self, frame: _Frame) -> None:
        """Undo one imported-key bridge without copying the occurrence table."""
        key = frame.bridge_key
        if key is None:
            return
        identity = frame.bridge_identity
        runtime_hash = frame.bridge_runtime_hash
        if identity is None or runtime_hash is None or frame.bridge_old_hash is None:
            raise AssertionError("incomplete runtime history bridge frame")

        bucket = self._occurrences.get(runtime_hash)
        if bucket is None:
            raise AssertionError("runtime bridge target bucket is missing")
        entry = next(
            (candidate for candidate in bucket if _identity_equal(candidate.identity, identity)),
            None,
        )
        if entry is None:
            raise AssertionError("runtime bridge target occurrence is missing")
        entry.count -= frame.bridge_old_count
        if entry.count < 0:
            raise AssertionError("runtime bridge target occurrence underflow")
        if entry.count == 0:
            bucket.remove(entry)
        if not bucket:
            self._occurrences.pop(runtime_hash, None)

        self._opaque_imported_keys.add(key)
        self._history_aliases.pop(key, None)
        old_bucket = self._occurrences.setdefault(frame.bridge_old_hash, [])
        old_entry = next(
            (
                candidate
                for candidate in old_bucket
                if _identity_equal(candidate.identity, _ImportedIdentity(key))
            ),
            None,
        )
        if old_entry is None:
            old_bucket.append(_Occurrence(_ImportedIdentity(key), frame.bridge_old_count))
        else:
            old_entry.count += frame.bridge_old_count

    def _opaque_history_key_for_child(self, child: Position) -> str | None:
        if not self._opaque_imported_keys:
            return None
        self.opaque_history_child_external_key_computations += 1
        key = str(position_identity_key(child, self.compiled))
        return key if key in self._opaque_imported_keys else None

    def occurrence_count(self, identity: object | None = None, runtime_hash: RuntimeHash | None = None) -> int:
        identity = identity or self._identity
        runtime_hash = runtime_hash or self.runtime_hash
        _, entry = self._find_occurrence(identity, runtime_hash, instrument=False)
        return 0 if entry is None else entry.count

    def history_occurrences(self, identity: object) -> list[int]:
        return [
            index
            for index, record in enumerate(self._history)
            if _identity_equal(
                self._history_aliases.get(record.external_key, record.identity),
                identity,
            )
        ]

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
        rollback_frame = None
        try:
            return self._push_impl(action, checkpoint)
        except BaseException:
            if len(self._frames) > before_depth:
                rollback_frame = self._frames[before_depth]
            removed_history = 0
            while len(self._history) > before_history_len:
                record = self._history.pop()
                self._occurrence_remove(record.identity, record.runtime_hash or self.runtime_hash)
                removed_history += 1
            if (
                rollback_frame is not None
                and rollback_frame.child_occurrence_added
                and removed_history == 0
            ):
                # Snapshot construction can fail after adding the child but
                # before appending history, even without an imported-key bridge.
                self._occurrence_remove(
                    rollback_frame.child_identity,
                    rollback_frame.child_runtime_hash,
                )
            del self._frames[before_depth:]
            self.position = before_position
            self.ply_count = before_ply
            self.terminal_status = before_status
            self._identity = before_identity
            self.runtime_hash = before_hash
            self._snapshot = before_snapshot
            self._legal_cache = before_cache
            self._bindings = before_bindings
            if rollback_frame is not None:
                self._history_context = rollback_frame.history_context
                self._no_progress_context = rollback_frame.no_progress_context
                self._restore_bridge(rollback_frame)
            self._sync_stats()
            raise

    def _push_impl(self, action: Action, checkpoint=None) -> RuntimeSearchState:
        legal = self.legal_actions(checkpoint)
        # Semantic frontiers already own a complete validated binding map.
        # Keep tuple authority for pass/legacy and unhashable caller inputs.
        if self._bindings and not isinstance(action, PassAction):
            try:
                accepted = action in self._bindings
            except TypeError:
                accepted = action in legal
        else:
            accepted = action in legal
        if not accepted:
            raise IllegalActionError(f"action is not legal in the current state: {action}")
        self._frames.append(
            _Frame(
                self.position,
                self.ply_count,
                self.terminal_status,
                self._identity,
                self.runtime_hash,
                self._snapshot,
                self._legal_cache,
                self._bindings,
                history_context=self._history_context,
                no_progress_context=self._no_progress_context,
            )
        )
        parent = self.position
        engine = semantic_engine_for(self.compiled)
        if engine is not None:
            if isinstance(action, PassAction):
                child = _apply_action_unchecked(parent, action, self.compiled)
            else:
                semantic_action, binding = self._bindings[action]
                child = engine._transition(parent, semantic_action, binding, checkpoint=checkpoint)
        else:
            child = _apply_action_unchecked(parent, action, self.compiled)
        gave_check = (
            False if isinstance(action, PassAction) else self._gave_check(child, checkpoint)
        )
        self._frames[-1].child_in_check = (
            None if isinstance(action, PassAction) else gave_check
        )
        child_external_key = self._opaque_history_key_for_child(child)
        child_identity = _runtime_position_identity(child, self.compiled,
            cache_hash=self._cache_position_identity_hash)
        if self._forced_hash is not None:
            child_hash = self.runtime_hash
        elif engine is None:
            child_hash = _legacy_incremental_hash(parent, child, action, self.compiled, self.runtime_hash)
            self.legacy_incremental_updates += 1
        else:
            child_hash = (
                _plain_leaper_local_hash(parent, child, action, self.compiled,
                                        self.runtime_hash, self._plain_leaper_hash_patterns)
                if self._plain_leaper_hash_patterns is not None else None
            )
            if child_hash is None:
                child_hash = _semantic_component_diff_hash(parent, child, self.compiled, self.runtime_hash)
                self.semantic_full_diff_fallbacks += 1
            else:
                self.semantic_local_hash_updates += 1
        self.position = child
        self.ply_count += 1
        self._identity = child_identity
        frame = self._frames[-1]
        frame.child_identity = child_identity
        frame.child_runtime_hash = child_hash
        if child_external_key is not None:
            self._resolve_opaque_history_key(child_external_key, child_identity, child_hash)
        previous_count = self._occurrence_add(child_identity, child_hash)
        frame.child_occurrence_added = True
        self.snapshot_updates += 1
        self.snapshot_entry_digest_calls += int(bool(previous_count)) + 1
        self._snapshot = self._snapshot.updated(
            child_identity,
            previous_count + 1,
            previous_count,
            child_hash,
        )
        signature = json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))
        self._history.append(
            RuntimeHistoryRecord(
                child_identity,
                parent.side_to_move,
                signature,
                gave_check,
                child_hash,
                child_external_key,
            )
        )
        self._history_context = RuntimeHistoryContext.append(
            self._history_context,
            child_identity,
            child_hash,
            parent.side_to_move,
            gave_check,
            signature if self._history_action_sensitive else "",
        )
        self._history_context_updates += 1
        self.runtime_hash = child_hash
        self._legal_cache = None
        self._bindings = {}
        if self._no_progress_context is not None:
            from .no_progress_context import advance
            self._no_progress_context = advance(
                self._no_progress_context, parent, child, action,
                self.compiled.no_progress_draw, self.ply_count,
            )
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
        self._history_context = frame.history_context
        self._no_progress_context = frame.no_progress_context
        self._restore_bridge(frame)
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
    "RuntimeHistoryContext",
    "RuntimeSearchState",
    "RuntimeCountsSnapshot",
    "RuntimeSearchKey",
    "SearchPathRuntime",
    "_component_map",
    "_full_runtime_hash",
]
