"""F24G provenance correction, missing direct evidence, and canonical perft."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from generic_chess.core.identity import position_identity_key
from generic_chess.core.pieces import Piece
from generic_chess.core.position import GameState
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_public_actions
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider

from scripts.audit_f24f_western_chess_perft import (
    compiled_western_chess,
    position_from_fen,
    standard_engine,
)
from scripts.audit_f24g_canonical_western_perft import (
    CANONICAL_CORPUS,
    F24F_FENS,
    canonical_manifest,
    canonical_manifest_sha256,
    f24f_artifact_sha256,
    loader_sanity,
    progressive_canonical_perft,
)


ROOT = Path(__file__).resolve().parents[1]


def _internal(engine, position, source, target, *, name=None):
    return next(
        action for action in engine.legal_actions(position)
        if action.source == source and action.target == target
        and (name is None or name in action.pattern_id)
        and action.promotion_target_id is None
    )


def _state(position, compiled):
    key = position_identity_key(position, compiled)
    return GameState(
        position=position, ply_count=0, repetition_counts=((key, 1),),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )


def test_f24g_preserves_f24f_artifacts_and_canonical_manifest():
    assert f24f_artifact_sha256(ROOT) == {
        "scripts/audit_f24f_western_chess_perft.py": "a6edda3bcf043103fa036f1095aebc2fb22174b499eb0b3a7a646fcffae7b8fa",
        "tests/test_f24f_western_chess_perft.py": "af946ffb9a6954e8d982d67c826d91ad7239aee6f8301b9eca38eb98191b1275",
        "tests/fixtures/f24f_western_chess_perft.json": "38f709af51cbe9ae9a4ceb0e746b5dcb879cb592aca16d387ca59126ff452802",
        "docs/architecture/ADR-082-western-chess-perft-certification.md": "f09a0b49f036bc26e6e16a6215ebc54e04ed371708a3f89b18fa38f45fe116ea",
    }
    assert [row["fen"] for row in canonical_manifest()] == [fen for _label, fen, _expected in CANONICAL_CORPUS]
    assert canonical_manifest_sha256() == "62b680de5ca316d6e5264a2ca35cc4207971fb5aed72f9af3146850f25e59123"


def test_f24g_loader_sanity_and_expected_f24f_error_classification():
    compiled = compiled_western_chess()
    sanity = loader_sanity(compiled)
    assert [row["label"] for row in sanity] == [label for label, _fen, _expected in CANONICAL_CORPUS]
    assert [row["side"] for row in sanity] == [0, 0, 0, 0, 0, 0]
    f24f_fixture = json.loads(
        (ROOT / "tests/fixtures/f24f_western_chess_perft.json").read_text(encoding="utf-8")
    )
    assert f24f_fixture["status"] == "FIRST_MISMATCH"
    assert f24f_fixture["actual"] == 45 and f24f_fixture["expected"] == 48
    assert F24F_FENS["kiwipete"] == f24f_fixture["fen"]
    assert NativeSemanticLegalityProvider.try_create(compiled) is None


def test_f24g_en_passant_discovered_line_and_safe_control():
    compiled, engine = standard_engine()
    unsafe = position_from_fen("4r1k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1", compiled)
    assert not any("en_passant" in action.pattern_id for action in engine.legal_actions(unsafe))
    safe = position_from_fen("6k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1", compiled)
    assert any("en_passant" in action.pattern_id for action in engine.legal_actions(safe))


def test_f24g_castling_rights_loss_after_king_and_rook_round_trips():
    compiled, engine = standard_engine()
    base = position_from_fen("7k/8/8/8/8/8/8/R3K2R w KQ - 0 1", compiled)
    king_out = _internal(engine, base, 4, 5, name="k_quiet")
    after_king = engine.apply(base, king_out)
    black_move = _internal(engine, after_king, 63, 62, name="k_quiet")
    after_black = engine.apply(after_king, black_move)
    king_back = _internal(engine, after_black, 5, 4, name="k_quiet")
    after_return = engine.apply(after_black, king_back)
    rights = dict(after_return.aux_state)
    assert rights[(3, -1)] == 0 and rights[(4, -1)] == 0
    assert not any("castle_w_" in action.pattern_id for action in engine.legal_actions(after_return))

    rook_out = _internal(engine, base, 7, 15, name="r_quiet")
    after_rook = engine.apply(base, rook_out)
    black_move = _internal(engine, after_rook, 63, 62, name="k_quiet")
    after_black = engine.apply(after_rook, black_move)
    rook_back = _internal(engine, after_black, 15, 7, name="r_quiet")
    after_rook_return = engine.apply(after_black, rook_back)
    rights = dict(after_rook_return.aux_state)
    assert rights[(3, -1)] == 0 and rights[(4, -1)] == 1


def test_f24g_original_rook_capture_and_replacement_does_not_restore_right():
    compiled, engine = standard_engine()
    position = position_from_fen("k7/8/8/8/8/8/6b1/4K2R b KQ - 0 1", compiled)
    capture = _internal(engine, position, 14, 7, name="b_capture")
    child = engine.apply(position, capture)
    rights = dict(child.aux_state)
    assert rights[(3, -1)] == 0
    board = list(child.board)
    board[7] = Piece(0, "R", "R")
    replacement = replace(child, board=tuple(board), side_to_move=0)
    assert not any("castle_w_ks" in action.pattern_id for action in engine.legal_actions(replacement))


def test_f24g_terminal_king_adjacency_and_search_runtime_special_move():
    compiled, engine = standard_engine()
    checkmate = position_from_fen("7k/6Q1/5K2/8/8/8/8/8 b - - 0 1", compiled)
    key = position_identity_key(checkmate, compiled)
    result = engine.terminal_result(checkmate, 0, ((key, 1),))
    assert result.status is TerminalStatus.CHECKMATE
    stalemate = position_from_fen("7k/5Q2/5K2/8/8/8/8/8 b - - 0 1", compiled)
    key = position_identity_key(stalemate, compiled)
    result = engine.terminal_result(stalemate, 0, ((key, 1),))
    assert result.status is TerminalStatus.STALEMATE
    adjacent = position_from_fen("8/8/8/8/8/8/4k3/4K3 w - - 0 1", compiled)
    assert not any(
        action.actor_type == "K" and abs(action.target - action.source) <= 9
        for action in engine.legal_actions(adjacent)
    )
    castle_position = position_from_fen("7k/8/8/8/8/8/8/R3K2R w K - 0 1", compiled)
    runtime = SearchPathRuntime.from_state(_state(castle_position, compiled), compiled)
    castle = next(action for action in runtime.legal_actions() if "castle_w_ks" in action.pattern_id)
    before = runtime.position
    runtime.push(castle)
    runtime.pop()
    runtime.assert_balanced()
    assert runtime.position == before


def test_f24g_ruleset_round_trip_keeps_canonical_initial_actions():
    ruleset = __import__(
        "scripts.audit_f24f_western_chess_perft", fromlist=["western_chess_ruleset"]
    ).western_chess_ruleset()
    first = compile_semantic_ruleset(ruleset)
    second = compile_semantic_ruleset(deserialize_ruleset(serialize_ruleset(ruleset)))
    first_engine, second_engine = standard_engine()[1], __import__(
        "generic_chess.core.semantic_executor", fromlist=["semantic_engine_for"]
    ).semantic_engine_for(second)
    assert semantic_public_actions(first_engine, first_engine._initial_position()) == semantic_public_actions(
        second_engine, second_engine._initial_position()
    )


def test_f24g_canonical_perft_one_shot():
    outcome = progressive_canonical_perft()
    assert outcome["status"] == "PASS", outcome
    fixture = json.loads(
        (ROOT / "tests/fixtures/f24g_canonical_western_perft.json").read_text(encoding="utf-8")
    )
    assert fixture["status"] == "PASS"
    assert fixture["canonical_manifest_sha256"] == canonical_manifest_sha256()
    assert all(row["actual"] == row["expected"] for row in fixture["results"])
    assert fixture["next_boundary"] == "F24H_WESTERN_CHESS_RULESET_PRODUCTIZATION_AND_REFERENCE_SEARCH_BASELINE"
