"""Small, deterministic random rulesets for benchmark admission work.

This module deliberately does not extend :mod:`generic_chess.generation`.
The production generator has a different material contract; F86A needs a
minimal one-anchor-per-side position with mirrored ordinary material.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from ..core.coordinates import Square
from ..core.movement import LeapAtom, RayAtom
from ..core.pieces import Piece, PieceType
from ..rules.compiler import compile_ruleset
from ..rules.schema import RuleSet
from ..rules.validation import RuleValidationError


_LEAPS = ((1, 0), (0, 1), (1, 1), (2, 1), (1, 2), (-1, 1))
_RAYS = ((1, 0), (0, 1), (1, 1), (-1, 1))


@dataclass(frozen=True, slots=True)
class MinimalGeneratedGame:
    """A generated ruleset and its compiled execution form."""

    seed: int
    board_size: int
    ordinary_count: int
    ruleset: RuleSet
    compiled: object

    @property
    def ruleset_fingerprint(self) -> str:
        return self.compiled.ruleset_fingerprint


def _rotate(square: Square, board_size: int) -> Square:
    return Square(board_size - 1 - square.file, board_size - 1 - square.rank)


def _movement_atoms(rng: random.Random, *, anchor: bool = False):
    if anchor:
        return tuple(LeapAtom(offset) for offset in ((1, 0), (0, 1), (1, 1), (-1, 1)))
    atoms = []
    if rng.random() < 0.7:
        atoms.append(LeapAtom(rng.choice(_LEAPS)))
    if rng.random() < 0.7:
        atoms.append(LeapAtom(rng.choice(_LEAPS)))
    if rng.random() < 0.55:
        atoms.append(RayAtom(rng.choice(_RAYS), rng.choice((1, 2, None))))
    if not atoms:
        atoms.append(LeapAtom(rng.choice(_LEAPS)))
    # Preserve deterministic uniqueness without changing the order used by
    # the compiler's movement tables.
    return tuple(dict.fromkeys(atoms))


def _paired_squares(board_size: int, rng: random.Random, count: int) -> list[Square]:
    """Choose ``count`` owner-0 squares from distinct 180-degree orbits."""
    orbits = []
    seen: set[Square] = set()
    for rank in range(board_size):
        for file in range(board_size):
            square = Square(file, rank)
            if square in seen:
                continue
            rotated = _rotate(square, board_size)
            seen.add(square)
            seen.add(rotated)
            if rotated != square:
                orbits.append((square, rotated))
    rng.shuffle(orbits)
    chosen = []
    for first, second in orbits[:count]:
        chosen.append(first if rng.randrange(2) == 0 else second)
    return chosen


def _build_ruleset(
    rng: random.Random,
    board_size: int,
    ordinary_count: int,
    max_ply: int,
    seed: int,
) -> RuleSet:
    ordinary_type_count = rng.randint(1, min(3, ordinary_count))
    ordinary_ids = tuple(f"P{i}" for i in range(ordinary_type_count))
    piece_types = [
        PieceType(
            type_id="K",
            name="Anchor",
            movement_atoms=_movement_atoms(rng, anchor=True),
            is_anchor=True,
        )
    ]
    piece_types.extend(
        PieceType(type_id=type_id, name=f"Ordinary {type_id}", movement_atoms=_movement_atoms(rng))
        for type_id in ordinary_ids
    )

    squares = _paired_squares(board_size, rng, ordinary_count + 1)
    if len(squares) != ordinary_count + 1:
        raise ValueError("board does not contain enough non-central rotation orbits")
    assignments = ["K"] + [rng.choice(ordinary_ids) for _ in range(ordinary_count)]
    board: list[Piece | None] = [None] * (board_size * board_size)
    for square, type_id in zip(squares, assignments):
        board[square.rank * board_size + square.file] = Piece(0, type_id, type_id)
        rotated = _rotate(square, board_size)
        board[rotated.rank * board_size + rotated.file] = Piece(1, type_id, type_id)

    rows = tuple(
        tuple(board[rank * board_size : (rank + 1) * board_size])
        for rank in range(board_size)
    )
    false_mask = (False,) * (board_size * board_size)
    return RuleSet(
        board_size=board_size,
        piece_types=tuple(piece_types),
        initial_position=rows,
        drop_allowed={type_id: (false_mask, false_mask) for type_id in ordinary_ids},
        promotion_allowed={},
        promotion_forced={},
        repetition_limit=4,
        repetition_policy="draw",
        max_ply=max_ply,
        stalemate_result="draw",
        metadata={
            "generator": "f86a-minimal",
            "seed": seed,
            "ordinary_count": ordinary_count,
        },
    )


def generate_minimal_game(
    seed: int,
    *,
    board_size: int = 5,
    ordinary_count: int | None = None,
    max_ply: int = 96,
    max_attempts: int = 128,
) -> MinimalGeneratedGame:
    """Generate a valid F86A ruleset using only LEAP/RAY movement atoms."""
    if board_size not in (4, 5, 6):
        raise ValueError("F86A minimal generator supports board sizes 4, 5, and 6")
    if ordinary_count is not None and not 2 <= ordinary_count <= 5:
        raise ValueError("ordinary_count must be between 2 and 5")
    if max_ply < 1 or max_attempts < 1:
        raise ValueError("max_ply and max_attempts must be positive")

    rng = random.Random(seed)
    requested_count = ordinary_count if ordinary_count is not None else rng.randint(2, 5)
    for _ in range(max_attempts):
        ruleset = _build_ruleset(rng, board_size, requested_count, max_ply, seed)
        try:
            compiled = compile_ruleset(ruleset)
        except RuleValidationError:
            # Random placement can put an anchor in check or leave the side
            # to move without an action.  Retrying is bounded and deterministic.
            continue
        return MinimalGeneratedGame(seed, board_size, requested_count, ruleset, compiled)
    raise RuntimeError(
        f"could not generate a valid minimal game after {max_attempts} attempts"
    )
