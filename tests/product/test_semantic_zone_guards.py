"""Finite zone membership is geometry, separate from the declared source law."""
from dataclasses import replace

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.semantic import semantic_opportunity
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleSquareRef, RuleSquareZoneGuard, RuleSpatialSelector
from tests.product.test_semantic_empty_guards import guarded_leap


ZONE = ((0, 0), (1, 0), (2, 1), (4, 2))
CONFIG = EvaluationConfig(density_points=(0., .5, 1.), density_weights=(1/3,) * 3)


def zone_rule(kind, relative, relation, *, complement=False, duplicate=False):
    zone = (tuple((i % 5, i // 5) for i in range(15)
                  if (i % 5, i // 5) not in ZONE) if complement else ZONE)
    guard = RuleSquareZoneGuard(RuleSquareRef(kind),
        RuleSpatialSelector('zone', zone_squares=zone),
        relation=('outside' if relation == 'inside' else 'inside') if complement else relation,
        owner_relative=relative)
    base = guarded_leap(())
    return replace(base, semantic_actions=tuple(replace(a,
        square_zone_guards=(guard, guard) if duplicate else (guard,))
        for a in base.semantic_actions))


@pytest.mark.parametrize('kind', ['source', 'target'])
@pytest.mark.parametrize('relative', [False, True])
@pytest.mark.parametrize('relation', ['inside', 'outside'])
def test_membership_matches_actual_core_and_independent_rectangle_oracle(kind, relative, relation):
    compiled = compile_ruleset_for_execution(zone_rule(kind, relative, relation))
    engine = SemanticEngine(compiled)
    template = engine._initial_position()
    counts = {'quiet': 0, 'capture': 0}
    checked = 0
    for owner in (0, 1):
        for source in range(15):
            for occupant in (None, 0, 1):
                # Geometry is independently enumerated, including off-board sources.
                df, dr = ((2, 1) if owner == 0 else (-2, -1))
                f, r = source % 5 + df, source // 5 + dr
                target = r * 5 + f if 0 <= f < 5 and 0 <= r < 3 else None
                board = [None] * 15
                board[source] = Piece(owner, 'H', 'H')
                if target is not None and occupant is not None:
                    board[target] = Piece(occupant, 'B', 'B')
                pos = replace(template, board=tuple(board), side_to_move=owner)
                square = source if kind == 'source' else target
                zone = {(4-f, 2-r) for f, r in ZONE} if relative and owner else set(ZONE)
                inside = square is not None and (square % 5, square // 5) in zone
                expected = (target is not None and inside == (relation == 'inside')
                            and occupant != owner)
                actions = engine.legal_actions(pos)
                assert bool(actions) == expected
                if expected:
                    assert {(a.source, a.target) for a in actions} == {(source, target)}
                    counts['quiet' if occupant is None else 'capture'] += 1
                    child = engine.apply(pos, actions[0])
                    assert child.board[source] is None and child.board[target] == Piece(owner, 'H', 'H')
                    assert pos.board == tuple(board)
                checked += 1
    assert checked == 90
    projected = semantic_opportunity(compiled, 'H', CONFIG)
    assert len(projected['included']) == 2
    for curve in projected['curves']:
        d = curve['density']
        assert curve['quiet'] == pytest.approx(counts['quiet'] / 30 * (1-d))
        assert curve['capture'] == pytest.approx(counts['capture'] / 30 * d/2)
    for options in ({'complement': True}, {'duplicate': True}):
        equivalent = semantic_opportunity(compile_ruleset_for_execution(
            zone_rule(kind, relative, relation, **options)), 'H', CONFIG)
        assert equivalent['signature'] == projected['signature']
        assert equivalent['curves'] == projected['curves']


def test_non_source_target_zone_refs_are_explicitly_outside_projection_scope():
    definition = zone_rule('source', True, 'inside')
    guard = replace(definition.semantic_actions[0].square_zone_guards[0],
                    square_ref=RuleSquareRef('fixed', square=(0, 0)))
    definition = replace(definition, semantic_actions=tuple(replace(a,
        square_zone_guards=(guard,)) for a in definition.semantic_actions))
    row = semantic_opportunity(compile_ruleset_for_execution(definition), 'H', CONFIG)
    assert not row['included']
    assert any('state/zone/postcondition' in e['reasons'] for e in row['excluded'])
