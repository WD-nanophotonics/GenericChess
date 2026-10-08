"""Semantic type transitions must survive a fresh Native root import."""
from dataclasses import replace

import pytest

from generic_chess.core.pieces import Piece
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.mirror import NativeSemanticPositionMirror, snapshot_matches
from generic_chess.native.semantic import guarded_actions, pack_position
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import weird_rulesets

pytestmark = pytest.mark.skipif(not native_available(), reason="native unavailable")


def transformed_root(*, self_promotion=False, capture_route=False):
    definition = weird_rulesets()[2]
    board = [list(row) for row in definition.initial_position]
    board[1][0] = Piece(0, "R", "R")
    if capture_route:
        board[2][2] = Piece(1, "R", "R")
        definition = replace(definition, drop_allowed={
            **definition.drop_allowed, "R": ((True,) * 64,) * 2})
    if self_promotion:
        action = definition.semantic_actions[0]
        action = replace(action, promotion_mode="explicit", explicit_promotion_type="R",
                         effects=tuple(e for e in action.effects if e.kind != "set_current_type"))
        definition = replace(definition, semantic_actions=(action,))
    compiled = compile_ruleset_for_execution(replace(
        definition, initial_position=tuple(map(tuple, board))))
    session = GameSession(compiled)
    rules = compile_native_semantic_rules(compiled)
    carried = NativeSemanticPositionMirror.from_state(
        compiled, rules, session.state, history_certified=True)
    action, = [a for a in session.legal_actions()
               if a.pattern_id.startswith("sem_")
               and (a.to_square.file, a.to_square.rank) == (1, 2)]
    carried.push(action, session.state.position)
    session.submit(action)
    return compiled, rules, session, carried


def test_legal_explicit_type_change_survives_fresh_native_root():
    compiled, rules, session, carried = transformed_root()
    piece = session.state.position.board[17]
    assert (piece.base_type_id, piece.current_type_id, piece.promoted) == (
        "R", "TP", True)
    assert not compiled.types_by_id["R"].is_promotable
    assert snapshot_matches(carried.snapshot(), session.state.position, rules, compiled)
    fresh = NativeSemanticPositionMirror.from_state(
        compiled, rules, session.state, history_certified=True)
    assert fresh.snapshot() == carried.snapshot()
    assert guarded_actions(rules, fresh.position) == guarded_actions(rules, carried.position)


def test_explicit_self_promotion_survives_fresh_native_root():
    compiled, rules, session, carried = transformed_root(self_promotion=True)
    assert session.state.position.board[17] == Piece(0, "R", "R", True)
    assert snapshot_matches(carried.snapshot(), session.state.position, rules, compiled)
    fresh = NativeSemanticPositionMirror.from_state(
        compiled, rules, session.state, history_certified=True)
    assert fresh.snapshot() == carried.snapshot()
    assert guarded_actions(rules, fresh.position) == guarded_actions(rules, carried.position)


def test_explicit_anchor_type_change_preserves_anchor_and_fresh_root():
    definition = weird_rulesets()[2]
    king = next(t for t in definition.piece_types if t.type_id == "K")
    action = definition.semantic_actions[0]
    effects = tuple(replace(e, type_ref=replace(e.type_ref, type_id="K2"))
                    if e.kind == "set_current_type" else e for e in action.effects)
    definition = replace(definition,
        piece_types=(*definition.piece_types, replace(king, type_id="K2", name="K2")),
        semantic_actions=(replace(action, type_ids=("K",), effects=effects),))
    compiled = compile_ruleset_for_execution(definition)
    session = GameSession(compiled)
    rules = compile_native_semantic_rules(compiled)
    carried = NativeSemanticPositionMirror.from_state(
        compiled, rules, session.state, history_certified=True)
    action, = [a for a in session.legal_actions() if a.pattern_id.startswith("sem_")]
    carried.push(action, session.state.position)
    session.submit(action)
    assert session.state.position.board[9] == Piece(0, "K", "K2", True)
    assert compiled.types_by_id["K2"].is_anchor
    fresh = NativeSemanticPositionMirror.from_state(
        compiled, rules, session.state, history_certified=True)
    assert fresh.snapshot() == carried.snapshot()
    assert guarded_actions(rules, fresh.position) == guarded_actions(rules, carried.position)


def test_semantic_pack_rejects_changed_current_with_false_flag():
    compiled, rules, _, _ = transformed_root()
    ids = {name: i for i, name in enumerate(rules.type_ids)}
    board = [None] * compiled.board_shape.area
    board[17] = [ids["R"], ids["TP"], 0, 0]
    with pytest.raises(ValueError, match="rejected payload"):
        pack_position(rules, {"board": board, "hands": [[0] * len(ids)] * 2,
                              "side": 0, "ply": 0, "aux_state": ()})


def test_transformed_capture_resets_base_identity_then_drop_restarts_exactly():
    compiled, rules, session, carried = transformed_root(capture_route=True)
    # Native carried state and fresh imports must agree across the actual
    # transformation -> capture -> reply -> drop history, not fabricated hands.
    for target in ((1, 2), (0, 1), (3, 3)):
        fresh = NativeSemanticPositionMirror.from_state(
            compiled, rules, session.state, history_certified=True)
        assert fresh.snapshot() == carried.snapshot()
        assert guarded_actions(rules, fresh.position) == guarded_actions(rules, carried.position)
        actions = [a for a in session.legal_actions()
                   if (a.to_square.file, a.to_square.rank) == target]
        if target == (1, 2):
            actions = [a for a in actions if a.actor_type_id == "R"]
        if target == (3, 3):
            actions = [a for a in actions if getattr(a, "base_type_id", None) == "R"]
        action, = actions
        carried.push(action, session.state.position)
        session.submit(action)
        assert snapshot_matches(carried.snapshot(), session.state.position, rules, compiled)
        if target == (1, 2):
            assert session.state.position.hands[1].count("R") == 1
            assert session.state.position.hands[1].count("TP") == 0
    assert session.state.position.board[27] == Piece(1, "R", "R", False)
    assert session.state.position.hands[1].count("R") == 0
    fresh = NativeSemanticPositionMirror.from_state(
        compiled, rules, session.state, history_certified=True)
    assert fresh.snapshot() == carried.snapshot()
    assert fresh.snapshot()["history_events_exact"]
    assert fresh.snapshot()["history_events"] == tuple(
        (255 if h.actor < 0 else h.actor, h.gave_check) for h in session.state.history)


def test_fresh_root_preserves_actual_check_event():
    definition = weird_rulesets()[2]
    board = [list(row) for row in definition.initial_position]
    board[1][0] = Piece(0, "R", "R")
    compiled = compile_ruleset_for_execution(replace(
        definition, initial_position=tuple(map(tuple, board))))
    session = GameSession(compiled)
    rules = compile_native_semantic_rules(compiled)
    carried = NativeSemanticPositionMirror.from_state(
        compiled, rules, session.state, history_certified=True)
    action, = [a for a in session.legal_actions()
               if (a.to_square.file, a.to_square.rank) == (7, 1)]
    carried.push(action, session.state.position)
    session.submit(action)
    assert session.state.history[-1].gave_check
    fresh = NativeSemanticPositionMirror.from_state(
        compiled, rules, session.state, history_certified=True)
    assert fresh.snapshot() == carried.snapshot()
    assert fresh.snapshot()["history_events_exact"]
    assert fresh.snapshot()["history_events"] == ((255, False), (0, True))


@pytest.mark.parametrize("native,broken", [(False, False), (True, False), (True, True)])
def test_public_decision_exposes_actual_legality_route(native, broken):
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits

    compiled, _, session, _ = transformed_root()
    player = AlphaBetaPlayer(compiled, use_disk_cache=False,
        use_native_semantic_legality=native, tuning=SearchTuning(use_root_tactical=False))
    if broken:
        def unavailable(*args):
            raise ValueError("simulated Native operational failure")
        player._native_legality_provider = unavailable
    decision = player.choose_action(session, SearchLimits(max_depth=1,
        max_nodes=128, max_time_seconds=3, quiescence_max_depth=0, quiescence_hard_max_depth=0))
    assert decision.action in session.legal_actions()
    assert decision.completed_depth == 1
    assert (decision.native_legality_calls > 0) == (native and not broken)
    assert decision.native_legality_fallbacks == int(broken)
    assert decision.native_legality_operational_failures == int(broken)


def test_fresh_roots_retain_actual_continuous_check_loss():
    from generic_chess.native.semantic import terminal_status
    from generic_chess.native.mirror import _position_payload

    definition = weird_rulesets()[2]
    board = [list(row) for row in definition.initial_position]
    board[6][6] = Piece(0, "R", "R")
    compiled = compile_ruleset_for_execution(replace(definition,
        initial_position=tuple(map(tuple, board)), repetition_limit=3,
        repetition_policy="continuous_check_loss"))
    session = GameSession(compiled)
    rules = compile_native_semantic_rules(compiled)
    carried = NativeSemanticPositionMirror.from_state(
        compiled, rules, session.state, history_certified=True)
    for target in ((7, 6), (6, 7), (6, 6), (7, 7)) * 2:
        action, = [a for a in session.legal_actions()
                   if (a.to_square.file, a.to_square.rank) == target]
        carried.push(action, session.state.position)
        session.submit(action)
        fresh = NativeSemanticPositionMirror.from_state(
            compiled, rules, session.state, history_certified=True)
        assert fresh.snapshot() == carried.snapshot()
        native = terminal_status(rules, fresh.position)
        assert (native["status"], native["winner"]) == (
            session.state.terminal_status.status.value, session.state.terminal_status.winner)
    assert session.state.terminal_status.status.value == "perpetual_check"
    assert session.state.terminal_status.winner == 1
    payload = _position_payload(compiled, rules, session.state)
    payload["history"] = tuple(h[:4] for h in payload["history"])
    key_only = pack_position(rules, payload)
    with pytest.raises(ValueError, match="exact full history"):
        terminal_status(rules, key_only)
