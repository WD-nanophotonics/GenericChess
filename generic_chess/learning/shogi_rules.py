"""Standard-shogi ruleset for GenericChess, expressed through the generic
rule schema (no ``if shogi`` special cases anywhere in Core), plus the
SFEN / USI adapter used for cshogi rule-parity auditing.

Known generic-schema limitations are listed in :data:`SHOGI_MODEL_GAPS`
and surfaced by :func:`shogi_ruleset_meta`: dynamic drop restrictions
(nifu / uchifuzume) and nyugyoku remain outside this certification protocol.
Continuous check is declared by the generic repetition policy of the
semantic ruleset; this module never adds Shogi-specific Core branches.
"""

from __future__ import annotations

import json
from dataclasses import replace

from ..core.actions import Action, BoardMove, DropMove
from ..core.coordinates import Square
from ..core.identity import repetition_identity_key
from ..core.movement import LeapAtom, RayAtom
from ..core.pieces import Piece, PieceType
from ..core.position import GameState, Hands, Position
from ..core.terminal import TerminalResult, _terminal_from_parts
from ..generation.drop_derivation import derive_drop_mask
from ..rules.compiler import compile_ruleset
from ..rules.schema import RuleSet


N = 9

# SFEN piece characters (upper = owner 0 / black, lower = owner 1 / white).
SFEN_CHAR = {
    "K": "K",
    "P": "P",
    "L": "L",
    "N": "N",
    "S": "S",
    "G": "G",
    "B": "B",
    "R": "R",
    "TP": "+P",
    "TL": "+L",
    "TN": "+N",
    "TS": "+S",
    "TB": "+B",
    "TR": "+R",
}
REVERSE_SFEN = {v: k for k, v in SFEN_CHAR.items()}

# cshogi piece indices (0 = empty; order is P L N S B R G K + promoted).
CSHOGI_INDEX = {
    "P": 1,
    "L": 2,
    "N": 3,
    "S": 4,
    "B": 5,
    "R": 6,
    "G": 7,
    "K": 8,
    "TP": 9,
    "TL": 10,
    "TN": 11,
    "TS": 12,
    "TB": 13,
    "TR": 14,
}
# AlphaSho legacy HAND_VALUES order: P L N S G B R.
HAND_ORDER = {"P": 0, "L": 1, "N": 2, "S": 3, "G": 4, "B": 5, "R": 6}


def _king_atoms() -> tuple:
    return tuple(
        LeapAtom((df, dr))
        for df in (-1, 0, 1)
        for dr in (-1, 0, 1)
        if df or dr
    )


def _gold_atoms() -> tuple:
    return (
        LeapAtom((0, 1)),
        LeapAtom((-1, 1)),
        LeapAtom((1, 1)),
        LeapAtom((-1, 0)),
        LeapAtom((1, 0)),
        LeapAtom((0, -1)),
    )


_GOLD = _gold_atoms()


def _bishop_rays() -> tuple:
    return (
        RayAtom((-1, -1)),
        RayAtom((-1, 1)),
        RayAtom((1, -1)),
        RayAtom((1, 1)),
    )


def _rook_rays() -> tuple:
    return (
        RayAtom((0, 1)),
        RayAtom((0, -1)),
        RayAtom((1, 0)),
        RayAtom((-1, 0)),
    )


def _bishop_horse() -> tuple:
    return _bishop_rays() + (
        LeapAtom((0, 1)),
        LeapAtom((0, -1)),
        LeapAtom((1, 0)),
        LeapAtom((-1, 0)),
    )


def _rook_dragon() -> tuple:
    return _rook_rays() + (
        LeapAtom((-1, -1)),
        LeapAtom((-1, 1)),
        LeapAtom((1, -1)),
        LeapAtom((1, 1)),
    )


ATOMS = {
    "P": (LeapAtom((0, 1)),),
    "L": (RayAtom((0, 1)),),
    "N": (LeapAtom((-1, 2)), LeapAtom((1, 2))),
    "S": (
        LeapAtom((0, 1)),
        LeapAtom((-1, 1)),
        LeapAtom((1, 1)),
        LeapAtom((-1, -1)),
        LeapAtom((1, -1)),
    ),
    "G": _GOLD,
    "B": _bishop_rays(),
    "R": _rook_rays(),
    "K": _king_atoms(),
    "TP": _GOLD,
    "TL": _GOLD,
    "TN": _GOLD,
    "TS": _GOLD,
    "TB": _bishop_horse(),
    "TR": _rook_dragon(),
}

PROMOTABLE = ("P", "L", "N", "S", "B", "R")
PROMOTION_TARGET = {
    "P": "TP",
    "L": "TL",
    "N": "TN",
    "S": "TS",
    "B": "TB",
    "R": "TR",
}
_BASE_BY_PROMOTED = {v: k for k, v in PROMOTION_TARGET.items()}
DROPPABLE = ("P", "L", "N", "S", "G", "B", "R")


SHOGI_MODEL_GAPS = [
    {
        "rule": "nifu (double pawn)",
        "expressible": False,
        "description": (
            "dropping a pawn onto a file already occupied by an unpromoted "
            "pawn of the same side is illegal in shogi; the generic schema "
            "only supports static per-square drop masks, not "
            "position-dependent drop restrictions"
        ),
    },
    {
        "rule": "uchifuzume (pawn-drop mate)",
        "expressible": False,
        "description": (
            "a pawn drop that delivers checkmate is illegal in shogi; this "
            "requires a game-state-dependent legality filter that the "
            "generic schema cannot express"
        ),
    },
    {
        "rule": "perpetual check (continuous-check repetition)",
        "expressible": True,
        "description": (
            "the generic repetition policy records checking witnesses and "
            "adjudicates continuous check as a loss for the checking side"
        ),
    },
    {
        "rule": "nyugyoku (king-entry win)",
        "expressible": False,
        "description": (
            "the special win condition for a king entering the promotion "
            "zone is not part of the GenericChess terminal model"
        ),
    },
    {
        "rule": "stalemate",
        "expressible": "deviation",
        "description": (
            "GenericChess declares a stalemate draw; standard shogi has no "
            "stalemate rule (a non-check position with no legal moves cannot "
            "arise in practice)"
        ),
    },
]


def build_shogi_piece_types() -> tuple[PieceType, ...]:
    types = []
    for tid in (
        "K",
        "P",
        "L",
        "N",
        "S",
        "G",
        "B",
        "R",
        "TP",
        "TL",
        "TN",
        "TS",
        "TB",
        "TR",
    ):
        types.append(
            PieceType(
                type_id=tid,
                name=tid,
                movement_atoms=ATOMS[tid],
                is_anchor=tid == "K",
                is_promotable=tid in PROMOTABLE,
                promotion_target_ids=(
                    (PROMOTION_TARGET[tid],) if tid in PROMOTABLE else ()
                ),
            )
        )
    return tuple(types)


def _shogi_initial_rows(*, cshogi_orientation: bool = False) -> tuple[tuple[Piece | None, ...], ...]:
    def piece(tid: str, owner: int) -> Piece:
        return Piece(owner=owner, base_type_id=tid, current_type_id=tid)

    rows: list[tuple[Piece | None, ...]] = []
    # GC row 0 (shogi rank 1): black back rank.
    rows.append(tuple(piece(t, 0) for t in ("L", "N", "S", "G", "K", "G", "S", "N", "L")))
    # The historical legacy preset keeps its original orientation for
    # fingerprint compatibility.  The semantic/cshogi adapter opts into the
    # oracle orientation explicitly.
    row1 = [None] * N
    row1[1] = piece("R" if cshogi_orientation else "B", 0)
    row1[7] = piece("B" if cshogi_orientation else "R", 0)
    rows.append(tuple(row1))
    # GC row 2 (shogi rank 3): black pawns.
    rows.append(tuple(piece("P", 0) for _ in range(N)))
    # GC rows 3-5: empty.
    rows.extend((None,) * N for _ in range(3))
    # GC row 6 (shogi rank 7): white pawns.
    rows.append(tuple(piece("P", 1) for _ in range(N)))
    # GC row 7 (shogi rank 8): white rook/bishop.
    row7 = [None] * N
    row7[1] = piece("B" if cshogi_orientation else "R", 1)
    row7[7] = piece("R" if cshogi_orientation else "B", 1)
    rows.append(tuple(row7))
    # GC row 8 (shogi rank 9): white back rank.
    rows.append(tuple(piece(t, 1) for t in ("L", "N", "S", "G", "K", "G", "S", "N", "L")))
    return tuple(rows)


def _promotion_data(n: int, player: int, include_origin_zone: bool = False):
    """Standard shogi promotion: zone = last three ranks; forced when the
    unpromoted base type would have no mobility at the destination."""
    from ..core.movement import empty_mobility
    from ..core.coordinates import index_to_square

    # GC rank 0 is the SFEN bottom row (USI rank ``i``).  Black/owner 0
    # advances toward rank 8; white/owner 1 advances toward rank 0.
    zone_ranks = (6, 7, 8) if player == 0 else (0, 1, 2)
    allowed: dict[str, frozenset] = {}
    forced: dict[str, frozenset] = {}
    for base in PROMOTABLE:
        atoms = ATOMS[base]
        pairs: set[tuple[Square, Square]] = set()
        forced_squares: set[Square] = set()
        for idx in range(n * n):
            from_sq = index_to_square(idx, n)
            for to_sq in empty_mobility(n, player, from_sq, atoms):
                if to_sq.rank in zone_ranks or (
                    include_origin_zone and from_sq.rank in zone_ranks
                ):
                    pairs.add((from_sq, to_sq))
                    if not empty_mobility(n, player, to_sq, atoms):
                        forced_squares.add(to_sq)
        allowed[base] = frozenset(pairs)
        forced[base] = frozenset(forced_squares)
    return allowed, forced


def build_shogi_ruleset(
    *, corrected_promotion: bool = False, cshogi_orientation: bool = False
) -> RuleSet:
    """Build the standard shogi RuleSet (schema-version 1, no extensions)."""
    promotion_allowed: dict = {}
    promotion_forced: dict = {}
    drop_allowed: dict = {}
    for player in (0, 1):
        pa, pf = _promotion_data(
            N, player, include_origin_zone=corrected_promotion
        )
        for base in PROMOTABLE:
            promotion_allowed.setdefault(base, [None, None])[player] = pa[base]
            promotion_forced.setdefault(base, [None, None])[player] = pf[base]
        for base in DROPPABLE:
            drop_allowed.setdefault(base, [None, None])[player] = derive_drop_mask(
                N, player, ATOMS[base]
            )
        # Promoted types are never dropped (hands store base types only);
        # the schema requires an entry for every non-anchor type, so they
        # get an all-false mask.
        for base in PROMOTION_TARGET.values():
            drop_allowed.setdefault(base, [None, None])[player] = (False,) * (N * N)
    promotion_allowed = {k: tuple(v) for k, v in promotion_allowed.items()}
    promotion_forced = {k: tuple(v) for k, v in promotion_forced.items()}
    drop_allowed = {k: tuple(v) for k, v in drop_allowed.items()}
    return RuleSet(
        schema_version=1,
        board_size=N,
        piece_types=build_shogi_piece_types(),
        initial_position=_shogi_initial_rows(cshogi_orientation=cshogi_orientation),
        drop_allowed=drop_allowed,
        promotion_allowed=promotion_allowed,
        promotion_forced=promotion_forced,
        repetition_limit=4,
        max_ply=512,
        stalemate_result="draw",
        metadata={"preset": "standard_shogi", "source": "learning_phase1_8"},
    )


def shogi_ruleset_meta(compiled) -> dict:
    return {
        "schema_version": 1,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "board_size": compiled.board_size,
        "piece_types": sorted(pt.type_id for pt in compiled.piece_types),
        "promotion_zone_ranks": {"owner0": [6, 7, 8], "owner1": [0, 1, 2]},
        "model_gaps": SHOGI_MODEL_GAPS,
    }


# ================================================================ SFEN


def _sfen_piece_char(piece: Piece) -> str:
    tid = piece.current_type_id
    char = SFEN_CHAR[tid]
    if piece.owner == 1:
        return char.lower().replace("+", "+")
    return char


def _compress_row(pieces: tuple[Piece | None, ...]) -> str:
    out = []
    empty = 0
    for p in pieces:
        if p is None:
            empty += 1
        else:
            if empty:
                out.append(str(empty))
                empty = 0
            out.append(_sfen_piece_char(p))
    if empty:
        out.append(str(empty))
    return "".join(out)


def sfen_hands(hands: tuple[Hands, Hands]) -> str:
    order = ("R", "B", "G", "S", "N", "L", "P")
    parts: list[str] = []
    for owner, hand in enumerate(hands):
        for tid in order:
            count = hand.count(tid)
            if count:
                char = tid if owner == 0 else tid.lower()
                parts.append(f"{count}{char}")  # cshogi count-first format
    return "-" if not parts else "".join(parts)


def gc_to_sfen(state: GameState, compiled) -> str:
    pos = state.position
    rows = []
    for rank in range(N - 1, -1, -1):
        row = tuple(pos.board[rank * N + file] for file in range(N - 1, -1, -1))
        rows.append(_compress_row(row))
    side = "b" if pos.side_to_move == 0 else "w"
    return (
        f"{'/'.join(rows)} {side} {sfen_hands(pos.hands)} {state.ply_count}"
    )


def _parse_hands(token: str, n: int) -> tuple[Hands, Hands]:
    hands = [Hands.empty(), Hands.empty()]
    if token == "-":
        return (hands[0], hands[1])
    counts: list[dict[str, int]] = [{}, {}]
    i = 0
    while i < len(token):
        char = token[i]
        num = ""
        if char.isdigit():  # cshogi count-first format
            while i < len(token) and token[i].isdigit():
                num += token[i]
                i += 1
            char = token[i]
            owner = 0 if char.isupper() else 1
            tid = REVERSE_SFEN[char.upper()]
            counts[owner][tid] = int(num)
            i += 1
        else:  # piece-first fallback
            owner = 0 if char.isupper() else 1
            tid = REVERSE_SFEN[char.upper()]
            i += 1
            while i < len(token) and token[i].isdigit():
                num += token[i]
                i += 1
            counts[owner][tid] = int(num or "1")
    return (
        Hands(tuple(sorted(counts[0].items()))),
        Hands(tuple(sorted(counts[1].items()))),
    )


def sfen_to_gc_state(compiled, sfen: str) -> GameState:
    parts = sfen.split()
    if len(parts) < 4:
        raise ValueError(f"malformed SFEN: {sfen!r}")
    board_part, side, hands_token, ply_token = parts[:4]
    ply = int(ply_token)
    board: list[Piece | None] = [None] * (N * N)
    for row_index, row_text in enumerate(board_part.split("/")):
        gc_rank = N - 1 - row_index
        file_pos = 0
        i = 0
        while i < len(row_text):
            char = row_text[i]
            if char.isdigit():
                file_pos += int(char)
                i += 1
                continue
            promoted = False
            if char == "+":
                promoted = True
                i += 1
                char = row_text[i]
            owner = 0 if char.isupper() else 1
            token = ("+" + char) if promoted else char
            tid = REVERSE_SFEN[token.upper()]
            gc_file = N - 1 - file_pos
            base_tid = _BASE_BY_PROMOTED.get(tid, tid)
            board[gc_rank * N + gc_file] = Piece(
                owner=owner,
                base_type_id=base_tid,
                current_type_id=tid,
                promoted=promoted,
            )
            file_pos += 1
            i += 1
    hand0, hand1 = _parse_hands(hands_token, N)
    position = Position(
        board=tuple(board),
        hands=(hand0, hand1),
        side_to_move=0 if side == "b" else 1,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
    )
    from ..core.semantic_executor import semantic_engine_for

    semantic_engine = semantic_engine_for(compiled)
    if semantic_engine is not None:
        key = repetition_identity_key(position, compiled)
        counts = ((key, 1),)
        status = semantic_engine.terminal_result(position, ply, counts)
    else:
        key = repetition_identity_key(position, compiled)
        counts = ((key, 1),)
        status = _terminal_from_parts(position, ply, counts, compiled)
    return GameState(
        position=position,
        ply_count=ply,
        repetition_counts=counts,
        terminal_status=status,
    )


# ================================================================ USI


def _gc_to_usi_square(sq: Square) -> str:
    return f"{sq.file + 1}{chr(ord('a') + 8 - sq.rank)}"


def _usi_to_gc_square(file_num: int, rank_letter: str) -> Square:
    return Square(file_num - 1, 8 - (ord(rank_letter) - ord("a")))


def gc_action_to_usi(action: Action) -> str:
    if isinstance(action, (BoardMove,)) or hasattr(action, "from_square"):
        out = (
            _gc_to_usi_square(action.from_square)
            + _gc_to_usi_square(action.to_square)
        )
        if action.promotion_target_id is not None:
            out += "+"
        return out
    return f"{action.base_type_id}*{_gc_to_usi_square(action.to_square)}"


def usi_to_gc_action(compiled, state: GameState, usi: str) -> Action:
    s = usi
    promote = s.endswith("+")
    if promote:
        s = s[:-1]
    if len(s) == 4 and s[1] == "*":
        tid = s[0]
        return DropMove(tid, _usi_to_gc_square(int(s[2]), s[3]))
    from_sq = _usi_to_gc_square(int(s[0]), s[1])
    to_sq = _usi_to_gc_square(int(s[2]), s[3])
    promo_target = None
    if promote:
        piece = state.position.board[from_sq.rank * N + from_sq.file]
        if piece is None:
            raise ValueError(f"USI move {usi!r}: no piece at source")
        type_metadata = (
            compiled.types_by_id
            if hasattr(compiled, "types_by_id")
            else compiled.support.type_metadata
        )
        base = type_metadata[piece.base_type_id]
        if not base.promotion_target_ids:
            raise ValueError(f"USI move {usi!r}: base type has no promotion")
        promo_target = base.promotion_target_ids[0]
    return BoardMove(from_sq, to_sq, promo_target)


def gc_legal_usi_set(compiled, state: GameState) -> set[str]:
    from ..core.movegen import legal_actions

    actions = legal_actions(state, compiled)
    return {gc_action_to_usi(a) for a in actions}


# ================================================================ cshogi


def cshogi_available() -> bool:
    try:
        import cshogi  # noqa: F401

        return True
    except ImportError:
        return False


def cshogi_legal_usi_set(sfen: str) -> set[str]:
    """Legal USI moves from cshogi (lazy import; raises if unavailable).

    Adapter convention: moves that capture a king are game-terminating in
    shogi (the game ends at checkmate) and are excluded here to match
    GenericChess's uncapturable-anchor semantics.
    """
    import cshogi

    board = cshogi.Board(sfen)
    return {
        cshogi.move_to_usi(m)
        for m in board.legal_moves
        if cshogi.move_cap(m) != 8
    }


def compare_sfen_parity(compiled, sfen: str) -> dict:
    """Exact legal-action set comparison between GenericChess and cshogi."""
    gc_state = sfen_to_gc_state(compiled, sfen)
    gc_usi = gc_legal_usi_set(compiled, gc_state)
    cshogi_usi = cshogi_legal_usi_set(sfen)
    missing = sorted(cshogi_usi - gc_usi)
    extra = sorted(gc_usi - cshogi_usi)
    return {
        "sfen": sfen,
        "gc_legal_count": len(gc_usi),
        "cshogi_legal_count": len(cshogi_usi),
        "equal": not missing and not extra,
        "missing_in_gc": missing,
        "extra_in_gc": extra,
    }


# ================================================================ curated cases


CURATED_CASES = [
    {
        "id": "initial_position",
        "category": "initial",
        "sfen": "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
    },
    {
        "id": "normal_move_7g7f",
        "category": "normal_move",
        "sfen": "lnsgkgsnl/1r5b1/ppppppppp/9/9/2P6/PP1PPPPPP/1B5R1/LNSGKGSNL w - 2",
    },
    {
        "id": "promotion_zone_pawn",
        "category": "optional_promotion",
        "sfen": "8k/9/9/4P4/9/9/9/9/4K4 b - 1",
    },
    {
        "id": "dead_rank_pawn_drop",
        "category": "dead_rank_drop",
        "sfen": "9/9/9/9/9/9/9/9/4K4 b P 1",
    },
    {
        "id": "nifu",
        "category": "nifu",
        "sfen": "9/9/9/9/9/9/9/9/K3P4 b P 1",
    },
    {
        "id": "uchifuzume",
        "category": "uchifuzume",
        "sfen": "8k/7G1/9/9/9/9/9/9/4K2R1 b P 1",
    },
    {
        "id": "promoted_piece_present",
        "category": "promoted_piece",
        "sfen": "8k/7+P1/9/9/9/9/9/9/4K4 b - 1",
    },
    {
        "id": "white_hand_drop",
        "category": "white_hand",
        "sfen": "8k/9/9/9/9/9/9/9/4K4 w r 1",
    },
]


def curated_parity_cases() -> list[dict]:
    return [dict(c) for c in CURATED_CASES]


# ================================================================ random corpus


def generate_reachable_sfens(
    count: int, seed: int = 20260807, max_plies: int = 80
) -> list[dict]:
    """Deterministic random reachable positions via cshogi (legal play)."""
    import random

    import cshogi

    rng = random.Random(seed)
    positions: list[dict] = []
    game_index = 0
    while len(positions) < count:
        board = cshogi.Board()
        history: list[str] = []
        ply = 0
        while ply < max_plies:
            legal = [
                m
                for m in board.legal_moves
                if cshogi.move_cap(m) != 8  # king capture ends the game
            ]
            if not legal:
                break
            move = rng.choice(legal)
            usi = cshogi.move_to_usi(move)
            board.push_usi(usi)
            history.append(usi)
            ply += 1
            if len(positions) < count:
                positions.append(
                    {
                        "index": len(positions),
                        "game": game_index,
                        "ply": ply,
                        "sfen": board.sfen(),
                        "history": list(history),
                    }
                )
        game_index += 1
        if game_index > 2000:
            raise RuntimeError("could not generate enough reachable positions")
    return positions
