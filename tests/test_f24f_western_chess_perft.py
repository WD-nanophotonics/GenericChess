"""F24F direct Western contracts and one-shot mandatory perft certification."""

from __future__ import annotations

import pytest

from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.core.coordinates import Square
from generic_chess.core.position import GameState
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for, semantic_public_actions
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider

from scripts.audit_f24f_western_chess_perft import (
    compiled_western_chess,
    perft,
    position_from_fen,
    root_divide,
    standard_engine,
    western_chess_ruleset,
)


def _internal(engine, position, source, target, *, name=None, promotion=None):
    return next(
        action for action in engine.legal_actions(position)
        if action.source == source and action.target == target
        and (name is None or name in action.pattern_id)
        and action.promotion_target_id == promotion
    )


def _position_state(position, compiled):
    from generic_chess.core.identity import position_identity_key

    key = position_identity_key(position, compiled)
    return GameState(
        position=position, ply_count=0, repetition_counts=((key, 1),),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )


def test_f24f_complete_shape_initial_legal_count_and_capture_disposition():
    compiled, engine = standard_engine()
    initial = engine._initial_position()
    assert len(engine.legal_actions(initial)) == 20
    board_captures = [
        pattern for pattern in engine._patterns
        if pattern.target.kind == "target_enemy"
        and pattern.pattern_id.startswith("legacy_")
    ]
    assert not board_captures
    for pattern in engine._patterns:
        if pattern.target.kind == "target_enemy" and pattern.pattern_id.startswith("sem_"):
            assert any(
                effect.kind == "remove" and effect.disposition == "remove_from_game"
                for effect in pattern.effects
            )
    assert NativeSemanticLegalityProvider.try_create(compiled) is not None


def test_f24f_pawn_contract_and_owner_mirror():
    compiled, engine = standard_engine()
    white = position_from_fen("4k3/8/8/8/8/8/P7/4K3 w - - 0 1", compiled)
    assert _internal(engine, white, 8, 16, name="pawn_one_step")
    assert _internal(engine, white, 8, 24, name="pawn_double_step")
    blocked = position_from_fen("4k3/8/8/8/8/N7/P7/4K3 w - - 0 1", compiled)
    assert not any(a.source == 8 for a in engine.legal_actions(blocked))
    non_start = position_from_fen("4k3/8/8/3P4/8/8/8/4K3 w - - 0 1", compiled)
    assert not any(a.source == 27 and a.target == 43 for a in engine.legal_actions(non_start))
    mixed = position_from_fen("4k3/8/8/3P4/8/8/P7/4K3 w - - 0 1", compiled)
    assert not any(a.source == 27 and a.target == 43 for a in engine.legal_actions(mixed))
    capture = position_from_fen("4k3/8/8/8/8/1n6/P7/4K3 w - - 0 1", compiled)
    assert not any(a.source == 8 and a.target == 9 for a in engine.legal_actions(capture))
    assert _internal(engine, capture, 8, 17, name="pawn_capture")
    black = position_from_fen("4k3/p7/8/8/8/8/8/4K3 b - - 0 1", compiled)
    assert _internal(engine, black, 8 * 6, 8 * 5, name="pawn_one_step")
    assert _internal(engine, black, 48, 32, name="pawn_double_step")


def test_f24f_promotion_variants_and_public_action_identity_round_trip():
    compiled, engine = standard_engine()
    quiet = position_from_fen("4k2r/P7/8/8/8/8/8/4K3 w - - 0 1", compiled)
    quiet_promotions = [
        a for a in engine.legal_actions(quiet)
        if a.source == 48 and a.target == 56
    ]
    assert {a.promotion_target_id for a in quiet_promotions} == {"Q", "R", "B", "N"}
    capture = position_from_fen("1n2k2r/P7/8/8/8/8/8/4K3 w - - 0 1", compiled)
    capture_promotions = [
        a for a in engine.legal_actions(capture)
        if a.source == 48 and a.target == 57
    ]
    assert {a.promotion_target_id for a in capture_promotions} == {"Q", "R", "B", "N"}
    public = semantic_public_actions(engine, quiet)
    sample = next(a for a in public if a.from_square == Square(0, 6) and a.to_square == Square(0, 7))
    assert action_from_dict(action_to_dict(sample)) == sample
    child = engine.apply(quiet, next(a for a in quiet_promotions if a.promotion_target_id == "Q"))
    promoted = child.board[56]
    assert promoted is not None and promoted.base_type_id == "P"
    assert promoted.current_type_id == "Q" and promoted.promoted


def test_f24f_en_passant_lifecycle_and_push_pop():
    compiled, engine = standard_engine()
    root = position_from_fen("7k/8/8/8/4p3/8/3P4/K7 w - - 0 1", compiled)
    double = _internal(engine, root, 11, 27, name="pawn_double_step")
    after_double = engine.apply(root, double)
    assert dict(after_double.aux_state)
    ep = _internal(engine, after_double, 28, 19, name="en_passant")
    after_ep = engine.apply(after_double, ep)
    assert after_ep.board[27] is None
    assert after_ep.board[19] is not None and after_ep.board[19].owner == 1
    assert all(hand.total() == 0 for hand in after_ep.hands)
    single = _internal(
        engine,
        root,
        11,
        19,
        name="pawn_one_step",
    )
    after_single = engine.apply(root, single)
    assert all(value is None or value == 0 for _key, value in after_single.aux_state)
    state = _position_state(root, compiled)
    runtime = SearchPathRuntime.from_state(state, compiled)
    before = runtime.position
    runtime.push(next(a for a in runtime.legal_actions() if a.from_square == Square(3, 1) and a.to_square == Square(3, 3)))
    runtime.pop()
    runtime.assert_balanced()
    assert runtime.position == before


def test_f24f_castling_rights_rook_presence_path_and_attack_safety():
    compiled, engine = standard_engine()
    base = position_from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", compiled)
    castles = [a for a in engine.legal_actions(base) if "castle_w" in a.pattern_id]
    assert len(castles) == 2
    king_side = next(a for a in castles if a.target == 6)
    child = engine.apply(base, king_side)
    assert child.board[6] is not None and child.board[5] is not None
    assert child.board[4] is None and child.board[7] is None
    rights = dict(child.aux_state)
    assert rights[(3, -1)] == 0
    assert rights[(4, -1)] == 0
    assert rights[(0, -1)] == 1 and rights[(1, -1)] == 1
    assert not any("castle_w_ks" in a.pattern_id for a in engine.legal_actions(child))
    assert not any("castle_w_ks" in a.pattern_id for a in engine.legal_actions(
        position_from_fen("r3k2r/8/8/8/8/8/8/R3K3 w KQkq - 0 1", compiled)
    ))
    assert not any("castle_w_ks" in a.pattern_id for a in engine.legal_actions(
        position_from_fen("r3k2r/8/8/8/8/8/8/R3KN1R w KQkq - 0 1", compiled)
    ))
    for rook_file in (4, 5, 6):
        black_row = ["1"] * 8
        black_row[rook_file] = "r"
        black_row[0] = "k"
        attacked = position_from_fen(
            f"{''.join(black_row)}/8/8/8/8/8/8/R3K2R w K - 0 1",
            compiled,
        )
        assert not any("castle_w_ks" in a.pattern_id for a in engine.legal_actions(attacked))
    assert any("castle_w_ks" in a.pattern_id for a in engine.legal_actions(base))


def test_f24f_ruleset_round_trip_fingerprint_and_subject_refs():
    ruleset = western_chess_ruleset()
    compiled = compile_semantic_ruleset(ruleset)
    restored = compile_semantic_ruleset(deserialize_ruleset(serialize_ruleset(ruleset)))
    assert restored.ruleset_fingerprint == compiled.ruleset_fingerprint
    assert any(
        guard.subject_ref is not None
        for pattern in restored.ir.patterns
        for guard in pattern.guards
    )
    original_engine = semantic_engine_for(compiled)
    restored_engine = semantic_engine_for(restored)
    assert semantic_public_actions(original_engine, original_engine._initial_position()) == semantic_public_actions(
        restored_engine, restored_engine._initial_position()
    )


def test_f24f_fen_loader_and_action_round_trip_are_deterministic():
    compiled, engine = standard_engine()
    fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    first = position_from_fen(fen, compiled)
    second = position_from_fen(fen, compiled)
    assert first == second
    actions = semantic_public_actions(engine, first)
    assert tuple(action_from_dict(action_to_dict(a)) for a in actions) == actions


def test_f24f_mandatory_perft_one_shot():
    compiled, engine = standard_engine()
    cases = (
        ("initial", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", (20, 400, 8902, 197281)),
        ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/2pP4/1p2P3/2N2N2/PPQBBPPP/R3K2R w KQkq - 0 1", (48, 2039, 97862)),
        ("position-3", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", (14, 191, 2812, 43238)),
        ("position-4", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P1PPP/R2Q1RK1 w kq - 0 1", (6, 264, 9467)),
        ("position-5", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", (44, 1486, 62379)),
        ("position-6", "r4rk1/1pp1qppp/p1np1n2/2b1p3/2B1P1b1/P1NP1N2/1PP1QPPP/R1B2RK1 w - - 0 10", (46, 2079, 89890)),
    )
    for label, fen, expected in cases:
        position = position_from_fen(fen, compiled)
        for depth, wanted in enumerate(expected, 1):
            actual = perft(engine, position, depth)
            if actual != wanted:
                divide = root_divide(engine, position, depth - 1)
                pytest.fail(
                    f"first F24F mismatch label={label} depth={depth} "
                    f"actual={actual} expected={wanted} divide={divide}"
                )
