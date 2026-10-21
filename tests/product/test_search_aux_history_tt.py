from dataclasses import replace

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import SemanticBoardMove
from generic_chess.core.coordinates import Square
from generic_chess.core.identity import search_state_identity
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleActionEffect, RuleAuxState, RuleGeometrySpec, RuleInvariant,
    RuleSemanticAction, RuleSquareRef,
)
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import (
    deserialize_game_record, serialize_game_record,
)
from rule_semantics_ir_fixtures import _king_type, _semantic_ruleset


def _aux_history_rules():
    writer = RuleSemanticAction(
        name="write_flag",
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)),
        target_relation="empty",
        composition="augment",
        aux_state=(RuleAuxState("flag", "bool", "global", "persistent", 0),),
        effects=(
            RuleActionEffect("move", from_ref=RuleSquareRef("source"),
                             to_ref=RuleSquareRef("target")),
            RuleActionEffect("set_bool", slot_name="flag", value=1),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    returner = RuleSemanticAction(
        name="return",
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(-1, 0)),
        target_relation="empty",
        composition="augment",
        effects=(RuleActionEffect("move", from_ref=RuleSquareRef("source"),
                                  to_ref=RuleSquareRef("target")),),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    rows = [[None] * 5 for _ in range(5)]
    rows[0][0] = Piece(0, "K", "K")
    rows[4][4] = Piece(1, "K", "K")
    rows[1][1] = Piece(0, "A", "A")
    rules = _semantic_ruleset((_king_type(), PieceType("A", "A", ())),
                              (writer, returner), n=5,
                              rows=tuple(tuple(row) for row in rows))
    return compile_semantic_ruleset(rules)


def _move(session, source, target):
    action = next(a for a in session.legal_actions()
                  if isinstance(a, SemanticBoardMove)
                  and a.from_square == source and a.to_square == target)
    session.submit(action)


def _same_board_flag_written(compiled):
    session = GameSession(compiled)
    _move(session, Square(1, 1), Square(2, 1))
    _move(session, Square(4, 4), Square(3, 4))
    _move(session, Square(2, 1), Square(1, 1))
    _move(session, Square(3, 4), Square(4, 4))
    return session


def _same_board_flag_unwritten(compiled):
    session = GameSession(compiled)
    _move(session, Square(0, 0), Square(0, 1))
    _move(session, Square(4, 4), Square(3, 4))
    _move(session, Square(0, 1), Square(0, 0))
    _move(session, Square(3, 4), Square(4, 4))
    return session


class _FlatEvaluator:
    def evaluate(self, state):
        return 17

    def type_value(self, piece_type):
        return 0

    def capture_order_value(self, moving, captured):
        return 0


def _player(compiled, tuning, use_tt=True):
    return AlphaBetaPlayer(
        compiled, evaluator_override=_FlatEvaluator(), use_tt=use_tt,
        use_ordering=False, tuning=tuning,
    )


def test_public_warm_tt_matches_cold_across_replayable_aux_distinct_roots():
    compiled = _aux_history_rules()
    written = _same_board_flag_written(compiled)
    unwritten = _same_board_flag_unwritten(compiled)

    assert written.state.ply_count == unwritten.state.ply_count == 4
    assert written.state.position.board == unwritten.state.position.board
    assert written.state.position.side_to_move == unwritten.state.position.side_to_move == 0
    assert written.state.position.aux_state != unwritten.state.position.aux_state
    assert search_state_identity(written.state, compiled) != search_state_identity(
        unwritten.state, compiled
    )

    for session in (written, unwritten):
        replayed = GameSession.replay(
            compiled,
            deserialize_game_record(serialize_game_record(session.to_record())),
        )
        assert replayed.state == session.state
        assert replayed.history == session.history

    limits = SearchLimits(max_depth=2, max_nodes=4096, max_time_seconds=2.0,
                          quiescence_max_depth=0, quiescence_hard_max_depth=8)
    tuning = SearchTuning(use_root_tactical=False, require_full_pv=True)
    root_before = unwritten.state
    warm = _player(compiled, tuning)
    warm.choose_action(written, limits)
    warm_result = warm.choose_action(unwritten, limits)
    cold_result = _player(compiled, tuning, use_tt=False).choose_action(
        unwritten, limits
    )

    assert warm_result.action in unwritten.legal_actions()
    assert warm_result.action == cold_result.action
    assert warm_result.score == cold_result.score
    assert warm_result.principal_variation == cold_result.principal_variation
    assert unwritten.state == root_before
    assert written.state.ply_count == unwritten.state.ply_count == 4