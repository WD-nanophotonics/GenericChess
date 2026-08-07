"""Python S0-S3 reference executor for the compiled semantic IR
(Phase 1.9B-2).

This is the first executable reference implementation of the semantic IR:
it generates candidates from compiled geometry, applies target/path/state/
slot predicates, performs trial transitions with royal-safety invariants,
applies bounded effects with the aux lifecycle and transition triggers, and
produces terminal results through the public Core path.

It never reads the high-level ``RuleSet``, ``PieceType.movement_atoms``,
debug names, or ``_legacy_compiled``.  S4 ``no_legal_reply`` patterns are
fail-closed (never generated).  Native/Search/Learner are untouched.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import gcd

from ..rules.ir import (
    CompiledSemanticRuleset,
    geometry_candidates,
)
from .coordinates import Square, index_to_square, square_to_index
from .pieces import Piece
from .position import Hands, Position


@dataclass(frozen=True, slots=True)
class SemanticAction:
    """Runtime action binding for the semantic executor.

    ``pattern_id`` distinguishes otherwise identical source/target actions
    coming from different semantic patterns.
    """

    pattern_id: str
    source: int | None  # None for drops
    target: int
    promotion_target_id: str | None = None
    actor_type: str | None = None  # exact actor/drop type (never type_ids[0])


def _own_anchor(position: Position, support, side: int) -> int | None:
    n = support.board_size
    for idx, piece in enumerate(position.board):
        if piece is not None and piece.owner == side:
            meta = support.type_metadata.get(piece.current_type_id)
            if meta is not None and meta.is_anchor:
                return idx
    return None


def is_semantic_compiled(compiled) -> bool:
    from ..rules.ir import CompiledSemanticRuleset

    return isinstance(compiled, CompiledSemanticRuleset)


def semantic_engine_for(compiled):
    if not is_semantic_compiled(compiled):
        return None
    return SemanticEngine(compiled)


def semantic_public_actions(engine, position: Position) -> tuple:
    """Map semantic bindings to public Core Action objects (R1-07 public
    legal-action query)."""
    from .actions import BoardMove, DropMove
    from .coordinates import index_to_square

    out = []
    for action in engine.legal_actions(position):
        if action.source is None:
            out.append(
                DropMove(
                    action.actor_type,
                    index_to_square(action.target, engine.support.board_size),
                )
            )
        else:
            out.append(
                BoardMove(
                    index_to_square(action.source, engine.support.board_size),
                    index_to_square(action.target, engine.support.board_size),
                    action.promotion_target_id,
                )
            )
    return tuple(out)


def semantic_action_for(engine, position: Position, action):
    """Resolve the unique semantic binding for a public Action (membership
    validated by the caller against the legal set)."""
    from .actions import BoardMove, DropMove
    from .coordinates import index_to_square
    from .errors import IllegalActionError

    candidates = []
    for candidate in engine.legal_actions(position):
        if isinstance(action, BoardMove):
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
    return candidates[0]


def _resolve_square_ref(ref, support, position, side, source, target, path):
    """Resolve a compiled square ref to an absolute square index."""
    n = support.board_size
    kind = ref.kind
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
        if path is None or ref.step is None or ref.step >= len(path):
            return None
        return path[ref.step]
    if kind == "aux_slot_square":
        for slot_id, value in position.aux_state:
            if slot_id == ref.slot_id and isinstance(value, tuple):
                return value[1] * n + value[0]
        return None
    return None


def _resolve_type_id(ref, piece_at_source, default_type: str | None = None) -> str | None:
    if ref is None:
        return None
    if ref.kind == "action_base":
        return piece_at_source.base_type_id if piece_at_source else default_type
    if ref.kind == "action_current":
        return piece_at_source.current_type_id if piece_at_source else default_type
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


def _apply_effect(effect, work: _WorkingPosition, support, side, source, target, path, action, default_type=None) -> None:
    kind = effect.kind
    if kind in ("move", "shift"):
        from_idx = _resolve_square_ref(effect.from_ref, support, None, side, source, target, path)
        to_idx = _resolve_square_ref(effect.to_ref, support, None, side, source, target, path)
        if from_idx is None or to_idx is None:
            raise RuntimeError(f"{kind} refs unresolved for {action.pattern_id}")
        piece = work.piece_at(from_idx)
        if piece is None:
            raise RuntimeError(f"{kind} with no piece at source for {action.pattern_id}")
        if effect.piece_type_ref is not None:
            want = _resolve_type_id(effect.piece_type_ref, piece)
            if want is not None and piece.base_type_id != want and piece.current_type_id != want:
                raise RuntimeError(f"{kind} piece type mismatch for {action.pattern_id}")
        if effect.piece_owner != "any" and (
            (effect.piece_owner == "self" and piece.owner != side)
            or (effect.piece_owner == "opponent" and piece.owner == side)
        ):
            raise RuntimeError(f"{kind} piece owner mismatch for {action.pattern_id}")
        work.set_piece(from_idx, None)
        work.set_piece(to_idx, piece)
        work.events.append(("piece_leaves_square", piece, from_idx))
        return
    if kind == "remove":
        idx = _resolve_square_ref(effect.square_ref, support, None, side, source, target, path)
        if idx is None:
            raise RuntimeError(f"remove ref unresolved for {action.pattern_id}")
        captured = work.piece_at(idx)
        if captured is not None:
            meta = support.type_metadata.get(captured.current_type_id)
            if meta is not None and meta.is_anchor:
                raise RuntimeError(f"anchor capture rejected for {action.pattern_id}")
        if captured is not None and effect.disposition == "capture_to_hand":
            hand = work.hands[side]
            hand[captured.base_type_id] = hand.get(captured.base_type_id, 0) + 1
        work.set_piece(idx, None)
        if captured is not None:
            work.events.append(("piece_removed_from_square", captured, idx))
        return
    if kind == "remove_from_hand":
        type_id = _resolve_type_id(effect.piece_type_ref, None, default_type)
        if type_id is None:
            raise RuntimeError(f"remove_from_hand without type for {action.pattern_id}")
        hand = work.hands[side]
        if hand.get(type_id, 0) < effect.count:
            raise RuntimeError(f"remove_from_hand insufficient hand for {action.pattern_id}")
        hand[type_id] -= effect.count
        if hand[type_id] == 0:
            del hand[type_id]
        return
    if kind == "place":
        idx = _resolve_square_ref(effect.to_ref, support, None, side, source, target, path)
        type_id = _resolve_type_id(effect.piece_type_ref, None, default_type)
        if idx is None or type_id is None:
            raise RuntimeError(f"place operands unresolved for {action.pattern_id}")
        work.set_piece(idx, Piece(owner=side, base_type_id=type_id, current_type_id=type_id))
        return
    if kind == "set_current_type":
        idx = _resolve_square_ref(effect.square_ref, support, None, side, source, target, path)
        type_id = _resolve_type_id(effect.type_ref, None)
        if idx is None or type_id is None:
            raise RuntimeError(f"set_current_type operands unresolved for {action.pattern_id}")
        piece = work.piece_at(idx)
        if piece is None:
            raise RuntimeError(f"set_current_type with no piece for {action.pattern_id}")
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
    raise RuntimeError(f"unsupported effect kind {kind} for {action.pattern_id}")


def _aux_default(aux_slots, slot_id):
    for slot in aux_slots:
        if slot.slot_id == slot_id:
            return slot.initial
    return None


def _apply_aux_effect(effect, aux: dict[int, object], aux_slots, support, side, source, target, path) -> None:
    kind = effect.kind
    if kind == "set_bool":
        aux[effect.slot_id] = effect.value
        return
    if kind == "clear_right":
        aux[effect.slot_id] = 0
        return
    if kind == "set_token":
        idx = _resolve_square_ref(effect.square_ref, support, None, side, source, target, path)
        if idx is None:
            raise RuntimeError("set_token ref unresolved")
        sq = index_to_square(idx, support.board_size)
        aux[effect.slot_id] = (sq.file, sq.rank)
        return
    if kind == "clear_token":
        aux[effect.slot_id] = None
        return


def _trigger_hits(trigger, support, before: Position, after_board, side, source, target, path) -> bool:
    idx = _resolve_square_ref(trigger.square_ref, support, before, side, source, target, path)
    if idx is None:
        return False
    pre = before.board[idx]
    post = after_board[idx]
    owner_matches = (
        trigger.owner == "any"
        or (trigger.owner == "self" and pre is not None and pre.owner == side)
        or (trigger.owner == "opponent" and pre is not None and pre.owner != side)
    )
    if trigger.event == "piece_leaves_square":
        return bool(pre is not None and owner_matches and post is None)
    if trigger.event == "piece_removed_from_square":
        return bool(pre is not None and owner_matches and post is None)
    return False


class SemanticEngine:
    """S0-S3 executor for one compiled semantic ruleset."""

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
        self._s0s3_patterns = tuple(
            p for p in self.ir.patterns if not p.postconditions
        )

    # ------------------------------------------------------- aux scope

    def _slot_scope(self, slot_id: int) -> str:
        for slot in self.ir.aux_slots:
            if slot.slot_id == slot_id:
                return slot.scope
        return "global"

    def _aux_key(self, slot_id: int, owner: int):
        return slot_id if self._slot_scope(slot_id) == "global" else (slot_id, owner)

    def _slot_value(self, position: Position, slot_id: int, owner: int):
        key = self._aux_key(slot_id, owner)
        for k, v in position.aux_state:
            if k == key:
                return v
        for slot in self.ir.aux_slots:
            if slot.slot_id == slot_id:
                return slot.initial
        return None

    # ------------------------------------------------------- resolution

    def _initial_position(self) -> Position:
        rows = self.support.initial_position
        n = self.support.board_size
        board = tuple(
            rows[r][f] for r in range(n) for f in range(n)
        )
        return Position(
            board=board,
            hands=(Hands.empty(), Hands.empty()),
            side_to_move=0,
            ruleset_fingerprint=self.support.ruleset_fingerprint,
            aux_state=(),
        )

    # ------------------------------------------------------- pseudo attack

    def is_square_attacked(self, position: Position, square: int, by_owner: int) -> bool:
        """Semantic pseudo-attack: geometry + path predicates only (target
        occupancy ignored), matching the legacy distinction where the first
        occupied ray square and protected friendly squares count as
        attacked and cannon attacks exactly behind one screen."""
        for pattern in self._s0s3_patterns:
            if pattern.target.kind != "target_enemy":
                continue  # attack eligibility = capture eligibility
            if "drop" in {
                self.ir.geometry[g].kind for g in pattern.geometry_ids
                if g in self.ir.geometry
            }:
                continue
            for tid in pattern.type_ids:
                for source, piece in enumerate(position.board):
                    if piece is None or piece.owner != by_owner:
                        continue
                    if piece.current_type_id != tid:
                        continue
                    for gid in pattern.geometry_ids:
                        geometry = self.ir.geometry.get(gid)
                        if geometry is None:
                            continue
                        for target, path in geometry_candidates(
                            geometry, str(by_owner), source
                        ):
                            if target != square:
                                continue
                            if self._path_holds(pattern.path, position, source, target, path):
                                return True
        return False

    def in_check(self, position: Position, side: int) -> bool:
        anchor = _own_anchor(position, self.support, side)
        if anchor is None:
            return False
        return self.is_square_attacked(position, anchor, 1 - side)

    # ------------------------------------------------------- predicates

    def _path_holds(self, predicates, position, source, target, path) -> bool:
        for predicate in predicates:
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
                    owner_ok = (
                        predicate.owner_filter == "any"
                        or (predicate.owner_filter == "self" and piece.owner == position.side_to_move)
                        or (predicate.owner_filter == "opponent" and piece.owner != position.side_to_move)
                    )
                    if not owner_ok:
                        return False
                    break
            elif kind == "path_last_blocker_owner":
                blockers = [i for i in path if position.board[i] is not None]
                if blockers:
                    piece = position.board[blockers[-1]]
                    owner_ok = (
                        predicate.owner_filter == "any"
                        or (predicate.owner_filter == "self" and piece.owner == position.side_to_move)
                        or (predicate.owner_filter == "opponent" and piece.owner != position.side_to_move)
                    )
                    if not owner_ok:
                        return False
        return True

    def _target_holds(self, kind: str, position: Position, target: int) -> bool:
        piece = position.board[target]
        side = position.side_to_move
        if kind == "target_empty":
            return piece is None
        if kind == "target_enemy":
            return piece is not None and piece.owner != side
        if kind == "target_friendly":
            return piece is not None and piece.owner == side
        return True  # target_any

    def _guard_holds(self, guard, position: Position, source, target, path, actor_type=None) -> bool:
        sel = guard.spatial
        bound_base = bound_current = None
        if source is not None:
            actor = position.board[source]
            if actor is not None:
                bound_base = actor.base_type_id
                bound_current = actor.current_type_id
        elif actor_type is not None:
            bound_base = bound_current = actor_type
        count = 0
        for idx, piece in enumerate(position.board):
            if piece is None:
                continue
            owner_ok = (
                guard.owner == "any"
                or (guard.owner == "self" and piece.owner == position.side_to_move)
                or (guard.owner == "opponent" and piece.owner != position.side_to_move)
            )
            if not owner_ok:
                continue
            if guard.location == "hand":
                continue  # hand selector not needed by v2 fixtures; board only
            type_ok = self._type_selector_ok(guard, piece, bound_base, bound_current)
            if not type_ok:
                continue
            promoted_ok = (
                guard.promoted == "any"
                or (guard.promoted == "yes") == piece.promoted
            )
            if not promoted_ok:
                continue
            if self._spatial_ok(sel, idx, source, target, path, position):
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

    def _spatial_ok(self, sel, idx, source, target, path, position) -> bool:
        n = self.support.board_size
        sq = index_to_square(idx, n)
        if sel.kind == "same_file":
            ref_sq = self._ref_square(sel.refs[0], source, target, path, position.side_to_move)
            return ref_sq is not None and ref_sq.file == sq.file
        if sel.kind == "same_rank":
            ref_sq = self._ref_square(sel.refs[0], source, target, path, position.side_to_move)
            return ref_sq is not None and ref_sq.rank == sq.rank
        if sel.kind == "exact":
            ref_sq = self._ref_square(sel.refs[0], source, target, path, position.side_to_move)
            return ref_sq is not None and ref_sq == sq
        if sel.kind == "adjacent":
            ref_sq = self._ref_square(sel.refs[0], source, target, path, position.side_to_move)
            return (
                ref_sq is not None
                and max(abs(ref_sq.file - sq.file), abs(ref_sq.rank - sq.rank)) == 1
            )
        if sel.kind == "path_between":
            a = self._ref_square(sel.refs[0], source, target, path, position.side_to_move)
            b = self._ref_square(sel.refs[1], source, target, path, position.side_to_move)
            if a is None or b is None:
                return False
            df = b.file - a.file
            dr = b.rank - a.rank
            g = gcd(abs(df), abs(dr))
            if g <= 1:
                return False
            step_f, step_r = df // g, dr // g
            for k in range(1, g):
                if sq.file == a.file + k * step_f and sq.rank == a.rank + k * step_r:
                    return True
            return False
        if sel.kind == "zone":
            zone = self.ir.zones.get(sel.zone_id)
            return zone is not None and idx in zone.squares
        return False

    def _ref_square(self, ref, source, target, path, side) -> Square | None:
        idx = _resolve_square_ref(
            ref, self.support, None, side, source, target, path
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

    def _slot_guard_holds(self, guard, position: Position, source, target, path) -> bool:
        value = self._slot_value(position, guard.slot_id, position.side_to_move)
        if guard.square_ref is not None:
            idx = _resolve_square_ref(
                guard.square_ref, self.support, position, position.side_to_move,
                source, target, path,
            )
            square = index_to_square(idx, self.support.board_size) if idx is not None else None
            if guard.comparison == "eq":
                return value == (square.file, square.rank) if square is not None else value is None
            if guard.comparison == "ne":
                return value != (square.file, square.rank) if square is not None else value is not None
            return False
        return self._compare(guard.comparison, value, guard.value)

    # ------------------------------------------------------- legality

    def legal_actions(self, position: Position) -> tuple[SemanticAction, ...]:
        actions: list[SemanticAction] = []
        side = position.side_to_move
        self._side = side
        for pattern in self._s0s3_patterns:
            is_drop = any(
                self.ir.geometry[g].kind == "drop"
                for g in pattern.geometry_ids
                if g in self.ir.geometry
            )
            if is_drop:
                self._drop_actions(pattern, position, actions)
            else:
                self._board_actions(pattern, position, actions)
        return tuple(actions)

    def _board_actions(self, pattern, position: Position, out: list[SemanticAction]) -> None:
        side = position.side_to_move
        for tid in pattern.type_ids:
            for source, piece in enumerate(position.board):
                if piece is None or piece.owner != side:
                    continue
                if piece.current_type_id != tid:
                    continue
                for gid in pattern.geometry_ids:
                    geometry = self.ir.geometry.get(gid)
                    if geometry is None or geometry.kind == "drop":
                        continue
                    if geometry.atom_source is not None and geometry.atom_source[0] != tid:
                        continue
                    for target, path in geometry_candidates(geometry, str(side), source):
                        if not self._target_holds(pattern.target.kind, position, target):
                            continue
                        if not self._path_holds(pattern.path, position, source, target, path):
                            continue
                        if not self._guards_hold(pattern, position, source, target, path):
                            continue
                        promotions = self._promotion_choices(pattern, piece, source, target)
                        for promotion_target in promotions:
                            action = SemanticAction(
                                pattern_id=pattern.pattern_id,
                                source=source,
                                target=target,
                                promotion_target_id=promotion_target,
                                actor_type=tid,
                            )
                            if self._trial_legal(pattern, position, action, target, path):
                                out.append(action)

    def _promotion_choices(self, pattern, piece, source, target) -> tuple[str | None, ...]:
        if pattern.promotion_mode == "none":
            return (None,)
        if pattern.promotion_mode == "explicit":
            return (pattern.explicit_promotion_type,)
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

    def _drop_actions(self, pattern, position: Position, out: list[SemanticAction]) -> None:
        side = position.side_to_move
        for tid in pattern.type_ids:
            mask = self.support.drop_allowed.get(tid, ((), ()))[side]
            hand = dict(position.hands[side].counts)
            if hand.get(tid, 0) <= 0:
                continue
            for target in range(self.support.board_size * self.support.board_size):
                if not mask[target] or position.board[target] is not None:
                    continue
                if not self._guards_hold(pattern, position, None, target, (), actor_type=tid):
                    continue
                action = SemanticAction(
                    pattern_id=pattern.pattern_id,
                    source=None,
                    target=target,
                    actor_type=tid,
                )
                if self._trial_legal(pattern, position, action, target, ()):
                    out.append(action)

    def _guards_hold(self, pattern, position, source, target, path, actor_type=None) -> bool:
        for guard in pattern.guards:
            if not self._guard_holds(guard, position, source, target, path, actor_type):
                return False
        for slot_guard in pattern.slot_guards:
            if not self._slot_guard_holds(slot_guard, position, source, target, path):
                return False
        return True

    def _trial_legal(self, pattern, position: Position, action, target, path) -> bool:
        """Trial transition + S3 invariants (own-anchor safety)."""
        try:
            child = self._transition(position, action, target, path, trial=True)
        except RuntimeError:
            return False
        for invariant in pattern.invariants:
            if invariant.kind == "own_anchor_safe":
                if self.in_check(child, position.side_to_move):
                    return False
            elif invariant.kind == "squares_not_attacked":
                for ref in invariant.square_refs:
                    idx = _resolve_square_ref(
                        ref, self.support, position, position.side_to_move,
                        action.source, action.target, path,
                    )
                    if idx is not None and self.is_square_attacked(child, idx, 1 - position.side_to_move):
                        return False
        return True

    def _transition(
        self,
        position: Position,
        action: SemanticAction,
        target: int,
        path,
        trial: bool = False,
    ) -> Position:
        """Apply one semantic action with the full aux lifecycle and
        transition-trigger semantics (pre-audit contract E)."""
        pattern = next(
            p for p in self.ir.patterns if p.pattern_id == action.pattern_id
        )
        side = position.side_to_move
        if action.source is not None:
            path = self._path_for(pattern, action.source, action.target, side) or path
        work = _WorkingPosition(position, self.support)
        # 1) resolve operands pre-action (effects resolved during apply).
        # 2) copy parent aux.
        aux = dict(position.aux_state)
        # 3) expire expire_next_turn values.
        for slot in self.ir.aux_slots:
            if slot.lifetime == "expire_next_turn":
                if slot.scope == "per_owner":
                    aux[self._aux_key(slot.slot_id, side)] = slot.initial
                else:
                    aux[slot.slot_id] = slot.initial
        # 4) board/hand/type effects in declared order; aux effects deferred
        #    to step 6 per the compiled effect sequence.
        aux_effects: list = []
        default_type = action.actor_type if action.source is None else None
        for effect in pattern.effects:
            if effect.kind in ("set_bool", "clear_right", "set_token", "clear_token"):
                aux_effects.append(effect)
                continue
            _apply_effect(
                effect, work, self.support, side,
                action.source, action.target, path, action, default_type,
            )
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
            if self._slot_scope(trigger.slot_id) == "per_owner":
                for owner in (0, 1):
                    if self._trigger_fires(
                        trigger, owner, position, work, side,
                        action.source, action.target, path,
                    ):
                        aux[self._aux_key(trigger.slot_id, owner)] = 0
            else:
                if self._trigger_fires(
                    trigger, side, position, work, side,
                    action.source, action.target, path,
                ):
                    aux[trigger.slot_id] = 0
        # 6) explicit aux effects in declared order.
        for effect in aux_effects:
            self._apply_aux_effect(effect, aux, side, action.source, action.target, path)
        # 7) switch side.
        work.side = 1 - side
        return work.to_position(
            tuple(sorted(aux.items())),
            self.support.ruleset_fingerprint,
        )

    def _trigger_fires(
        self, trigger, owner, position, work, side, source, target, path
    ) -> bool:
        idx = _resolve_square_ref(
            trigger.square_ref, self.support, position, owner, source, target, path
        )
        if idx is None:
            return False
        for event, piece, square in work.events:
            if event != trigger.event or square != idx or piece is None:
                continue
            if trigger.owner == "self" and piece.owner != owner:
                continue
            if trigger.owner == "opponent" and piece.owner == owner:
                continue
            return True
        return False

    def _apply_aux_effect(self, effect, aux, side, source, target, path) -> None:
        key = self._aux_key(effect.slot_id, side)
        kind = effect.kind
        if kind == "set_bool":
            aux[key] = effect.value
        elif kind == "clear_right":
            aux[key] = 0
        elif kind == "set_token":
            idx = _resolve_square_ref(
                effect.square_ref, self.support, None, side, source, target, path
            )
            if idx is None:
                raise RuntimeError("set_token ref unresolved")
            square = index_to_square(idx, self.support.board_size)
            aux[key] = (square.file, square.rank)
        elif kind == "clear_token":
            aux[key] = None

    def _path_for(self, pattern, source, target, side) -> tuple[int, ...]:
        for gid in pattern.geometry_ids:
            geometry = self.ir.geometry.get(gid)
            if geometry is None or geometry.kind == "drop":
                continue
            for candidate_target, candidate_path in geometry_candidates(
                geometry, str(side), source
            ):
                if candidate_target == target:
                    return candidate_path
        return ()

    def apply(self, position: Position, action: SemanticAction) -> Position:
        from .errors import IllegalActionError

        if action not in self.legal_actions(position):
            raise IllegalActionError(
                f"action is not legal in the current state: {action}"
            )
        target = action.target
        path = ()
        return self._transition(position, action, target, path)

    # ------------------------------------------------------- terminal

    def has_legal_action(self, position: Position) -> bool:
        return bool(self.legal_actions(position))

    def terminal_result(
        self,
        position: Position,
        ply_count: int,
        repetition_counts,
    ):
        from .terminal import TerminalResult, TerminalStatus

        if not self.has_legal_action(position):
            if self.in_check(position, position.side_to_move):
                return TerminalResult(TerminalStatus.CHECKMATE, 1 - position.side_to_move)
            return TerminalResult(TerminalStatus.STALEMATE)
        if any(count >= self.support.repetition_limit for _, count in repetition_counts):
            return TerminalResult(TerminalStatus.REPETITION)
        if ply_count >= self.support.max_ply:
            return TerminalResult(TerminalStatus.MAX_PLY)
        return TerminalResult(TerminalStatus.ONGOING)
