from __future__ import annotations

from dataclasses import replace

import numpy as np

from generic_chess import compile_ruleset_for_execution
from generic_chess.core.identity import position_identity_key
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.session import GameSession
from generic_chess.session.serialization import deserialize_game_record, serialize_game_record
from tests.test_f24c_mixed_mechanic_certification import A0, A1, H0, _mixed_ruleset, _position

from scripts.f133_shogi_resource_transition_action_semantics import (
    _microtests,
    _rename_ruleset,
    _resource_classes,
    _resource_transition,
)


def test_resource_classes_are_structural_and_type_rename_invariant():
    original = compile_semantic_ruleset(build_standard_shogi_ruleset())
    renamed = compile_semantic_ruleset(_rename_ruleset(build_standard_shogi_ruleset()))
    left = _resource_classes(original)
    right = _resource_classes(renamed)
    assert len(left["classes"]) == 7
    assert [item["signature_sha256"] for item in left["classes"]] == [item["signature_sha256"] for item in right["classes"]]


def test_mixed_capture_drop_and_promoted_capture_use_authoritative_hand_delta():
    compiled = compile_semantic_ruleset(_mixed_ruleset())
    classes = _resource_classes(compiled)
    engine = semantic_engine_for(compiled)
    anchors = [(0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))]
    root = _position(compiled, [(1, 1, Piece(0, A0, A0)), (2, 1, Piece(1, A0, A0)), *anchors], hands=([(A0, 1)], ()))
    actions = engine.legal_actions(root)
    capture = next(action for action in actions if "capture_A0_A0" in action.pattern_id)
    drop = next(action for action in actions if action.source is None and action.actor_type == A0)
    capture_delta = _resource_transition(root, engine.apply(root, capture), classes)
    drop_delta = _resource_transition(root, engine.apply(root, drop), classes)
    assert np.max(capture_delta) == 1.0
    assert np.min(drop_delta) == -1.0

    promoted_root = _position(compiled, [(1, 1, Piece(0, A0, A0)), (2, 1, Piece(1, A0, A1, promoted=True)), *anchors], hands=([(A0, 1)], ()))
    promoted_capture = next(action for action in engine.legal_actions(promoted_root) if "capture_A0_A0" in action.pattern_id)
    assert np.max(_resource_transition(promoted_root, engine.apply(promoted_root, promoted_capture), classes)) == 1.0


def test_capture_to_hand_can_be_reentered_by_same_owner_after_turn_cycle_and_replay():
    ruleset = build_standard_shogi_ruleset()
    rows = [[None for _ in range(9)] for _ in range(9)]
    rows[0][4] = Piece(0, "K", "K")
    rows[8][4] = Piece(1, "K", "K")
    rows[3][3] = Piece(0, "S", "S")
    rows[4][4] = Piece(1, "G", "G")
    ruleset = replace(ruleset, initial_position=tuple(tuple(row) for row in rows))
    compiled = compile_ruleset_for_execution(ruleset)
    session = GameSession(compiled)

    # Negative control: without a captured/held gold, no gold drop is executable.
    assert not any(
        getattr(action, "base_type_id", None) == "G"
        for action in session.legal_actions()
    )
    initial_total = sum(piece is not None for piece in session.state.position.board)
    initial_identity = position_identity_key(session.state.position, compiled)

    capture = next(
        action
        for action in session.legal_actions()
        if action.from_square.rank * 9 + action.from_square.file == 30
        and action.to_square.rank * 9 + action.to_square.file == 40
    )
    captured = session.submit(capture)
    assert captured.position.side_to_move == 1
    assert captured.position.hands[0].count("G") == 1
    assert captured.position.board[40] == Piece(0, "S", "S")
    assert captured.position.board[30] is None
    assert sum(piece is not None for piece in captured.position.board) + sum(
        hand.total() for hand in captured.position.hands
    ) == initial_total
    capture_identity = position_identity_key(captured.position, compiled)
    assert capture_identity != initial_identity

    # The opponent completes a legal turn; the capturer then drops that resource.
    reply = next(
        action for action in session.legal_actions()
        if action.from_square.rank * 9 + action.from_square.file == 76
        and action.to_square.rank * 9 + action.to_square.file == 75
    )
    replied = session.submit(reply)
    assert replied.position.side_to_move == 0
    reply_identity = position_identity_key(replied.position, compiled)
    drop = next(
        action
        for action in session.legal_actions()
        if getattr(action, "base_type_id", None) == "G"
        and action.to_square.rank * 9 + action.to_square.file == 50
    )
    dropped = session.submit(drop)
    assert dropped.position.hands[0].count("G") == 0
    assert dropped.position.board[50] == Piece(0, "G", "G")
    assert sum(piece is not None for piece in dropped.position.board) + sum(
        hand.total() for hand in dropped.position.hands
    ) == initial_total
    assert capture_identity != reply_identity
    assert reply_identity != position_identity_key(dropped.position, compiled)

    encoded = serialize_game_record(session.to_record())
    replayed = GameSession.replay(compiled, deserialize_game_record(encoded))
    assert replayed.state == session.state
    assert tuple(record.action for record in replayed.history) == (capture, reply, drop)


def test_western_rules_have_no_reusable_resource_transition_classes():
    from generic_chess.rules.western_chess import build_western_chess_ruleset
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    classes = _resource_classes(compiled)
    assert classes["classes"] == []
    position = initial_state(compiled).position
    assert _resource_transition(position, position, classes).shape == (0,)


def test_genericity_microtests_pass():
    report = _microtests()
    assert report["pass"] is True
