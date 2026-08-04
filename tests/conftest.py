"""Shared helpers for building hand-made rulesets and positions in tests."""

from __future__ import annotations

from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.coordinates import Square
from generic_chess.core.keys import position_key
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import GameState, Hands, Position
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.generation.drop_derivation import derive_drop_mask
from generic_chess.generation.promotion_derivation import derive_promotion_data
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import RuleSet


KING_ATOMS = tuple(
    LeapAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1) if (df, dr) != (0, 0)
)


def king_type() -> PieceType:
    return PieceType("K", "King", KING_ATOMS, is_anchor=True)


def T(
    type_id: str,
    *atoms,
    is_anchor: bool = False,
    is_promotable: bool = False,
    targets=(),
) -> PieceType:
    """Compact PieceType factory."""
    return PieceType(
        type_id=type_id,
        name=type_id,
        movement_atoms=tuple(atoms),
        is_anchor=is_anchor,
        is_promotable=is_promotable,
        promotion_target_ids=tuple(targets),
    )


def sq(f: int, r: int) -> Square:
    return Square(f, r)


def parse_lines(n: int, lines: list[str]) -> tuple[tuple[Piece | None, ...], ...]:
    """Parse a top-first ASCII board (line 0 = rank n-1) into rank-0-first rows.

    ``.`` is an empty square; uppercase letters are player 0 pieces, lowercase
    letters are player 1 pieces of the same type.
    """
    rows: list[tuple[Piece | None, ...]] = []
    for line in reversed(lines):
        assert len(line) == n, f"expected row of length {n}, got {line!r}"
        row = []
        for ch in line:
            if ch == ".":
                row.append(None)
            else:
                owner = 0 if ch.isupper() else 1
                tid = ch.upper()
                row.append(Piece(owner=owner, base_type_id=tid, current_type_id=tid, promoted=False))
        rows.append(tuple(row))
    return tuple(rows)


def default_lines(n: int) -> list[str]:
    """A safe default initial board: kings in opposite corners."""
    lines = ["." * n for _ in range(n - 1)]
    lines.append("K" + "." * (n - 2) + "k")
    return lines


def _all_true(n: int) -> tuple[bool, ...]:
    return (True,) * (n * n)


def auto_drop_masks(n: int, atoms) -> tuple[tuple[bool, ...], tuple[bool, ...]]:
    return (derive_drop_mask(n, 0, atoms), derive_drop_mask(n, 1, atoms))


def auto_promotion_masks(n: int, atoms):
    """(allowed, forced) per player derived like the generator does."""
    pa0, pf0 = derive_promotion_data(n, 0, atoms)
    pa1, pf1 = derive_promotion_data(n, 1, atoms)
    return (pa0, pa1), (pf0, pf1)


def make_ruleset(
    n: int,
    types: list[PieceType],
    lines: list[str] | None = None,
    *,
    drop_all: dict[str, tuple[bool, ...]] | None = None,
    auto_drop: bool = False,
    promotion: dict[str, tuple[list, list]] | None = None,
    auto_promotion: bool = False,
    repetition_limit: int = 4,
    max_ply: int = 512,
) -> RuleSet:
    """Build a RuleSet; default drop mask is all squares, no promotions."""
    types = tuple(types)
    lines = lines or default_lines(n)
    initial = parse_lines(n, lines)

    drop: dict[str, tuple[tuple[bool, ...], ...]] = {}
    for t in types:
        if t.is_anchor:
            continue
        if drop_all is not None and t.type_id in drop_all:
            mask = tuple(drop_all[t.type_id])
            drop[t.type_id] = (mask, mask)
        elif auto_drop:
            d0, d1 = auto_drop_masks(n, t.movement_atoms)
            drop[t.type_id] = (d0, d1)
        else:
            mask = _all_true(n)
            drop[t.type_id] = (mask, mask)

    allowed: dict[str, tuple[frozenset, ...]] = {}
    forced: dict[str, tuple[frozenset, ...]] = {}
    for t in types:
        if not t.is_promotable:
            continue
        if auto_promotion:
            (pa0, pa1), (pf0, pf1) = auto_promotion_masks(n, t.movement_atoms)
            allowed[t.type_id] = (pa0, pa1)
            forced[t.type_id] = (pf0, pf1)
        elif promotion is not None and t.type_id in promotion:
            pairs, forced_squares = promotion[t.type_id]
            a = frozenset(pairs)
            f = frozenset(forced_squares)
            allowed[t.type_id] = (a, a)
            forced[t.type_id] = (f, f)
        else:
            allowed[t.type_id] = (frozenset(), frozenset())
            forced[t.type_id] = (frozenset(), frozenset())

    return RuleSet(
        schema_version=1,
        board_size=n,
        piece_types=types,
        initial_position=initial,
        drop_allowed=drop,
        promotion_allowed=allowed,
        promotion_forced=forced,
        repetition_limit=repetition_limit,
        max_ply=max_ply,
        stalemate_result="draw",
    )


def make_compiled(n: int, types: list[PieceType], **kw):
    return compile_ruleset(make_ruleset(n, types, **kw))


def make_position(
    compiled,
    lines: list[str],
    side_to_move: int = 0,
    hands: tuple[list, list] = ((), ()),
    promoted: dict[tuple[int, int], str] | None = None,
) -> Position:
    """Build an arbitrary position from a top-first ASCII board.

    ``hands`` are two lists of ``(type_id, count)`` pairs; ``promoted`` maps
    ``(file, rank)`` to the base type of a promoted piece (the cell char is
    the current type).
    """
    n = compiled.board_size
    rows = parse_lines(n, lines)
    board = tuple(cell for row in rows for cell in row)
    if promoted:
        board = list(board)
        for (file, rank), base in promoted.items():
            idx = rank * n + file
            piece = board[idx]
            assert piece is not None
            board[idx] = Piece(
                owner=piece.owner,
                base_type_id=base,
                current_type_id=piece.current_type_id,
                promoted=True,
            )
        board = tuple(board)
    hands_t = (Hands(tuple(sorted(hands[0]))), Hands(tuple(sorted(hands[1]))))
    return Position(
        board=board,
        hands=hands_t,
        side_to_move=side_to_move,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
    )


def make_state(compiled, lines, side_to_move=0, hands=((), ()), promoted=None) -> GameState:
    pos = make_position(compiled, lines, side_to_move, hands, promoted)
    key = position_key(pos, compiled)
    return GameState(
        position=pos,
        ply_count=0,
        repetition_counts=((key, 1),),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )


def board_move(f0, r0, f1, r1, promotion_target_id=None) -> BoardMove:
    return BoardMove(sq(f0, r0), sq(f1, r1), promotion_target_id)


def drop_move(tid: str, f: int, r: int) -> DropMove:
    return DropMove(tid, sq(f, r))
