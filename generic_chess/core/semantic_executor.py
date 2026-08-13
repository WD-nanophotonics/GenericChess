"""Python S0-S3 reference executor for the compiled semantic IR
(Phase 1.9B-2, Review R2).

This is the first executable reference implementation of the semantic IR:
it generates candidates from compiled geometry, applies target/path/state/
slot predicates, performs trial transitions with royal-safety invariants,
applies bounded effects with the aux lifecycle and transition triggers, and
produces terminal results through the public Core path.

Review R2 hardens the executor around one immutable pre-action binding
context (ADR-015): the runtime binding carries the exact ``geometry_id``,
every action-relative TypeRef/SquareRef/guard/effect consumes that context,
auxiliary physical keys are canonical ``(slot_id, owner_tag)`` tuples, and
pseudo-attack shares the exact S0+S1 eligibility semantics with attacker
perspective.

It never reads the high-level ``RuleSet``, ``PieceType.movement_atoms``,
debug names, or ``_legacy_compiled``.  S4 ``no_legal_reply`` patterns are
fail-closed (never generated).  Native/Search/Learner are untouched.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from math import gcd

from ..rules.ir import (
    CompiledSemanticRuleset,
    geometry_candidates,
)
from .coordinates import Square, index_to_square, square_to_index
from .errors import RuleSetMismatchError
from .pieces import Piece
from .position import Hands, Position


GLOBAL_OWNER_TAG = -1
Checkpoint = Callable[[], None]


def _checkpoint(checkpoint: Checkpoint | None) -> None:
    """Run a caller-owned cooperative checkpoint without knowing its policy."""
    if checkpoint is not None:
        checkpoint()


@dataclass(frozen=True, slots=True)
class SemanticAction:
    """Runtime action binding for the semantic executor.

    ``pattern_id`` distinguishes otherwise identical source/target actions
    coming from different semantic patterns; ``geometry_id`` pins the exact
    compiled geometry so execution never rescan geometries (R2-02).
    """

    pattern_id: str
    source: int | None  # None for drops
    target: int
    promotion_target_id: str | None = None
    actor_type: str | None = None  # exact actor/drop type (never type_ids[0])
    geometry_id: str | None = None


@dataclass(frozen=True, slots=True)
class _ActionBinding:
    """Immutable pre-action binding context (ADR-015 section 3).

    Built once per candidate from the pre-action position; consumed by every
    TypeRef/SquareRef resolution, S1 guard, effect and invariant check.
    ACTION_BASE/ACTION_CURRENT always mean the pre-action actor.
    """

    pattern: object
    geometry_id: str
    actor_owner: int
    actor_type: str
    actor_base: str
    actor_current: str
    source: int | None
    target: int
    promotion_target_id: str | None
    path: tuple[int, ...]


def _own_anchor(position: Position, support, side: int) -> int | None:
    n = support.board_size
    for idx, piece in enumerate(position.board):
        if piece is not None and piece.owner == side:
            meta = support.type_metadata.get(piece.current_type_id)
            if meta is not None and meta.is_anchor:
                return idx
    return None


def _sources_by_owner_type(position: Position) -> dict[tuple[int, str], tuple[tuple[int, Piece], ...]]:
    """Return a position-local source index in board order.

    Semantic candidate and pseudo-attack dispatch both need the same
    owner/current-type filtering.  Building this immutable-by-convention local
    view once per operation removes repeated full-board scans without changing
    Position identity, public ordering, or any ruleset authority.
    """
    indexed: dict[tuple[int, str], list[tuple[int, Piece]]] = {}
    for source, piece in enumerate(position.board):
        if piece is not None:
            indexed.setdefault((piece.owner, piece.current_type_id), []).append(
                (source, piece)
            )
    return {key: tuple(value) for key, value in indexed.items()}


def is_semantic_compiled(compiled) -> bool:
    from ..rules.ir import CompiledSemanticRuleset

    return isinstance(compiled, CompiledSemanticRuleset)


def semantic_engine_for(compiled):
    if not is_semantic_compiled(compiled):
        return None
    return SemanticEngine(compiled)


def _semantic_public_action(engine, action: SemanticAction):
    """Project one runtime binding to a lossless public semantic action."""
    from .actions import SemanticBoardMove, SemanticDropMove

    if action.source is None:
        if action.geometry_id is None or action.actor_type is None:
            raise RuntimeError(
                f"semantic drop binding missing identity for {action.pattern_id}"
            )
        return SemanticDropMove(
            pattern_id=action.pattern_id,
            geometry_id=action.geometry_id,
            base_type_id=action.actor_type,
            to_square=index_to_square(action.target, engine.support.board_size),
        )
    if action.geometry_id is None or action.actor_type is None:
        raise RuntimeError(
            f"semantic board binding missing identity for {action.pattern_id}"
        )
    return SemanticBoardMove(
        pattern_id=action.pattern_id,
        geometry_id=action.geometry_id,
        actor_type_id=action.actor_type,
        from_square=index_to_square(action.source, engine.support.board_size),
        to_square=index_to_square(action.target, engine.support.board_size),
        promotion_target_id=action.promotion_target_id,
    )


def iter_semantic_public_actions(
    engine, position: Position, checkpoint: Checkpoint | None = None
) -> Iterator:
    """Map semantic bindings to lossless public Core Action objects
    (R2-01: pattern/geometry identity survives projection)."""
    for action in engine.iter_legal_actions(position, checkpoint=checkpoint):
        _checkpoint(checkpoint)
        yield _semantic_public_action(engine, action)


def semantic_public_actions(
    engine, position: Position, checkpoint: Checkpoint | None = None
) -> tuple:
    return tuple(iter_semantic_public_actions(engine, position, checkpoint))


def semantic_action_for(engine, position: Position, action):
    """Resolve the unique semantic binding for a public Action (membership
    validated by the caller against the legal set).

    Semantic action variants match on exact pattern/geometry/actor identity.
    Legacy ``BoardMove``/``DropMove`` are accepted only when the visible
    coordinates identify exactly one binding; ambiguity fails closed instead
    of silently picking ``candidates[0]``.
    """
    from .actions import (
        BoardMove,
        DropMove,
        SemanticBoardMove,
        SemanticDropMove,
    )
    from .coordinates import index_to_square
    from .errors import IllegalActionError

    candidates = []
    for candidate in engine.iter_legal_actions(position):
        if isinstance(action, SemanticBoardMove):
            from_sq = (
                index_to_square(candidate.source, engine.support.board_size)
                if candidate.source is not None
                else None
            )
            to_sq = index_to_square(candidate.target, engine.support.board_size)
            if (
                candidate.source is not None
                and candidate.pattern_id == action.pattern_id
                and candidate.geometry_id == action.geometry_id
                and candidate.actor_type == action.actor_type_id
                and from_sq == action.from_square
                and to_sq == action.to_square
                and candidate.promotion_target_id == action.promotion_target_id
            ):
                candidates.append(candidate)
        elif isinstance(action, SemanticDropMove):
            to_sq = index_to_square(candidate.target, engine.support.board_size)
            if (
                candidate.source is None
                and candidate.pattern_id == action.pattern_id
                and candidate.geometry_id == action.geometry_id
                and candidate.actor_type == action.base_type_id
                and to_sq == action.to_square
            ):
                candidates.append(candidate)
        elif isinstance(action, BoardMove):
            from_sq = (
                index_to_square(candidate.source, engine.support.board_size)
                if candidate.source is not None
                else None
            )
            to_sq = index_to_square(candidate.target, engine.support.board_size)
            if (
                candidate.source is not None
                and from_sq == action.from_square
                and to_sq == action.to_square
                and candidate.promotion_target_id == action.promotion_target_id
            ):
                candidates.append(candidate)
        elif isinstance(action, DropMove):
            to_sq = index_to_square(candidate.target, engine.support.board_size)
            if (
                candidate.source is None
                and candidate.actor_type == action.base_type_id
                and to_sq == action.to_square
            ):
                candidates.append(candidate)
    if not candidates:
        raise IllegalActionError(
            f"action is not a legal semantic action in the current state: {action}"
        )
    if len(candidates) > 1:
        raise IllegalActionError(
            f"legacy action {action} is ambiguous across semantic bindings; "
            "use the semantic action variant"
        )
    return candidates[0]


def _aux_slot_by_id(aux_slots, slot_id):
    for slot in aux_slots:
        if slot.slot_id == slot_id:
            return slot
    return None


def _logical_owners(slot) -> tuple[int, ...]:
    """Canonical owner tags for one compiled slot (ADR-015 section 4)."""
    return (GLOBAL_OWNER_TAG,) if slot.scope == "global" else (0, 1)


def _aux_value(aux_state, slot, owner):
    """Logical value of one slot instance: explicit entry or slot.initial."""
    key = (slot.slot_id, owner)
    for k, v in aux_state:
        if k == key:
            return v
    return slot.initial


def _resolve_square_ref(ref, support, aux_slots, position, side, binding):
    """Resolve a compiled square ref to an absolute square index.

    ``side`` is the perspective owner (the actor for legal generation, the
    attacker for pseudo-attack, or the logical slot owner for triggers).
    ``position`` must be the pre-action position whenever an
    ``aux_slot_square`` ref may be resolved.
    """
    n = support.board_size
    kind = ref.kind
    source = binding.source
    target = binding.target
    path = binding.path
    if kind == "source":
        return source
    if kind == "target":
        return target
    if kind == "fixed":
        f, r = ref.square
        if ref.owner_relative and side == 1:
            f, r = n - 1 - f, n - 1 - r
        return r * n + f
    if kind in ("offset_from_source", "offset_from_target"):
        base = source if kind == "offset_from_source" else target
        df, dr = ref.offset
        if ref.owner_relative and side == 1:
            df, dr = -df, -dr
        base_sq = index_to_square(base, n)
        f, r = base_sq.file + df, base_sq.rank + dr
        if not (0 <= f < n and 0 <= r < n):
            return None
        return r * n + f
    if kind == "path_step":
        if ref.step is None or ref.step >= len(path):
            return None
        return path[ref.step]
    if kind == "aux_slot_square":
        if position is None or ref.slot_id is None:
            return None
        slot = _aux_slot_by_id(aux_slots, ref.slot_id)
        if slot is None:
            return None
        owner = side if slot.scope == "per_owner" else GLOBAL_OWNER_TAG
        value = _aux_value(position.aux_state, slot, owner)
        if value is None or not isinstance(value, tuple):
            return None
        return value[1] * n + value[0]
    return None


def _resolve_type_id(ref, binding) -> str | None:
    if ref is None or binding is None:
        return None
    if ref.kind == "action_base":
        return binding.actor_base
    if ref.kind == "action_current":
        return binding.actor_current
    if ref.kind == "explicit":
        return ref.type_id
    return None


class _WorkingPosition:
    """Mutable working copy for trial transitions."""

    def __init__(self, position: Position, support) -> None:
        self.n = support.board_size
        self.board = list(position.board)
        self.hands = [
            dict(position.hands[0].counts),
            dict(position.hands[1].counts),
        ]
        self.side = position.side_to_move
        self.events: list[tuple[str, object, int]] = []  # (event, piece, square)

    def piece_at(self, idx: int) -> Piece | None:
        return self.board[idx]

    def set_piece(self, idx: int, piece: Piece | None) -> None:
        self.board[idx] = piece

    def to_position(self, aux_state, fingerprint: str) -> Position:
        return Position(
            board=tuple(self.board),
            hands=(
                Hands(tuple(sorted(self.hands[0].items()))),
                Hands(tuple(sorted(self.hands[1].items()))),
            ),
            side_to_move=self.side,
            ruleset_fingerprint=fingerprint,
            aux_state=aux_state,
        )


def _apply_effect(effect, work, support, aux_slots, pre_position, binding) -> None:
    """Apply one board/hand/type effect with explicit occupancy and
    owner/type binding contracts (R2-12/R2-13)."""
    pattern_id = binding.pattern.pattern_id
    side = binding.actor_owner
    kind = effect.kind
    if kind in ("move", "shift"):
        from_idx = _resolve_square_ref(
            effect.from_ref, support, aux_slots, pre_position, side, binding
        )
        to_idx = _resolve_square_ref(
            effect.to_ref, support, aux_slots, pre_position, side, binding
        )
        if from_idx is None or to_idx is None:
            raise RuntimeError(f"{kind} refs unresolved for {pattern_id}")
        piece = work.piece_at(from_idx)
        if piece is None:
            raise RuntimeError(f"{kind} with no piece at source for {pattern_id}")
        if effect.piece_type_ref is not None:
            want = _resolve_type_id(effect.piece_type_ref, binding)
            if (
                want is not None
                and piece.base_type_id != want
                and piece.current_type_id != want
            ):
                raise RuntimeError(f"{kind} piece type mismatch for {pattern_id}")
        if effect.piece_owner != "any" and (
            (effect.piece_owner == "self" and piece.owner != side)
            or (effect.piece_owner == "opponent" and piece.owner == side)
        ):
            raise RuntimeError(f"{kind} piece owner mismatch for {pattern_id}")
        if work.piece_at(to_idx) is not None:
            raise RuntimeError(
                f"{kind} destination is occupied; capture/removal must be an "
                f"explicit earlier effect ({pattern_id})"
            )
        work.set_piece(from_idx, None)
        work.set_piece(to_idx, piece)
        work.events.append(("piece_leaves_square", piece, from_idx))
        return
    if kind == "remove":
        idx = _resolve_square_ref(
            effect.square_ref, support, aux_slots, pre_position, side, binding
        )
        if idx is None:
            raise RuntimeError(f"remove ref unresolved for {pattern_id}")
        captured = work.piece_at(idx)
        if captured is None:
            raise RuntimeError(f"remove requires a real victim for {pattern_id}")
        meta = support.type_metadata.get(captured.current_type_id)
        if meta is not None and meta.is_anchor:
            raise RuntimeError(f"anchor capture rejected for {pattern_id}")
        if effect.piece_type_ref is not None:
            want = _resolve_type_id(effect.piece_type_ref, binding)
            if (
                want is not None
                and captured.base_type_id != want
                and captured.current_type_id != want
            ):
                raise RuntimeError(f"remove victim type mismatch for {pattern_id}")
        if effect.piece_owner != "any" and (
            (effect.piece_owner == "self" and captured.owner != side)
            or (effect.piece_owner == "opponent" and captured.owner == side)
        ):
            raise RuntimeError(f"remove victim owner mismatch for {pattern_id}")
        if effect.disposition == "capture_to_hand":
            hand = work.hands[side]
            hand[captured.base_type_id] = hand.get(captured.base_type_id, 0) + 1
        work.set_piece(idx, None)
        work.events.append(("piece_removed_from_square", captured, idx))
        return
    if kind == "remove_from_hand":
        type_id = _resolve_type_id(effect.piece_type_ref, binding)
        if type_id is None:
            raise RuntimeError(f"remove_from_hand without type for {pattern_id}")
        hand = work.hands[side]
        if hand.get(type_id, 0) < effect.count:
            raise RuntimeError(f"remove_from_hand insufficient hand for {pattern_id}")
        hand[type_id] -= effect.count
        if hand[type_id] == 0:
            del hand[type_id]
        return
    if kind == "place":
        idx = _resolve_square_ref(
            effect.to_ref, support, aux_slots, pre_position, side, binding
        )
        type_id = _resolve_type_id(effect.piece_type_ref, binding)
        if idx is None or type_id is None:
            raise RuntimeError(f"place operands unresolved for {pattern_id}")
        if work.piece_at(idx) is not None:
            raise RuntimeError(f"place destination is occupied for {pattern_id}")
        work.set_piece(idx, Piece(owner=side, base_type_id=type_id, current_type_id=type_id))
        return
    if kind == "set_current_type":
        idx = _resolve_square_ref(
            effect.square_ref, support, aux_slots, pre_position, side, binding
        )
        type_id = _resolve_type_id(effect.type_ref, binding)
        if idx is None or type_id is None:
            raise RuntimeError(f"set_current_type operands unresolved for {pattern_id}")
        piece = work.piece_at(idx)
        if piece is None:
            raise RuntimeError(f"set_current_type with no piece for {pattern_id}")
        work.set_piece(
            idx,
            Piece(
                owner=piece.owner,
                base_type_id=piece.base_type_id,
                current_type_id=type_id,
                promoted=type_id != piece.base_type_id,
            ),
        )
        return
    # Aux slot effects are applied by the caller (they need the aux state).
    if kind in ("set_bool", "clear_right", "set_token", "clear_token"):
        return
    raise RuntimeError(f"unsupported effect kind {kind} for {pattern_id}")


def _apply_aux_effect(effect, aux, support, aux_slots, pre_position, binding) -> None:
    kind = effect.kind
    slot = _aux_slot_by_id(aux_slots, effect.slot_id)
    if slot is None:
        raise RuntimeError(f"aux effect references undeclared slot {effect.slot_id}")
    owner_tag = (
        GLOBAL_OWNER_TAG if slot.scope == "global" else binding.actor_owner
    )
    key = (effect.slot_id, owner_tag)
    if kind == "set_bool":
        aux[key] = effect.value
        return
    if kind == "clear_right":
        aux[key] = 0
        return
    if kind == "set_token":
        idx = _resolve_square_ref(
            effect.square_ref, support, aux_slots, pre_position, binding.actor_owner, binding
        )
        if idx is None:
            raise RuntimeError("set_token ref unresolved")
        sq = index_to_square(idx, support.board_size)
        aux[key] = (sq.file, sq.rank)
        return
    if kind == "clear_token":
        aux[key] = None
        return


class SemanticEngine:
    """S0-S4 executor for one compiled semantic ruleset.

    Phase 1.9B-3 adds the bounded post-action probe (ADR-016): a candidate
    passes through the single S0-S3 trial machinery and, in normal legality,
    is then filtered by its S4 postconditions (one forbidden conjunction,
    cheap-first).  The reply probe reuses the exact same S0-S3 machinery
    with S4 disabled, early-exits on the first valid reply, and never enters
    S5."""

    def __init__(self, semantic: CompiledSemanticRuleset) -> None:
        if semantic.support is None:
            raise RuntimeError("semantic ruleset missing support payload")
        if not semantic.ir.capabilities.new_ir_core_executable:
            raise RuntimeError(
                "semantic ruleset is not executable by the B-2 reference "
                "executor: S4/postcondition or unsupported primitive "
                "combination (fail-closed)"
            )
        self.semantic = semantic
        self.ir = semantic.ir
        self.support = semantic.support
        # All patterns participate in S0-S3 legality and pseudo-attack; S4
        # postconditions are a per-candidate filter, never a reason to omit
        # a pattern's S0-S3 projection (B-3 audit requirement).
        self._patterns = self.ir.patterns

    # ------------------------------------------------------- identity

    def _ensure_match(self, position: Position) -> None:
        if position.ruleset_fingerprint != self.support.ruleset_fingerprint:
            raise RuleSetMismatchError(
                f"position fingerprint {position.ruleset_fingerprint!r} does not "
                f"match semantic ruleset fingerprint "
                f"{self.support.ruleset_fingerprint!r}"
            )

    # ------------------------------------------------------- aux scope

    def _slot_scope(self, slot_id: int) -> str:
        slot = _aux_slot_by_id(self.ir.aux_slots, slot_id)
        return slot.scope if slot is not None else "global"

    def _slot_value(self, position: Position, slot_id: int, owner: int):
        slot = _aux_slot_by_id(self.ir.aux_slots, slot_id)
        if slot is None:
            return None
        logical_owner = GLOBAL_OWNER_TAG if slot.scope == "global" else owner
        return _aux_value(position.aux_state, slot, logical_owner)

    # ------------------------------------------------------- resolution

    def _initial_position(self) -> Position:
        rows = self.support.initial_position
        n = self.support.board_size
        board = tuple(rows[r][f] for r in range(n) for f in range(n))
        return Position(
            board=board,
            hands=(Hands.empty(), Hands.empty()),
            side_to_move=0,
            ruleset_fingerprint=self.support.ruleset_fingerprint,
            aux_state=(),
        )

    # ------------------------------------------------------- pseudo attack

    def is_square_attacked(
        self,
        position: Position,
        square: int,
        by_owner: int,
        checkpoint: Checkpoint | None = None,
    ) -> bool:
        """Semantic pseudo-attack (R2-09/R2-10): exact type/geometry
        compatibility, path predicates, state guards and slot guards with
        attacker-relative SELF/OPPONENT.  No full legal recursion and no S3
        own-anchor safety, matching the legacy attacked-square distinction.

        B-3: S4-bearing capture patterns still contribute their S0/S1
        capture eligibility to pseudo-attack; S4 postconditions are never
        consulted here."""
        self._ensure_match(position)
        sources_by_owner_type = _sources_by_owner_type(position)
        for pattern in self._patterns:
            _checkpoint(checkpoint)
            if pattern.target.kind != "target_enemy":
                continue  # attack eligibility = capture eligibility
            for tid in pattern.type_ids:
                _checkpoint(checkpoint)
                for source, piece in sources_by_owner_type.get((by_owner, tid), ()):
                    _checkpoint(checkpoint)
                    for gid in pattern.geometry_ids:
                        _checkpoint(checkpoint)
                        geometry = self.ir.geometry.get(gid)
                        if geometry is None or geometry.kind == "drop":
                            continue
                        if (
                            geometry.atom_source is not None
                            and geometry.atom_source[0] != tid
                        ):
                            continue
                        for target, path in geometry_candidates(
                            geometry, str(by_owner), source
                        ):
                            _checkpoint(checkpoint)
                            if target != square:
                                continue
                            binding = self._make_binding(
                                pattern, gid, tid, piece,
                                source, square, None, path, position,
                            )
                            if self._path_holds(
                                pattern.path, position, binding, by_owner,
                                checkpoint=checkpoint,
                            ) and self._guards_hold(
                                pattern, position, binding, by_owner,
                                checkpoint=checkpoint,
                            ):
                                return True
        return False

    def in_check(
        self, position: Position, side: int, checkpoint: Checkpoint | None = None
    ) -> bool:
        anchor = _own_anchor(position, self.support, side)
        if anchor is None:
            return False
        return self.is_square_attacked(
            position, anchor, 1 - side, checkpoint=checkpoint
        )

    # ------------------------------------------------------- binding

    def _make_binding(
        self,
        pattern,
        gid: str,
        tid: str,
        piece: Piece | None,
        source: int | None,
        target: int,
        promotion_target_id: str | None,
        path,
        position: Position | None,
    ) -> _ActionBinding:
        if piece is not None:
            actor_owner = piece.owner
            actor_base = piece.base_type_id
            actor_current = piece.current_type_id
        else:
            actor_owner = position.side_to_move if position is not None else 0
            actor_base = tid
            actor_current = tid
        return _ActionBinding(
            pattern=pattern,
            geometry_id=gid,
            actor_owner=actor_owner,
            actor_type=tid,
            actor_base=actor_base,
            actor_current=actor_current,
            source=source,
            target=target,
            promotion_target_id=promotion_target_id,
            path=tuple(path),
        )

    def _make_binding_from_action(
        self, position: Position, action: SemanticAction, pattern
    ) -> _ActionBinding:
        """Rebuild the exact pre-action binding from a runtime action.

        The runtime action is the sole source of geometry identity: no
        geometry re-inference or first-match fallback is allowed (R3-02).
        Every contract violation fails closed with ``IllegalActionError``.
        """
        from .errors import IllegalActionError

        side = position.side_to_move
        if action.source is not None:
            if action.geometry_id is None:
                raise IllegalActionError(
                    f"semantic board binding missing geometry_id for "
                    f"{action.pattern_id}"
                )
            if action.actor_type is None:
                raise IllegalActionError(
                    f"semantic board binding missing actor_type for "
                    f"{action.pattern_id}"
                )
            geometry = self.ir.geometry.get(action.geometry_id)
            if geometry is None:
                raise IllegalActionError(
                    f"semantic board binding references unknown geometry "
                    f"{action.geometry_id!r} for {action.pattern_id}"
                )
            if action.geometry_id not in pattern.geometry_ids:
                raise IllegalActionError(
                    f"geometry {action.geometry_id!r} does not belong to "
                    f"pattern {action.pattern_id}"
                )
            if geometry.kind == "drop":
                raise IllegalActionError(
                    f"drop geometry {action.geometry_id!r} used for a board "
                    f"binding ({action.pattern_id})"
                )
            if (
                geometry.atom_source is not None
                and geometry.atom_source[0] != action.actor_type
            ):
                raise IllegalActionError(
                    f"geometry {action.geometry_id!r} is incompatible with "
                    f"actor type {action.actor_type!r} ({action.pattern_id})"
                )
            piece = position.board[action.source]
            if piece is None:
                raise IllegalActionError(
                    f"binding source has no piece for {action.pattern_id}"
                )
            if piece.current_type_id != action.actor_type:
                raise IllegalActionError(
                    f"actor type {action.actor_type!r} does not match piece "
                    f"current type {piece.current_type_id!r} at source "
                    f"{action.source} ({action.pattern_id})"
                )
            exact = self._path_for_geometry(
                action.geometry_id, action.source, action.target, side
            )
            if exact is None:
                raise IllegalActionError(
                    f"geometry {action.geometry_id!r} does not reach target "
                    f"{action.target} from source {action.source} "
                    f"({action.pattern_id})"
                )
            path = exact
            return self._make_binding(
                pattern, action.geometry_id, piece.current_type_id, piece,
                action.source, action.target, action.promotion_target_id, path, position,
            )
        if action.actor_type is None:
            raise IllegalActionError(
                f"drop binding without actor type for {action.pattern_id}"
            )
        if action.geometry_id is None:
            raise IllegalActionError(
                f"semantic drop binding missing geometry_id for {action.pattern_id}"
            )
        geometry = self.ir.geometry.get(action.geometry_id)
        if geometry is None:
            raise IllegalActionError(
                f"semantic drop binding references unknown geometry "
                f"{action.geometry_id!r} for {action.pattern_id}"
            )
        if action.geometry_id not in pattern.geometry_ids:
            raise IllegalActionError(
                f"geometry {action.geometry_id!r} does not belong to pattern "
                f"{action.pattern_id}"
            )
        if geometry.kind != "drop":
            raise IllegalActionError(
                f"board geometry {action.geometry_id!r} used for a drop "
                f"binding ({action.pattern_id})"
            )
        return self._make_binding(
            pattern, action.geometry_id, action.actor_type, None, None,
            action.target, None, (), position,
        )

    def _path_for_geometry(self, gid, source, target, side):
        geometry = self.ir.geometry.get(gid)
        if geometry is None or geometry.kind == "drop":
            return None
        for candidate_target, candidate_path in geometry_candidates(
            geometry, str(side), source
        ):
            if candidate_target == target:
                return candidate_path
        return None

    # ------------------------------------------------------- predicates

    def _owner_filter_ok(self, owner_filter: str, owner: int, perspective: int) -> bool:
        if owner_filter == "any":
            return True
        if owner_filter == "self":
            return owner == perspective
        return owner != perspective

    def _path_holds(
        self, predicates, position, binding, perspective,
        checkpoint: Checkpoint | None = None,
    ) -> bool:
        path = binding.path
        for predicate in predicates:
            _checkpoint(checkpoint)
            kind = predicate.kind
            if kind == "path_clear":
                if any(position.board[i] is not None for i in path):
                    return False
            elif kind == "path_count_eq":
                count = sum(1 for i in path if position.board[i] is not None)
                if count != predicate.count:
                    return False
            elif kind == "path_count_range":
                count = sum(1 for i in path if position.board[i] is not None)
                if not (predicate.lo <= count <= predicate.hi):
                    return False
            elif kind == "path_first_blocker_owner":
                for i in path:
                    piece = position.board[i]
                    if piece is None:
                        continue
                    if not self._owner_filter_ok(
                        predicate.owner_filter, piece.owner, perspective
                    ):
                        return False
                    break
            elif kind == "path_last_blocker_owner":
                blockers = [i for i in path if position.board[i] is not None]
                if blockers:
                    piece = position.board[blockers[-1]]
                    if not self._owner_filter_ok(
                        predicate.owner_filter, piece.owner, perspective
                    ):
                        return False
        return True

    def _target_holds(self, kind: str, position: Position, target: int, perspective: int) -> bool:
        piece = position.board[target]
        if kind == "target_empty":
            return piece is None
        if kind == "target_enemy":
            return piece is not None and piece.owner != perspective
        if kind == "target_friendly":
            return piece is not None and piece.owner == perspective
        return True  # target_any

    def _guard_holds(
        self, guard, position: Position, binding, perspective,
        checkpoint: Checkpoint | None = None,
    ) -> bool:
        sel = guard.spatial
        bound_base = binding.actor_base
        bound_current = binding.actor_current
        count = 0
        for idx, piece in enumerate(position.board):
            _checkpoint(checkpoint)
            if piece is None:
                continue
            if not self._owner_filter_ok(guard.owner, piece.owner, perspective):
                continue
            if guard.location == "hand":
                continue  # hand predicates are rejected at compile time
            if not self._type_selector_ok(guard, piece, bound_base, bound_current):
                continue
            promoted_ok = (
                guard.promoted == "any"
                or (guard.promoted == "yes") == piece.promoted
            )
            if not promoted_ok:
                continue
            if self._spatial_ok(
                sel, idx, position, binding, perspective, checkpoint=checkpoint
            ):
                count += 1
        if guard.aggregation == "exists":
            value = 1 if count > 0 else 0
        else:
            value = count
        return self._compare(guard.comparison, value, guard.value)

    def _type_selector_ok(self, guard, piece, bound_base, bound_current) -> bool:
        ref = guard.type_ref
        if ref.kind == "any":
            return True
        want = (
            bound_current
            if ref.kind == "action_current"
            else bound_base
            if ref.kind == "action_base"
            else ref.type_id
        )
        if want is None:
            return False
        field = piece.current_type_id if guard.compare_field == "current" else piece.base_type_id
        return field == want

    def _spatial_ok(
        self, sel, idx, position, binding, perspective,
        checkpoint: Checkpoint | None = None,
    ) -> bool:
        n = self.support.board_size
        sq = index_to_square(idx, n)
        if sel.kind == "same_file":
            ref_sq = self._ref_square(sel.refs[0], position, binding, perspective)
            return ref_sq is not None and ref_sq.file == sq.file
        if sel.kind == "same_rank":
            ref_sq = self._ref_square(sel.refs[0], position, binding, perspective)
            return ref_sq is not None and ref_sq.rank == sq.rank
        if sel.kind == "exact":
            ref_sq = self._ref_square(sel.refs[0], position, binding, perspective)
            return ref_sq is not None and ref_sq == sq
        if sel.kind == "adjacent":
            ref_sq = self._ref_square(sel.refs[0], position, binding, perspective)
            return (
                ref_sq is not None
                and max(abs(ref_sq.file - sq.file), abs(ref_sq.rank - sq.rank)) == 1
            )
        if sel.kind == "path_between":
            a = self._ref_square(sel.refs[0], position, binding, perspective)
            b = self._ref_square(sel.refs[1], position, binding, perspective)
            if a is None or b is None:
                return False
            df = b.file - a.file
            dr = b.rank - a.rank
            g = gcd(abs(df), abs(dr))
            if g <= 1:
                return False
            step_f, step_r = df // g, dr // g
            for k in range(1, g):
                _checkpoint(checkpoint)
                if sq.file == a.file + k * step_f and sq.rank == a.rank + k * step_r:
                    return True
            return False
        if sel.kind == "zone":
            zone = self.ir.zones.get(sel.zone_id)
            return zone is not None and idx in zone.squares
        return False

    def _ref_square(self, ref, position, binding, perspective) -> Square | None:
        idx = _resolve_square_ref(
            ref, self.support, self.ir.aux_slots, position, perspective, binding
        )
        return index_to_square(idx, self.support.board_size) if idx is not None else None

    def _compare(self, op: str, a, b) -> bool:
        if op == "eq":
            return a == b
        if op == "ne":
            return a != b
        if op == "lt":
            return a < b
        if op == "le":
            return a <= b
        if op == "gt":
            return a > b
        if op == "ge":
            return a >= b
        return False

    def _slot_guard_holds(self, guard, position: Position, binding, perspective) -> bool:
        value = self._slot_value(position, guard.slot_id, perspective)
        if guard.square_ref is not None:
            idx = _resolve_square_ref(
                guard.square_ref, self.support, self.ir.aux_slots,
                position, perspective, binding,
            )
            square = (
                index_to_square(idx, self.support.board_size)
                if idx is not None
                else None
            )
            if guard.comparison == "eq":
                return value == (square.file, square.rank) if square is not None else value is None
            if guard.comparison == "ne":
                return value != (square.file, square.rank) if square is not None else value is not None
            return False
        return self._compare(guard.comparison, value, guard.value)

    # ------------------------------------------------------- legality

    def _iter_candidates(
        self, pattern, position: Position, checkpoint: Checkpoint | None = None
    ):
        """Yield ``(SemanticAction, _ActionBinding)`` for every S0-S1
        eligible candidate of one pattern (geometry, target, path, guards,
        promotion variants).  S3 trial and S4 postconditions are applied by
        callers, so this is the single candidate oracle shared by normal
        legality and the reply probe (B-3: one S0-S3 machinery)."""
        side = position.side_to_move
        _checkpoint(checkpoint)
        is_drop = any(
            self.ir.geometry[g].kind == "drop"
            for g in pattern.geometry_ids
            if g in self.ir.geometry
        )
        if is_drop:
            yield from self._iter_drop_candidates(
                pattern, position, side, checkpoint=checkpoint
            )
        else:
            yield from self._iter_board_candidates(
                pattern, position, checkpoint=checkpoint
            )

    def _iter_board_candidates(
        self, pattern, position: Position, checkpoint: Checkpoint | None = None
    ):
        side = position.side_to_move
        sources_by_owner_type = _sources_by_owner_type(position)
        for tid in pattern.type_ids:
            _checkpoint(checkpoint)
            for source, piece in sources_by_owner_type.get((side, tid), ()):
                _checkpoint(checkpoint)
                for gid in pattern.geometry_ids:
                    _checkpoint(checkpoint)
                    geometry = self.ir.geometry.get(gid)
                    if geometry is None or geometry.kind == "drop":
                        continue
                    if (
                        geometry.atom_source is not None
                        and geometry.atom_source[0] != tid
                    ):
                        continue
                    for target, path in geometry_candidates(geometry, str(side), source):
                        _checkpoint(checkpoint)
                        if not self._target_holds(pattern.target.kind, position, target, side):
                            continue
                        promotions = self._promotion_choices(pattern, piece, source, target)
                        for promotion_target in promotions:
                            _checkpoint(checkpoint)
                            binding = self._make_binding(
                                pattern, gid, tid, piece, source, target,
                                promotion_target, path, position,
                            )
                            if not self._path_holds(
                                pattern.path, position, binding, side,
                                checkpoint=checkpoint,
                            ):
                                continue
                            if not self._guards_hold(
                                pattern, position, binding, side,
                                checkpoint=checkpoint,
                            ):
                                continue
                            action = SemanticAction(
                                pattern_id=pattern.pattern_id,
                                source=source,
                                target=target,
                                promotion_target_id=promotion_target,
                                actor_type=tid,
                                geometry_id=gid,
                            )
                            yield action, binding

    def _promotion_choices(self, pattern, piece, source, target) -> tuple[str | None, ...]:
        if pattern.promotion_mode == "none":
            return (None,)
        if pattern.promotion_mode == "explicit":
            return (pattern.explicit_promotion_type,)
        # Promotion is a one-way transition from an unpromoted base piece.
        # A promoted piece may use the same movement geometry, but it must
        # never receive another promotion variant merely because its base
        # type has compiled promotion masks.
        if piece.promoted:
            return (None,)
        # inherit_compiled_masks
        base = piece.base_type_id
        allowed = self.support.promotion_allowed.get(base, ((), ()))
        forced = self.support.promotion_forced.get(base, (frozenset(), frozenset()))
        side = piece.owner
        from_sq = index_to_square(source, self.support.board_size)
        to_sq = index_to_square(target, self.support.board_size)
        meta = self.support.type_metadata.get(base)
        if meta is None or not meta.is_promotable:
            return (None,)
        if (from_sq, to_sq) not in allowed[side]:
            return (None,)
        n = self.support.board_size
        alive = [
            t
            for t in meta.promotion_target_ids
            if self.support.empty_mobility.get(t, ((), ()))[side][target]
        ]
        if to_sq in forced[side]:
            return tuple(alive)
        return (None,) + tuple(alive)

    def _iter_drop_candidates(
        self, pattern, position: Position, side,
        checkpoint: Checkpoint | None = None,
    ):
        drop_gid = next(
            (
                g
                for g in pattern.geometry_ids
                if self.ir.geometry[g].kind == "drop"
            ),
            "",
        )
        for tid in pattern.type_ids:
            _checkpoint(checkpoint)
            mask = self.support.drop_allowed.get(tid, ((), ()))[side]
            hand = dict(position.hands[side].counts)
            if hand.get(tid, 0) <= 0:
                continue
            for target in range(self.support.board_size * self.support.board_size):
                _checkpoint(checkpoint)
                if not mask[target] or position.board[target] is not None:
                    continue
                binding = self._make_binding(
                    pattern, drop_gid, tid, None, None, target, None, (), position
                )
                if not self._guards_hold(
                    pattern, position, binding, side, checkpoint=checkpoint
                ):
                    continue
                action = SemanticAction(
                    pattern_id=pattern.pattern_id,
                    source=None,
                    target=target,
                    actor_type=tid,
                    geometry_id=drop_gid,
                )
                yield action, binding

    def _guards_hold(
        self, pattern, position, binding, perspective,
        checkpoint: Checkpoint | None = None,
    ) -> bool:
        for guard in pattern.guards:
            _checkpoint(checkpoint)
            if not self._guard_holds(
                guard, position, binding, perspective, checkpoint=checkpoint
            ):
                return False
        for slot_guard in pattern.slot_guards:
            _checkpoint(checkpoint)
            if not self._slot_guard_holds(slot_guard, position, binding, perspective):
                return False
        return True

    def _trial_child_if_s3_legal(
        self, pattern, position: Position, action, binding,
        checkpoint: Checkpoint | None = None,
    ) -> Position | None:
        """One S3 trial transition per candidate; returns the exact child
        Position or ``None`` when S3-illegal.  The same child is handed to
        the S4 postconditions in normal mode, so a candidate never gets a
        second, theoretically-equivalent transition (ADR-016 section 9)."""
        try:
            if checkpoint is None:
                child = self._transition(position, action, binding)
            else:
                child = self._transition(
                    position, action, binding, checkpoint=checkpoint
                )
        except RuntimeError:
            return None
        for invariant in pattern.invariants:
            _checkpoint(checkpoint)
            if invariant.kind == "own_anchor_safe":
                if self.in_check(
                    child, position.side_to_move, checkpoint=checkpoint
                ):
                    return None
            elif invariant.kind == "squares_not_attacked":
                for ref in invariant.square_refs:
                    _checkpoint(checkpoint)
                    idx = _resolve_square_ref(
                        ref, self.support, self.ir.aux_slots, position,
                        position.side_to_move, binding,
                    )
                    if idx is not None and self.is_square_attacked(
                        child, idx, 1 - position.side_to_move,
                        checkpoint=checkpoint,
                    ):
                        return None
        return child

    def _action_delivers_check(
        self, position: Position, child: Position, action,
        checkpoint: Checkpoint | None = None,
    ) -> bool:
        """Return whether this action's actor itself checks the reply side.

        This is distinct from the resulting position being checked: a
        position may already contain a check from an earlier history state.
        The distinction is a generic action-witness primitive and is needed
        by bounded postconditions such as a checking drop restriction.
        """
        anchor = _own_anchor(child, self.support, child.side_to_move)
        if anchor is None:
            return False
        source = action.target
        piece = child.board[source]
        if piece is None or piece.owner != position.side_to_move:
            return False
        for pattern in self._patterns:
            _checkpoint(checkpoint)
            if pattern.target.kind != "target_enemy" or piece.current_type_id not in pattern.type_ids:
                continue
            for gid in pattern.geometry_ids:
                _checkpoint(checkpoint)
                geometry = self.ir.geometry.get(gid)
                if geometry is None or geometry.kind == "drop":
                    continue
                if geometry.atom_source is not None and geometry.atom_source[0] != piece.current_type_id:
                    continue
                for target, path in geometry_candidates(
                    geometry, str(piece.owner), source
                ):
                    _checkpoint(checkpoint)
                    if target != anchor:
                        continue
                    binding = self._make_binding(
                        pattern,
                        gid,
                        piece.current_type_id,
                        piece,
                        source,
                        target,
                        None,
                        path,
                        child,
                    )
                    if self._path_holds(
                        pattern.path, child, binding, piece.owner,
                        checkpoint=checkpoint,
                    ) and self._guards_hold(
                        pattern, child, binding, piece.owner,
                        checkpoint=checkpoint,
                    ):
                        return True
        return False

    def _violates_postconditions(
        self, pattern, child, checkpoint: Checkpoint | None = None
    ) -> bool:
        """S4 forbidden-condition conjunction (ADR-016 truth table).

        Postconditions are prohibitions: the candidate is rejected only when
        every present forbidden condition holds.  ``opponent_checked`` is
        evaluated first and short-circuits the conjunction so the C4 reply
        probe does not run when it is false.  Source field order never
        decides semantics or cost."""
        kinds = {pc.kind for pc in pattern.postconditions}
        if not kinds:
            return False
        parent = getattr(self, "_postcondition_parent", None)
        action = getattr(self, "_postcondition_action", None)
        action_checked = (
            "action_delivers_check" in kinds
            and action is not None
            and self._action_delivers_check(
                parent, child, action, checkpoint=checkpoint
            )
        )
        if "action_delivers_check" in kinds and not action_checked:
            return False
        child_checked = "opponent_checked" in kinds and self.in_check(
            child, child.side_to_move, checkpoint=checkpoint
        )
        if "opponent_checked" in kinds and not child_checked:
            return False
        if "no_legal_reply" in kinds and self._exists_s3_reply(
            child, checkpoint=checkpoint
        ):
            return False
        return True

    def _exists_s3_reply(
        self, position: Position, checkpoint: Checkpoint | None = None
    ) -> bool:
        """``EXISTS_LEGAL_REPLY(stratum <= S3)``: early-exit existence scan
        over ALL patterns with S4 postconditions disabled (Option B).  It
        never consults terminal/repetition/max-ply/history (ADR-016 section
        8)."""
        for pattern in self._patterns:
            _checkpoint(checkpoint)
            for action, binding in self._iter_candidates(
                pattern, position, checkpoint=checkpoint
            ):
                _checkpoint(checkpoint)
                if checkpoint is None:
                    reply_child = self._trial_child_if_s3_legal(
                        pattern, position, action, binding
                    )
                else:
                    reply_child = self._trial_child_if_s3_legal(
                        pattern, position, action, binding,
                        checkpoint=checkpoint,
                    )
                if reply_child is not None:
                    return True
        return False

    def iter_legal_action_bindings(
        self, position: Position, checkpoint: Checkpoint | None = None
    ) -> Iterator[tuple[SemanticAction, _ActionBinding]]:
        """Stream legal runtime actions with their verified S3 binding."""
        self._ensure_match(position)
        for pattern in self._patterns:
            _checkpoint(checkpoint)
            for action, binding in self._iter_candidates(
                pattern, position, checkpoint=checkpoint
            ):
                _checkpoint(checkpoint)
                if checkpoint is None:
                    child = self._trial_child_if_s3_legal(
                        pattern, position, action, binding
                    )
                else:
                    child = self._trial_child_if_s3_legal(
                        pattern, position, action, binding,
                        checkpoint=checkpoint,
                    )
                if child is None:
                    continue
                self._postcondition_parent = position
                self._postcondition_action = action
                try:
                    if checkpoint is None:
                        violates = self._violates_postconditions(pattern, child)
                    else:
                        violates = self._violates_postconditions(
                            pattern, child, checkpoint=checkpoint
                        )
                finally:
                    self._postcondition_parent = None
                    self._postcondition_action = None
                if violates:
                    continue
                _checkpoint(checkpoint)
                yield action, binding

    def iter_legal_actions(
        self, position: Position, checkpoint: Checkpoint | None = None
    ) -> Iterator[SemanticAction]:
        """Stream S0-S4 legal actions from the canonical semantic machinery."""
        for action, _binding in self.iter_legal_action_bindings(
            position, checkpoint=checkpoint
        ):
            yield action

    def legal_actions(
        self, position: Position, checkpoint: Checkpoint | None = None
    ) -> tuple[SemanticAction, ...]:
        """All S0-S4 legal actions (public membership authority)."""
        return tuple(self.iter_legal_actions(position, checkpoint=checkpoint))

    def _transition(
        self, position: Position, action: SemanticAction, binding,
        checkpoint: Checkpoint | None = None,
    ) -> Position:
        """Apply one semantic action with the full aux lifecycle and
        transition-trigger semantics (pre-audit contract E / ADR-015 §6)."""
        pattern = binding.pattern
        side = position.side_to_move
        work = _WorkingPosition(position, self.support)
        # 2) copy parent aux (operands were bound pre-action by the caller).
        aux = dict(position.aux_state)
        # 3) expire every logical instance of every expire_next_turn slot.
        for slot in self.ir.aux_slots:
            _checkpoint(checkpoint)
            if slot.lifetime == "expire_next_turn":
                for owner in _logical_owners(slot):
                    _checkpoint(checkpoint)
                    aux[(slot.slot_id, owner)] = slot.initial
        # 4) board/hand/type effects in declared order; aux effects deferred
        #    to step 6 per the compiled effect sequence.
        aux_effects: list = []
        for effect in pattern.effects:
            _checkpoint(checkpoint)
            if effect.kind in ("set_bool", "clear_right", "set_token", "clear_token"):
                aux_effects.append(effect)
                continue
            _apply_effect(effect, work, self.support, self.ir.aux_slots, position, binding)
        if action.promotion_target_id is not None and action.source is not None:
            moved = work.piece_at(action.target)
            if moved is not None and moved.owner == side:
                work.set_piece(
                    action.target,
                    Piece(
                        owner=moved.owner,
                        base_type_id=moved.base_type_id,
                        current_type_id=action.promotion_target_id,
                        promoted=True,
                    ),
                )
        # 5) transition triggers against the pre-bound event trace.
        for trigger in self.ir.triggers:
            _checkpoint(checkpoint)
            slot = _aux_slot_by_id(self.ir.aux_slots, trigger.slot_id)
            if slot is None:
                continue
            if slot.scope == "per_owner":
                for owner in (0, 1):
                    _checkpoint(checkpoint)
                    if self._trigger_fires(
                        trigger, owner, position, work, binding,
                        checkpoint=checkpoint,
                    ):
                        aux[(trigger.slot_id, owner)] = 0
            else:
                if self._trigger_fires(
                    trigger, side, position, work, binding,
                    checkpoint=checkpoint,
                ):
                    aux[(trigger.slot_id, GLOBAL_OWNER_TAG)] = 0
        # 6) explicit aux effects in declared order.
        for effect in aux_effects:
            _checkpoint(checkpoint)
            _apply_aux_effect(effect, aux, self.support, self.ir.aux_slots, position, binding)
        # 7) switch side.
        work.side = 1 - side
        return work.to_position(
            tuple(sorted(aux.items())),
            self.support.ruleset_fingerprint,
        )

    def _trigger_fires(
        self, trigger, owner, position, work, binding,
        checkpoint: Checkpoint | None = None,
    ) -> bool:
        idx = _resolve_square_ref(
            trigger.square_ref, self.support, self.ir.aux_slots,
            position, owner, binding,
        )
        if idx is None:
            return False
        for event, piece, square in work.events:
            _checkpoint(checkpoint)
            if event != trigger.event or square != idx or piece is None:
                continue
            if trigger.owner == "self" and piece.owner != owner:
                continue
            if trigger.owner == "opponent" and piece.owner == owner:
                continue
            return True
        return False

    def apply(self, position: Position, action: SemanticAction) -> Position:
        from .errors import IllegalActionError

        self._ensure_match(position)
        if action not in self.legal_actions(position):
            raise IllegalActionError(
                f"action is not legal in the current state: {action}"
            )
        pattern = next(
            p for p in self.ir.patterns if p.pattern_id == action.pattern_id
        )
        binding = self._make_binding_from_action(position, action, pattern)
        return self._transition(position, action, binding)

    # ------------------------------------------------------- terminal

    def has_legal_action(
        self, position: Position, checkpoint: Checkpoint | None = None
    ) -> bool:
        for _action in self.iter_legal_actions(position, checkpoint=checkpoint):
            return True
        return False

    def terminal_result(
        self,
        position: Position,
        ply_count: int,
        repetition_counts,
        history=(),
        checkpoint: Checkpoint | None = None,
    ):
        from .terminal import (
            TerminalResult,
            TerminalStatus,
            _perpetual_check_result,
        )

        self._ensure_match(position)
        if not self.has_legal_action(position, checkpoint=checkpoint):
            if self.in_check(
                position, position.side_to_move, checkpoint=checkpoint
            ):
                return TerminalResult(TerminalStatus.CHECKMATE, 1 - position.side_to_move)
            return TerminalResult(TerminalStatus.STALEMATE)
        if self.support.repetition_policy == "continuous_check_loss":
            perpetual = _perpetual_check_result(
                repetition_counts, history, self.support.repetition_limit
            )
            if perpetual is not None:
                return perpetual
        if any(count >= self.support.repetition_limit for _, count in repetition_counts):
            return TerminalResult(TerminalStatus.REPETITION)
        if ply_count >= self.support.max_ply:
            return TerminalResult(TerminalStatus.MAX_PLY)
        return TerminalResult(TerminalStatus.ONGOING)
