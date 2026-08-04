"""Pseudo-attacks, attacked-square queries and check detection.

Pseudo-attacks consider only movement geometry, board boundaries, ray
blocking and current occupancy.  They do *not* consider whether performing
the attack would expose the attacker's own anchor: pinned pieces still
produce pseudo-attacks and friendly-occupied squares are still "protected".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .coordinates import Square, index_to_square, square_to_index
from .movement import LeapAtom
from .position import Position

if TYPE_CHECKING:
    from ..rules.compiled import CompiledRuleSet

AttackMap = frozenset[Square]


def anchor_square(position: Position, player: int, compiled: "CompiledRuleSet") -> Square | None:
    """The square of ``player``'s anchor, or ``None`` if missing/inconsistent."""
    n = compiled.board_size
    for idx, piece in enumerate(position.board):
        if piece is not None and piece.owner == player:
            if compiled.types_by_id[piece.current_type_id].is_anchor:
                return index_to_square(idx, n)
    return None


def pseudo_attacks(position: Position, player: int, compiled: "CompiledRuleSet") -> AttackMap:
    """All squares geometrically attacked by ``player``'s pieces."""
    n = compiled.board_size
    attacked: set[Square] = set()
    for idx, piece in enumerate(position.board):
        if piece is None or piece.owner != player:
            continue
        tid = piece.current_type_id
        square = index_to_square(idx, n)
        atoms = compiled.types_by_id[tid].movement_atoms
        leap_row = compiled.leap_targets[tid][player][idx]
        ray_row = compiled.ray_paths[tid][player][idx]
        for a_idx, atom in enumerate(atoms):
            if isinstance(atom, LeapAtom):
                attacked.update(leap_row[a_idx])
            else:
                for target in ray_row[a_idx]:
                    attacked.add(target)
                    if position.board[square_to_index(target, n)] is not None:
                        break
    return frozenset(attacked)


def is_square_attacked(
    position: Position, square: Square, by_player: int, compiled: "CompiledRuleSet"
) -> bool:
    return square in pseudo_attacks(position, by_player, compiled)


def is_in_check(position: Position, player: int, compiled: "CompiledRuleSet") -> bool:
    sq = anchor_square(position, player, compiled)
    if sq is None:
        return False
    return is_square_attacked(position, sq, 1 - player, compiled)
