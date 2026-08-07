"""Phase 1.9B-2 focused tests: Python S0-S3 semantic reference executor."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from generic_chess.core.coordinates import Square
from generic_chess.core.keys import position_key, semantic_position_key
from generic_chess.core.movegen import legal_actions_from_position
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands, Position
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import (
    compile_ruleset,
    compile_semantic_ruleset,
    lower_legacy_to_ir,
    _build_semantic_support,
)
from generic_chess.rules.ir import CompiledSemanticRuleset

from rule_semantics_ir_fixtures import (
    cannon_ruleset,
    castling_ruleset,
    en_passant_ruleset,
    nifu_ruleset,
)


def _engine(fixture) -> SemanticEngine:
    return SemanticEngine(compile_semantic_ruleset(fixture))


def _idx(support, file, rank):
    return rank * support.board_size + file


def _with_pieces(support, pieces, side=0):
    board = [None] * (support.board_size * support.board_size)
    for idx, piece in pieces:
        board[idx] = piece
    return Position(
        board=tuple(board),
        hands=(Hands.empty(), Hands.empty()),
        side_to_move=side,
        ruleset_fingerprint=support.ruleset_fingerprint,
        aux_state=(),
    )


# ---------------------------------------------------------------- cannon


def _cannon_position(engine, enemy_file, screen=True, extra_screens=()):
    support = engine.support
    n = support.board_size
    pieces = [
        (_idx(support, 0, 0), Piece(0, "C", "C")),  # cannon
        (_idx(support, n - 1, n - 1), Piece(1, "K", "K")),  # enemy king
    ]
    if screen:
        pieces.append((_idx(support, 1, 0), Piece(1, "P", "P")))
    for f in extra_screens:
        pieces.append((_idx(support, f, 0), Piece(1, "P", "P")))
    if enemy_file:
        pieces.append((_idx(support, enemy_file, 0), Piece(1, "P", "P")))
    return _with_pieces(support, pieces)


def test_cannon_quiet_and_screen_capture_legality():
    engine = _engine(cannon_ruleset())
    support = engine.support
    # 0 screens: quiet to empty square legal, capture of adjacent enemy illegal.
    pos = _cannon_position(engine, enemy_file=1, screen=False)
    actions = engine.legal_actions(pos)
    from generic_chess.core.semantic_executor import SemanticAction

    quiet = [
        a for a in actions
        if a.pattern_id == "sem_00_cannon_quiet" and a.source == _idx(support, 0, 0)
    ]
    captures = [
        a for a in actions
        if a.pattern_id == "sem_01_cannon_capture" and a.source == _idx(support, 0, 0)
    ]
    assert quiet, "0-screen quiet must exist"
    assert not captures, "0-screen capture must be illegal"
    # 1 screen: capture behind the screen legal.
    pos1 = _cannon_position(engine, enemy_file=2, screen=True)
    actions1 = engine.legal_actions(pos1)
    captures1 = [
        a for a in actions1
        if a.pattern_id == "sem_01_cannon_capture"
        and a.target == _idx(support, 2, 0)
    ]
    assert captures1, "1-screen capture must be legal"
    # 2 screens: capture illegal.
    pos2 = _cannon_position(engine, enemy_file=4, screen=True, extra_screens=(2,))
    captures2 = [
        a for a in engine.legal_actions(pos2)
        if a.pattern_id == "sem_01_cannon_capture"
        and a.target == _idx(support, 4, 0)
    ]
    assert not captures2, "2-screen capture must be illegal"


def test_cannon_attack_semantics_match_capture_geometry():
    engine = _engine(cannon_ruleset())
    support = engine.support
    # Royal behind exactly one screen is attacked; zero or two screens are not.
    pos = _cannon_position(engine, enemy_file=2, screen=True)
    king_idx = _idx(support, 2, 0)
    assert engine.is_square_attacked(pos, king_idx, 0) is True  # cannon attacks the square behind 1 screen
    pos0 = _cannon_position(engine, enemy_file=1, screen=False)
    assert engine.is_square_attacked(pos0, _idx(support, 1, 0), 0) is False  # 0 screens
    pos2 = _cannon_position(engine, enemy_file=4, screen=True, extra_screens=(2,))
    assert engine.is_square_attacked(pos2, _idx(support, 4, 0), 0) is False  # 2 screens


# ---------------------------------------------------------------- castling


def _castling_position(engine, side=0):
    support = engine.support
    n = support.board_size
    rank = 0 if side == 0 else n - 1
    king = Piece(side, "K", "K")
    rook = Piece(side, "R", "R")
    pieces = [
        (_idx(support, 4, rank), king),
        (_idx(support, 7, rank), rook),
        (_idx(support, 3, n - 1 - rank), Piece(1 - side, "K", "K")),
    ]
    return _with_pieces(support, pieces, side=side)


def test_castling_compound_move_and_right_lifecycle():
    engine = _engine(castling_ruleset())
    support = engine.support
    pos = _castling_position(engine, side=0)
    from generic_chess.core.semantic_executor import SemanticAction

    actions = engine.legal_actions(pos)
    castle = [
        a for a in actions if a.pattern_id == "sem_00_king_side_shift"
    ]
    assert castle, "castle action must be legal"
    assert castle[0].source == _idx(support, 4, 0)
    assert castle[0].target == _idx(support, 6, 0)
    # Ordinary king movement preserved (anchor patterns exist).
    pattern_by_id = {p.pattern_id: p for p in engine.ir.patterns}
    assert any(
        a.pattern_id.startswith("legacy_") and "K" in pattern_by_id[a.pattern_id].type_ids
        for a in actions
    )
    child = engine.apply(pos, castle[0])
    assert child.board[_idx(support, 6, 0)] is not None
    assert child.board[_idx(support, 5, 0)] is not None  # rook moved to f1
    assert child.board[_idx(support, 4, 0)] is None
    assert child.board[_idx(support, 7, 0)] is None
    # Right for side 0 is consumed.
    assert dict(child.aux_state).get(0, 1) == 0
    # Replacement rook at h1 cannot restore the right.
    later = _with_pieces(support, [
        (_idx(support, 6, 0), Piece(0, "K", "K")),
        (_idx(support, 5, 0), Piece(0, "R", "R")),
        (_idx(support, 7, 0), Piece(0, "R", "R")),
        (_idx(support, 3, 7), Piece(1, "K", "K")),
    ], side=0)
    later = Position(
        board=later.board,
        hands=later.hands,
        side_to_move=0,
        ruleset_fingerprint=later.ruleset_fingerprint,
        aux_state=((0, 0),),
    )
    assert not [a for a in engine.legal_actions(later) if a.pattern_id == "sem_00_king_side_shift"]


def test_castling_blocked_when_transit_attacked():
    engine = _engine(castling_ruleset())
    support = engine.support
    pos = _castling_position(engine, side=0)
    # Enemy rook on the 1-file attacking f1 (rank 0 file 5).
    board = list(pos.board)
    board[_idx(support, 5, 7)] = Piece(1, "R", "R")
    attacked = Position(
        board=tuple(board), hands=pos.hands, side_to_move=0,
        ruleset_fingerprint=pos.ruleset_fingerprint, aux_state=pos.aux_state,
    )
    assert not [
        a for a in engine.legal_actions(attacked)
        if a.pattern_id == "sem_00_king_side_shift"
    ]


# ---------------------------------------------------------------- en passant


def test_en_passant_token_and_off_target_capture():
    engine = _engine(en_passant_ruleset())
    support = engine.support
    token_slot = next(s.slot_id for s in engine.ir.aux_slots if s.value_kind == "square_or_none")
    white = Piece(0, "P", "P")
    black = Piece(1, "P", "P")
    pos = _with_pieces(support, [
        (_idx(support, 4, 1), white),  # e2
        (_idx(support, 3, 3), black),  # d4
        (_idx(support, 3, 7), Piece(1, "K", "K")),
        (_idx(support, 4, 0), Piece(0, "K", "K")),
    ], side=0)
    from generic_chess.core.semantic_executor import SemanticAction

    double = [
        a for a in engine.legal_actions(pos)
        if a.pattern_id == "sem_00_double_step_creates_token"
    ]
    assert double, "double-step must be legal"
    assert double[0].target == _idx(support, 4, 3)  # e4
    child = engine.apply(pos, double[0])
    # Token == landing square e3 = (4, 2).
    assert dict(child.aux_state).get(token_slot) == (4, 2)
    assert child.side_to_move == 1
    # Black EP capture: landing e3 empty, victim e4 removed off-target.
    ep = [
        a for a in engine.legal_actions(child)
        if a.pattern_id.startswith("sem_") and "capture" in a.pattern_id
    ]
    assert ep, "EP capture must be legal"
    assert ep[0].target == _idx(support, 4, 2)  # landing e3 empty
    grandchild = engine.apply(child, ep[0])
    assert grandchild.board[_idx(support, 4, 3)] is None  # victim e4 removed
    assert grandchild.board[_idx(support, 4, 2)] is not None  # black pawn on e3
    assert dict(grandchild.aux_state).get(token_slot) is None  # token cleared


def test_en_passant_token_expires_after_one_turn():
    engine = _engine(en_passant_ruleset())
    support = engine.support
    token_slot = next(s.slot_id for s in engine.ir.aux_slots if s.value_kind == "square_or_none")
    white = Piece(0, "P", "P")
    pos = _with_pieces(support, [
        (_idx(support, 4, 1), white),
        (_idx(support, 3, 7), Piece(1, "K", "K")),
        (_idx(support, 4, 0), Piece(0, "K", "K")),
    ], side=0)
    from generic_chess.core.semantic_executor import SemanticAction

    double = next(
        a for a in engine.legal_actions(pos)
        if a.pattern_id == "sem_00_double_step_creates_token"
    )
    child = engine.apply(pos, double)
    assert dict(child.aux_state).get(token_slot) == (4, 2)
    # Black makes any move: token expires next turn.
    black_move = engine.legal_actions(child)[0]
    grandchild = engine.apply(child, black_move)
    assert dict(grandchild.aux_state).get(token_slot) is None


def test_en_passant_both_owners():
    engine = _engine(en_passant_ruleset())
    support = engine.support
    n = support.board_size
    # Mirrored board: black double-steps downward, white captures upward.
    white = Piece(0, "P", "P")
    black = Piece(1, "P", "P")
    pos = _with_pieces(support, [
        (_idx(support, 4, n - 2), black),
        (_idx(support, 3, n - 4), white),
        (_idx(support, 4, n - 1), Piece(0, "K", "K")),
        (_idx(support, 3, 0), Piece(1, "K", "K")),
    ], side=1)
    from generic_chess.core.semantic_executor import SemanticAction

    double = [
        a for a in engine.legal_actions(pos)
        if a.pattern_id == "sem_00_double_step_creates_token"
    ]
    assert double
    child = engine.apply(pos, double[0])
    ep = [
        a for a in engine.legal_actions(child)
        if a.pattern_id.startswith("sem_") and "capture" in a.pattern_id
    ]
    assert ep, "white EP capture must be legal in the mirrored setup"


# ---------------------------------------------------------------- nifu


def test_nifu_drop_guard_semantics():
    engine = _engine(nifu_ruleset())
    support = engine.support
    pawn = Piece(0, "P", "P")
    promoted = Piece(0, "P", "TP", promoted=True)
    pos = Position(
        board=tuple([None] * (support.board_size * support.board_size)),
        hands=(Hands((("P", 1),)), Hands.empty()),
        side_to_move=0,
        ruleset_fingerprint=support.ruleset_fingerprint,
        aux_state=(),
    )
    board = list(pos.board)
    board[_idx(support, 4, 0)] = pawn  # unpromoted P on file 4
    pos = Position(
        board=tuple(board), hands=pos.hands, side_to_move=0,
        ruleset_fingerprint=pos.ruleset_fingerprint, aux_state=(),
    )
    drops = [
        a for a in engine.legal_actions(pos)
        if a.pattern_id == "sem_00_drop_file_occupancy_guard"
    ]
    assert not [d for d in drops if d.target % support.board_size == 4], (
        "drop on occupied file must be blocked (nifu)"
    )
    assert [d for d in drops if d.target % support.board_size == 3], (
        "drop on other files must be legal"
    )
    # Promoted piece on the file does NOT block the drop.
    board2 = list(pos.board)
    board2[_idx(support, 4, 0)] = promoted
    pos2 = Position(
        board=tuple(board2), hands=pos.hands, side_to_move=0,
        ruleset_fingerprint=pos.ruleset_fingerprint, aux_state=(),
    )
    drops2 = [
        a for a in engine.legal_actions(pos2)
        if a.pattern_id == "sem_00_drop_file_occupancy_guard"
    ]
    assert [d for d in drops2 if d.target % support.board_size == 4], (
        "promoted piece must not trigger nifu"
    )


# ---------------------------------------------------------------- legacy differential


def _legacy_actions_set(compiled, position):
    from generic_chess.core.actions import BoardMove, DropMove

    out = set()
    for action in legal_actions_from_position(position, compiled):
        if isinstance(action, BoardMove):
            out.add(
                (
                    "board",
                    action.from_square.file,
                    action.from_square.rank,
                    action.to_square.file,
                    action.to_square.rank,
                    action.promotion_target_id,
                )
            )
        else:
            out.add(("drop", action.base_type_id, action.to_square.file, action.to_square.rank))
    return out


def _semantic_actions_set(engine, position):
    from generic_chess.core.coordinates import index_to_square

    out = set()
    for action in engine.legal_actions(position):
        if action.source is None:
            pattern = next(
                p for p in engine.ir.patterns if p.pattern_id == action.pattern_id
            )
            base = pattern.effects[0].piece_type_ref.type_id
            sq = index_to_square(action.target, engine.support.board_size)
            out.add(("drop", base, sq.file, sq.rank))
        else:
            from_sq = index_to_square(action.source, engine.support.board_size)
            to_sq = index_to_square(action.target, engine.support.board_size)
            out.add(
                (
                    "board",
                    from_sq.file,
                    from_sq.rank,
                    to_sq.file,
                    to_sq.rank,
                    action.promotion_target_id,
                )
            )
    return out


def test_legacy_differential_legal_actions():
    from generic_chess.ai.benchmark.audit_suite import (
        build_compiled,
        standard_ruleset_specs,
    )
    from generic_chess.core.transition import _transition, initial_state

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    corpus = [
        build_compiled(specs["gen_classic_like_4_101"]),
        build_compiled(specs["gen_free_random_4_102"]),
    ]
    for compiled in corpus:
        ir = lower_legacy_to_ir(compiled)
        support = _build_semantic_support(compiled)
        semantic = CompiledSemanticRuleset(ir=ir, _legacy_compiled=compiled, support=support)
        engine = SemanticEngine(semantic)
        state = initial_state(compiled)
        # Initial + a few deterministic random plies.
        import random

        rng = random.Random(1234)
        positions = [state.position]
        for _ in range(6):
            legal = legal_actions_from_position(state.position, compiled)
            if not legal:
                break
            action = sorted(legal, key=str)[rng.randrange(len(legal))]
            state = _transition(state, action, compiled)
            positions.append(state.position)
        for position in positions:
            legacy = _legacy_actions_set(compiled, position)
            semantic_set = _semantic_actions_set(engine, position)
            assert legacy == semantic_set, (
                compiled.ruleset_fingerprint,
                position_key(position, compiled),
            )


def test_aux_state_participates_in_semantic_identity_not_legacy_key():
    from generic_chess.learning.shogi_rules import build_shogi_ruleset

    compiled = compile_ruleset(build_shogi_ruleset())
    support = _build_semantic_support(compiled)
    state = initial_state(compiled)
    p0 = state.position
    p1 = Position(
        board=p0.board,
        hands=p0.hands,
        side_to_move=p0.side_to_move,
        ruleset_fingerprint=p0.ruleset_fingerprint,
        aux_state=((0, 1),),
    )
    # Legacy identity ignores aux (historical keys stable).
    assert position_key(p0, compiled) == position_key(p1, compiled)
    # Semantic identity includes aux.
    assert semantic_position_key(p0, support) != semantic_position_key(p1, support)
    assert semantic_position_key(p0, support) == semantic_position_key(p0, support)
