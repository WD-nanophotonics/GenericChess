"""Legal move generation and position-level state transitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .actions import Action, BoardMove, DropMove
from .attacks import anchor_square, is_square_attacked
from .coordinates import Square, index_to_square, square_to_index
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


def apply_action_to_position(
    position: Position, action: Action, compiled: "CompiledRuleSet"
) -> Position:
    """Apply ``action`` to the board/hands and switch the side to move.

    The caller is responsible for passing a legal action; this function only
    performs the mechanical update (including capture -> hand, and promotion).
    """
    n = compiled.board_size
    side = position.side_to_move
    board = list(position.board)
    hands = position.hands

    if isinstance(action, BoardMove):
        from_idx = square_to_index(action.from_square, n)
        to_idx = square_to_index(action.to_square, n)
        piece = board[from_idx]
        if piece is None or piece.owner != side:
            raise ValueError(f"illegal board move from square without own piece: {action}")
        captured = board[to_idx]
        if captured is not None and captured.owner == side:
            raise ValueError(f"cannot capture own piece: {action}")
        if captured is not None and _is_anchor(captured, compiled):
            raise ValueError(f"anchors cannot be captured: {action}")

        if action.promotion_target_id is not None:
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
        to_idx = square_to_index(action.to_square, n)
        if board[to_idx] is not None:
            raise ValueError(f"cannot drop onto an occupied square: {action}")
        if hands[side].count(action.base_type_id) <= 0:
            raise ValueError(f"no {action.base_type_id} in hand: {action}")
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
    after = apply_action_to_position(position, action, compiled)
    side = position.side_to_move
    own_anchor = anchor_square(after, side, compiled)
    if own_anchor is None:
        return False
    return not is_square_attacked(after, own_anchor, 1 - side, compiled)


def legal_actions_from_position(
    position: Position, compiled: "CompiledRuleSet"
) -> list[Action]:
    """All legal actions for the side to move in ``position``."""
    pseudo = _piece_actions(position, compiled)
    expanded: list[Action] = []
    for action in pseudo:
        if isinstance(action, BoardMove):
            piece = position.board[square_to_index(action.from_square, compiled.board_size)]
            expanded.extend(_promotion_variants(action, piece, position, compiled))
        else:
            expanded.append(action)
    expanded.extend(_drop_actions(position, compiled))
    return [a for a in expanded if _is_legal(position, a, compiled)]


def legal_actions(state: "GameState", compiled: "CompiledRuleSet") -> list[Action]:
    """Public API: legal actions of a game state (empty when terminal)."""
    from .terminal import TerminalStatus

    if state.terminal_status.status is not TerminalStatus.ONGOING:
        return []
    return legal_actions_from_position(state.position, compiled)
