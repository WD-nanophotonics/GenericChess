"""Pure exact emptiness guard scope; no price-quality or full legal-mobility claim."""
from dataclasses import replace

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.semantic import semantic_opportunity
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleSet, RuleSemanticAction, RuleGeometrySpec, RuleActionEffect,
    RuleSquareRef, RuleStateGuard, RuleSpatialSelector, RuleTypeRef,
)
from rule_semantics_ir_fixtures import _king_type


def guarded_leap(offsets=((1, 0),), *, relative=True, subject=False):
    guards = []
    for offset in offsets:
        ref = RuleSquareRef('offset_from_source', offset=offset, owner_relative=relative)
        guards.append(RuleStateGuard(
            aggregation='count', owner='any', type_ref=RuleTypeRef('any'),
            compare_field='base', promoted='any', location='board',
            spatial=RuleSpatialSelector('exact', refs=(ref,)), comparison='eq', value=0,
            subject_ref=ref if subject else None))
    actions = []
    for relation in ('empty', 'enemy'):
        effects = (() if relation == 'empty' else (RuleActionEffect(
            'remove', square_ref=RuleSquareRef('target'), piece_owner='opponent'),))
        actions.append(RuleSemanticAction(
            name='guard_' + relation, type_ids=('H',),
            geometry=RuleGeometrySpec('leap', offset=(2, 1)),
            target_relation=relation, composition='augment', state_guards=tuple(guards),
            effects=effects + (RuleActionEffect('move', from_ref=RuleSquareRef('source'),
                                              to_ref=RuleSquareRef('target')),)))
    board = [None] * 15
    board[0], board[-1] = Piece(0, 'K', 'K'), Piece(1, 'K', 'K')
    return RuleSet(board_size=None, board_width=5, board_height=3,
        piece_types=(_king_type(), PieceType('H', 'H', ()), PieceType('B', 'B', ())),
        initial_position=tuple(tuple(board[r * 5:(r + 1) * 5]) for r in range(3)),
        drop_allowed={'H': ((False,) * 15,) * 2, 'B': ((False,) * 15,) * 2},
        semantic_actions=tuple(actions))


def row(definition):
    config = EvaluationConfig(density_points=(0., .125, .5, .875, 1.), density_weights=(.2,) * 5)
    return semantic_opportunity(compile_ruleset_for_execution(definition), 'H', config)


def test_distinct_leg_is_one_shared_occupancy_event_and_duplicates_are_equivalent():
    single = row(guarded_leap())
    duplicate = row(guarded_leap(((1, 0), (1, 0))))
    assert single['signature'] == duplicate['signature']
    assert single['curves'] == duplicate['curves']
    assert len(single['included']) == 2
    for curve in single['curves']:
        d = curve['density']
        # Six valid source->target leaps per owner, all with one distinct leg.
        assert curve['quiet'] == pytest.approx(6 / 15 * (1 - d) ** 2)
        assert curve['capture'] == pytest.approx(6 / 15 * (1 - d) * d / 2)


@pytest.mark.parametrize('offset,quiet_factor,capture_factor', [
    ((0, 0), 0, 0),       # source is conditioned occupied
    ((2, 1), 1, 0),       # quiet target already empty; capture target occupied
    ((20, 0), 1, 1),      # unresolved exact ref counts zero in Core
])
def test_source_target_and_offboard_guards_are_conditioned(offset, quiet_factor, capture_factor):
    projected = row(guarded_leap((offset,)))
    baseline = row(guarded_leap(()))
    for actual, base in zip(projected['curves'], baseline['curves']):
        assert actual['quiet'] == pytest.approx(base['quiet'] * quiet_factor)
        assert actual['capture'] == pytest.approx(base['capture'] * capture_factor)


@pytest.mark.parametrize('change', [
    {'owner': 'self'}, {'value': 1}, {'comparison': 'ne'},
    {'aggregation': 'exists', 'value': 1}, {'promoted': 'yes'},
    {'type_ref': RuleTypeRef('explicit', type_id='H')},
    {'subject_ref': RuleSquareRef('target')},
])
def test_other_state_guards_still_excluded_instead_of_being_assumed_empty(change):
    definition = guarded_leap()
    actions = tuple(replace(a, state_guards=tuple(replace(g, **change) for g in a.state_guards))
                    for a in definition.semantic_actions)
    projected = row(replace(definition, semantic_actions=actions))
    assert not projected['included']
    assert all('state/zone/postcondition' in p['reasons'] for p in projected['excluded']
               if p['pattern'].startswith('sem_'))


@pytest.mark.parametrize('relative', [False, True])
def test_real_core_endpoint_eligibility_and_transition_match_declared_guard(relative):
    from generic_chess.core.semantic_executor import SemanticEngine
    compiled = compile_ruleset_for_execution(guarded_leap(relative=relative))
    engine = SemanticEngine(compiled)
    template = engine._initial_position()
    for owner, source, target in ((0, 0, 7), (1, 14, 7)):
        guard_square = source + (-1 if owner and relative else 1)
        guard_on_board = guard_square < 15 and guard_square // 5 == source // 5
        for blocker_owner in (None, 0, 1):
            for endpoint_owner in (None, 0, 1):
                board = [None] * 15
                board[source] = Piece(owner, 'H', 'H')
                if guard_on_board and blocker_owner is not None:
                    board[guard_square] = Piece(blocker_owner, 'B', 'B')
                if endpoint_owner is not None:
                    board[target] = Piece(endpoint_owner, 'B', 'B')
                position = replace(template, board=tuple(board), side_to_move=owner)
                expected = ((not guard_on_board or blocker_owner is None)
                            and (endpoint_owner is None or endpoint_owner != owner))
                matches = [a for a in engine.legal_actions(position)
                           if a.source == source and a.target == target]
                assert bool(matches) == expected
                for action in matches:
                    child = engine.apply(position, action)
                    assert child.board[source] is None
                    assert child.board[target] == Piece(owner, 'H', 'H')
                    assert position.board == tuple(board)


@pytest.mark.parametrize("offsets", [((1, 0),), ((0, 0),), ((2, 1),), ((20, 0),)])
def test_equal_subject_and_spatial_ref_preserves_global_count_semantics(offsets):
    a = row(guarded_leap(offsets))
    b = row(guarded_leap(offsets, subject=True))
    assert a['signature'] == b['signature']
    assert a['curves'] == b['curves']
    from generic_chess.core.semantic_executor import SemanticEngine
    global_engine = SemanticEngine(compile_ruleset_for_execution(guarded_leap(offsets)))
    local_engine = SemanticEngine(compile_ruleset_for_execution(guarded_leap(offsets, subject=True)))
    template = global_engine._initial_position()
    for owner, source, target, guard in ((0, 0, 7, 1), (1, 14, 7, 13)):
        for blocker in (None, 0, 1):
            board = [None] * 15
            board[source] = Piece(owner, 'H', 'H')
            if blocker is not None:
                board[guard] = Piece(blocker, 'B', 'B')
            for endpoint in (None, 0, 1):
                board[target] = None if endpoint is None else Piece(endpoint, 'B', 'B')
                p = replace(template, board=tuple(board), side_to_move=owner)
                q = replace(p, ruleset_fingerprint=local_engine.support.ruleset_fingerprint)
                key = lambda e, pos: {(a.source, a.target, a.pattern_id) for a in e.legal_actions(pos)}
                assert key(global_engine, p) == key(local_engine, q)


@pytest.mark.parametrize('offset', [(1, 0), (0, 0), (2, 1), (20, 0)])
@pytest.mark.parametrize('relative', [False, True])
@pytest.mark.parametrize('subject', [False, True])
def test_exact_empty_exists_and_count_preserve_projection_and_inert_hand(offset, relative, subject):
    from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
    a = guarded_leap((offset,), relative=relative, subject=subject)
    b = replace(a, semantic_actions=tuple(replace(action, state_guards=tuple(
        replace(g, aggregation='exists') for g in action.state_guards))
        for action in a.semantic_actions))
    ca, cb = (compile_ruleset_for_execution(r) for r in (a, b))
    pa, sa = build_semantic_opportunity_profile(ca, EvaluationConfig())
    pb, sb = build_semantic_opportunity_profile(cb, EvaluationConfig())
    assert sa['types'] == sb['types']
    assert pa.board_value_by_type == pb.board_value_by_type
    assert pa.hand_value_by_base_type == pb.hand_value_by_base_type
    assert sa['hand_policy'] == sb['hand_policy'] == 'zero_proved_inert'
    assert pa.evaluator_version == pb.evaluator_version
    assert ca.ruleset_fingerprint != cb.ruleset_fingerprint


def test_equivalent_empty_guards_reach_same_full_session_leaf_score():
    from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
    from generic_chess.ai.evaluation.evaluator import Evaluator
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.limits import SearchLimits
    from generic_chess.core.movement import RayAtom
    from generic_chess.session.session import GameSession
    a = guarded_leap()
    board = [None] * 15
    board[0], board[14] = Piece(0, 'K', 'K'), Piece(1, 'K', 'K')
    board[5], board[12] = Piece(0, 'H', 'H'), Piece(1, 'B', 'B')
    a = replace(a, initial_position=tuple(tuple(board[r*5:(r+1)*5]) for r in range(3)),
                piece_types=tuple(PieceType('B', 'B', (RayAtom((1, 0)),))
                                  if p.type_id == 'B' else p for p in a.piece_types))
    b = replace(a, semantic_actions=tuple(replace(action, state_guards=tuple(
        replace(g, aggregation='exists') for g in action.state_guards))
        for action in a.semantic_actions))
    cfg = EvaluationConfig(dynamic_mobility_weight=0, anchor_escape_weight=0,
                           promotion_potential_weight=0)
    results = []
    for rule in (a, b):
        c = compile_ruleset_for_execution(rule)
        session = GameSession(c)
        profile, _ = build_semantic_opportunity_profile(c, cfg)
        player = AlphaBetaPlayer(c, evaluator_override=Evaluator(c, profile, cfg),
                                 use_disk_cache=False, use_ordering=False,
                                 use_native_semantic_legality=False)
        before = session.to_record()
        decision = player.choose_action(session, SearchLimits(
            max_depth=1, max_nodes=256, max_time_seconds=5,
            quiescence_max_depth=0, quiescence_hard_max_depth=0))
        assert session.to_record() == before
        assert decision.completed_depth == 1
        session.submit(decision.action)
        assert len(session.state.history) == 2
        assert session.state.position.hands[0].count('B') == 1
        results.append((decision.score, decision.action.pattern_id,
                        decision.action.from_square, decision.action.to_square,
                        session.state.position.board, session.state.position.hands))
    assert results[0] == results[1]
