"""Legal move generation and position-level state transitions."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

from .actions import Action, BoardMove, DropMove
from .attacks import anchor_square, is_square_attacked
from .coordinates import Square, index_to_square, square_to_index
from .errors import IllegalActionError, ensure_ruleset_match
from .movement import LeapAtom
from .pieces import Piece
from .position import Position

if TYPE_CHECKING:
    from ..rules.compiled import CompiledRuleSet
    from .position import GameState


def _is_anchor(piece: Piece | None, compiled: "CompiledRuleSet") -> bool:
    return piece is not None and compiled.types_by_id[piece.current_type_id].is_anchor


def _piece_actions(position: Position, compiled: "CompiledRuleSet") -> list[Action]:
    """Pseudo-legal board moves (without anchor-safety filtering)."""
    n = compiled.board_size
    side = position.side_to_move
    actions: list[Action] = []
    for idx, piece in enumerate(position.board):
        if piece is None or piece.owner != side:
            continue
        square = index_to_square(idx, n)
        tid = piece.current_type_id
        atoms = compiled.types_by_id[tid].movement_atoms
        leap_row = compiled.leap_targets[tid][side][idx]
        ray_row = compiled.ray_paths[tid][side][idx]
        for a_idx, atom in enumerate(atoms):
            if isinstance(atom, LeapAtom):
                for target in leap_row[a_idx]:
                    occupant = position.board[square_to_index(target, n)]
                    if occupant is None:
                        actions.append(BoardMove(square, target))
                    elif occupant.owner != side and not _is_anchor(occupant, compiled):
                        actions.append(BoardMove(square, target))
                    # enemy anchor: attacked but never capturable -> no move
            else:
                for target in ray_row[a_idx]:
                    occupant = position.board[square_to_index(target, n)]
                    if occupant is None:
                        actions.append(BoardMove(square, target))
                        continue
                    if occupant.owner != side and not _is_anchor(occupant, compiled):
                        actions.append(BoardMove(square, target))
                    break  # any occupied square stops the ray
    return actions


def _promotion_variants(
    move: BoardMove, piece: Piece, position: Position, compiled: "CompiledRuleSet"
) -> list[Action]:
    """Expand a board move into its promotion variants per the compiled masks."""
    if piece.promoted:
        return [move]
    base = compiled.types_by_id[piece.base_type_id]
    if not base.is_promotable:
        return [move]
    side = position.side_to_move
    if (move.from_square, move.to_square) not in compiled.promotion_allowed[piece.base_type_id][side]:
        return [move]
    to_idx = square_to_index(move.to_square, compiled.board_size)
    alive_targets = [
        tid
        for tid in base.promotion_target_ids
        if compiled.empty_mobility[tid][side][to_idx]
    ]
    if move.to_square in compiled.promotion_forced[piece.base_type_id][side]:
        # Mandatory promotion: skip unpromoted move and structurally dead targets.
        return [BoardMove(move.from_square, move.to_square, tid) for tid in alive_targets]
    return [move] + [BoardMove(move.from_square, move.to_square, tid) for tid in alive_targets]


def _drop_actions(position: Position, compiled: "CompiledRuleSet") -> list[Action]:
    n = compiled.board_size
    side = position.side_to_move
    actions: list[Action] = []
    for tid, count in position.hands[side].counts:
        if count <= 0:
            continue
        mask = compiled.drop_allowed[tid][side]
        for idx, allowed in enumerate(mask):
            if allowed and position.board[idx] is None:
                actions.append(DropMove(tid, index_to_square(idx, n)))
    return actions


def _expanded_pseudo_actions(
    position: Position, compiled: "CompiledRuleSet"
) -> Iterator[Action]:
    """Pseudo-legal moves with promotion variants and drops (no safety filter)."""
    n = compiled.board_size
    for action in _piece_actions(position, compiled):
        if isinstance(action, BoardMove):
            piece = position.board[square_to_index(action.from_square, n)]
            yield from _promotion_variants(action, piece, position, compiled)
        else:
            yield action
    yield from _drop_actions(position, compiled)


def _apply_action_unchecked(
    position: Position, action: Action, compiled: "CompiledRuleSet"
) -> Position:
    """Mechanical board/hand update without full legal-action validation.

    This is the private executor behind the public, legality-checking
    :func:`apply_action`.  It still guards the basic invariants (bounds, own
    piece, anchor capture, occupied drop squares, hand counts, promotion
    target membership) so that even an internal misuse cannot corrupt a state.
    """
    ensure_ruleset_match(position, compiled)
    n = compiled.board_size
    side = position.side_to_move
    board = list(position.board)
    hands = position.hands

    if isinstance(action, BoardMove):
        if not (0 <= action.from_square.file < n and 0 <= action.from_square.rank < n):
            raise IllegalActionError(f"from square out of bounds: {action}")
        if not (0 <= action.to_square.file < n and 0 <= action.to_square.rank < n):
            raise IllegalActionError(f"to square out of bounds: {action}")
        from_idx = square_to_index(action.from_square, n)
        to_idx = square_to_index(action.to_square, n)
        piece = board[from_idx]
        if piece is None or piece.owner != side:
            raise IllegalActionError(f"illegal board move from square without own piece: {action}")
        captured = board[to_idx]
        if captured is not None and captured.owner == side:
            raise IllegalActionError(f"cannot capture own piece: {action}")
        if captured is not None and _is_anchor(captured, compiled):
            raise IllegalActionError(f"anchors cannot be captured: {action}")

        if action.promotion_target_id is not None:
            base = compiled.types_by_id[piece.base_type_id]
            if piece.promoted:
                raise IllegalActionError(f"already-promoted piece cannot promote again: {action}")
            if not base.is_promotable:
                raise IllegalActionError(f"non-promotable piece cannot promote: {action}")
            if action.promotion_target_id not in base.promotion_target_ids:
                raise IllegalActionError(
                    f"{action.promotion_target_id!r} is not a promotion target of "
                    f"{piece.base_type_id!r}: {action}"
                )
            new_piece = Piece(
                owner=side,
                base_type_id=piece.base_type_id,
                current_type_id=action.promotion_target_id,
                promoted=True,
            )
        else:
            new_piece = piece

        if captured is not None:
            hands_side = hands[side].add(captured.base_type_id)
            hands = (hands_side, hands[1]) if side == 0 else (hands[0], hands_side)

        board[from_idx] = None
        board[to_idx] = new_piece
    else:  # DropMove
        if not (0 <= action.to_square.file < n and 0 <= action.to_square.rank < n):
            raise IllegalActionError(f"drop square out of bounds: {action}")
        to_idx = square_to_index(action.to_square, n)
        if board[to_idx] is not None:
            raise IllegalActionError(f"cannot drop onto an occupied square: {action}")
        if hands[side].count(action.base_type_id) <= 0:
            raise IllegalActionError(f"no {action.base_type_id} in hand: {action}")
        board[to_idx] = Piece(
            owner=side,
            base_type_id=action.base_type_id,
            current_type_id=action.base_type_id,
            promoted=False,
        )
        hands_side = hands[side].remove(action.base_type_id)
        hands = (hands_side, hands[1]) if side == 0 else (hands[0], hands_side)

    return Position(
        board=tuple(board),
        hands=hands,
        side_to_move=1 - side,
        ruleset_fingerprint=position.ruleset_fingerprint,
    )


def _is_legal(position: Position, action: Action, compiled: "CompiledRuleSet") -> bool:
    after = _apply_action_unchecked(position, action, compiled)
    side = position.side_to_move
    own_anchor = anchor_square(after, side, compiled)
    if own_anchor is None:
        return False
    return not is_square_attacked(after, own_anchor, 1 - side, compiled)


Checkpoint = Callable[[], None]


def iter_legal_actions_from_position(
    position: Position,
    compiled: "CompiledRuleSet",
    checkpoint: Checkpoint | None = None,
) -> Iterator[Action]:
    """Stream legacy legal actions in the canonical first-seen order."""
    ensure_ruleset_match(position, compiled)
    seen: set[Action] = set()
    for action in _expanded_pseudo_actions(position, compiled):
        if checkpoint is not None:
            checkpoint()
        if action in seen:
            continue
        if not _is_legal(position, action, compiled):
            continue
        seen.add(action)
        yield action


def legal_actions_from_position(
    position: Position, compiled: "CompiledRuleSet"
) -> list[Action]:
    """All legal actions for the side to move in ``position``."""
    return list(iter_legal_actions_from_position(position, compiled))


def has_legal_action(
    position: Position,
    compiled: "CompiledRuleSet",
    checkpoint: Checkpoint | None = None,
) -> bool:
    """Return at the first legal action for both legacy and semantic paths."""
    from .semantic_executor import semantic_engine_for

    engine = semantic_engine_for(compiled)
    if engine is not None:
        return engine.has_legal_action(position, checkpoint=checkpoint)
    for _action in iter_legal_actions_from_position(
        position, compiled, checkpoint=checkpoint
    ):
        return True
    return False


def iter_legal_actions(
    state: "GameState",
    compiled: "CompiledRuleSet",
    checkpoint: Checkpoint | None = None,
) -> Iterator[Action]:
    """Stream public legal actions without duplicating semantic machinery."""
    from .terminal import TerminalStatus
    from .semantic_executor import (
        iter_semantic_public_actions,
        semantic_engine_for,
    )

    ensure_ruleset_match(state.position, compiled)
    if state.terminal_status.status is not TerminalStatus.ONGOING:
        return
    engine = semantic_engine_for(compiled)
    if engine is not None:
        yield from iter_semantic_public_actions(
            engine, state.position, checkpoint=checkpoint
        )
        return
    yield from iter_legal_actions_from_position(
        state.position, compiled, checkpoint=checkpoint
    )


def legal_actions(
    state: "GameState",
    compiled: "CompiledRuleSet",
    checkpoint: Checkpoint | None = None,
) -> list[Action]:
    """Public API: legal actions of a game state (empty when terminal)."""
    return list(iter_legal_actions(state, compiled, checkpoint=checkpoint))
