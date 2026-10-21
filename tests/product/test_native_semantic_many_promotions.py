"""Semantic promotion closure must not inherit the legacy eight-target array."""
from dataclasses import replace
import pytest
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import SemanticBoardMove
from generic_chess.core.coordinates import Square
from generic_chess.core.identity import position_identity_key
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.transition import apply_action
from generic_chess.native import native_available
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.mirror import snapshot_matches
from generic_chess.native.semantic import guarded_actions, make_checked, public_action, snapshot, position_key
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleSemanticAction, RuleGeometrySpec, RuleActionEffect, RuleSquareRef, RuleInvariant
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record, serialize_game_record
from rule_semantics_ir_fixtures import _semantic_ruleset, _king_type

pytestmark = pytest.mark.skipif(not native_available(), reason='Native extension unavailable')


def many_target_rules(target_count, forced):
    targets = tuple(PieceType(f'T{i:02d}', f'T{i:02d}', (LeapAtom((0, 1)),))
                    for i in range(target_count))
    mover = PieceType('A', 'A', (LeapAtom((1, 0)),), is_promotable=True,
                      promotion_target_ids=tuple(t.type_id for t in targets))
    board = [None] * 64
    board[0], board[63], board[1] = Piece(0, 'K', 'K'), Piece(1, 'K', 'K'), Piece(0, 'A', 'A')
    move = RuleSemanticAction(name='all_targets', type_ids=('A',),
        geometry=RuleGeometrySpec(kind='leap', offset=(1, 0)), target_relation='empty',
        composition='augment', promotion_mode='inherit_compiled_masks',
        effects=(RuleActionEffect('move', from_ref=RuleSquareRef('source'),
                                 to_ref=RuleSquareRef('target')),),
        invariants=(RuleInvariant('own_anchor_safe'),))
    rules = _semantic_ruleset((_king_type(), mover, *targets), (move,), n=8,
        rows=tuple(tuple(board[i:i+8]) for i in range(0, 64, 8)))
    return replace(rules,
        promotion_allowed={'A': (frozenset({(Square(1, 0), Square(2, 0))}), frozenset())},
        promotion_forced={'A': (frozenset({Square(2, 0)}) if forced else frozenset(), frozenset())})


@pytest.mark.parametrize('target_count', [9, 62])
@pytest.mark.parametrize('forced', [False, True])
def test_full_semantic_promotion_target_closure(target_count, forced):
    compiled = compile_ruleset_for_execution(many_target_rules(target_count, forced))
    session = GameSession(compiled)
    rules = compile_native_semantic_rules(compiled)
    root = pack_semantic_search_position(compiled, rules, session)
    codes = guarded_actions(rules, root)
    actual = tuple(public_action(rules, code) for code in codes)
    expected = session.legal_actions()
    assert set(actual) == set(expected)
    semantic_promotions = {a.promotion_target_id for a in actual
                          if getattr(a, 'pattern_id', '').startswith('sem_')}
    assert semantic_promotions == {f'T{i:02d}' for i in range(target_count)} | (
        set() if forced else {None})
    for code, action in zip(codes, actual):
        child = make_checked(rules, root, code)
        reference = apply_action(session.state, action, compiled)
        assert snapshot_matches(snapshot(rules, child), reference.position, rules, compiled)
        assert position_key(rules, child) == str(position_identity_key(reference.position, compiled))
    assert position_key(rules, root) == str(position_identity_key(session.state.position, compiled))


def test_alphabeta_selects_and_replays_ninth_semantic_promotion_target():
    compiled = compile_ruleset_for_execution(many_target_rules(9, False))
    session = GameSession(compiled)

    class PreferNinthTarget:
        def evaluate(self, state):
            selected = any(
                piece is not None and piece.owner == 0
                and piece.current_type_id == "T08" and piece.promoted
                for piece in state.position.board
            )
            return -10_000 if selected else 10_000

    player = AlphaBetaPlayer(
        compiled, evaluator_override=PreferNinthTarget(), use_disk_cache=False
    )
    assert player.native_legality_provider is not None
    decision = player.choose_action(
        session,
        SearchLimits(
            max_depth=1,
            max_nodes=2_000,
            quiescence_max_depth=0,
            quiescence_hard_max_depth=0,
        ),
    )
    assert isinstance(decision.action, SemanticBoardMove)
    assert decision.action.promotion_target_id == "T08"
    assert decision.principal_variation[0] == decision.action
    session.submit(decision.action)
    record = deserialize_game_record(serialize_game_record(session.to_record()))
    replayed = GameSession.replay(compiled, record)
    assert replayed.state == session.state
    assert replayed.state.position.board[
        decision.action.to_square.rank * 8 + decision.action.to_square.file
    ].current_type_id == "T08"
    assert replayed.result == session.result
