"""Finite supported-family consistency, not universal material-price proof."""
from dataclasses import replace

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.ir import geometry_candidates
from generic_chess.rules.schema import (
    RuleActionEffect, RuleGeometrySpec, RulePathConstraint, RuleSemanticAction,
    RuleSquareRef,
)
from rule_semantics_ir_fixtures import _king_type, _semantic_ruleset


def ray_family(length, enumerated):
    actions = []
    for direction in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for distance in range(1, length + 1) if enumerated else (None,):
            geometry = RuleGeometrySpec(kind='ray', direction=direction,
                min_steps=distance or 1, max_steps=distance or length)
            for relation in ('empty', 'enemy'):
                effects = (() if relation == 'empty' else (RuleActionEffect(
                    'remove', square_ref=RuleSquareRef('target'), piece_owner='opponent'),))
                actions.append(RuleSemanticAction(
                    name=f'{direction}_{distance}_{relation}', type_ids=('C',),
                    geometry=geometry, target_relation=relation, composition='augment',
                    path_constraints=(RulePathConstraint('path_clear'),),
                    effects=effects + (RuleActionEffect('move',
                        from_ref=RuleSquareRef('source'), to_ref=RuleSquareRef('target')),)))
    # Fixed independent non-anchor reference prevents self-normalization hiding
    # raw growth. C has no legacy atom; explicit semantic actions are authority.
    definition = _semantic_ruleset((_king_type(), PieceType('C', 'C', ()),
        PieceType('N', 'N', (LeapAtom((1, 2)), LeapAtom((-1, 2))))), tuple(actions), n=5)
    return compile_ruleset_for_execution(definition)


def edge_sets(compiled):
    return {(owner, source, target, path, p.target.kind)
        for p in compiled.ir.patterns if 'C' in p.type_ids
        for gid in p.geometry_ids for owner in ('0', '1') for source in range(25)
        for target, path in geometry_candidates(compiled.ir.geometry[gid], owner, source)}


def measure_family():
    cfg = EvaluationConfig(density_points=(0., .125, .5, .875, 1.),
        density_weights=(.2,) * 5)
    rows = []
    for length in range(1, 6):
        a, b = ray_family(length, False), ray_family(length, True)
        assert edge_sets(a) == edge_sets(b)
        pa, sa = build_semantic_opportunity_profile(a, cfg)
        pb, sb = build_semantic_opportunity_profile(b, cfg)
        ra, rb = sa['types']['C'], sb['types']['C']
        # Compiler emits drop patterns even with an all-false drop mask. This
        # projection explicitly excludes drops; compare the supported board part.
        assert all('drop' in x['reasons'] for x in ra['excluded'] + rb['excluded'])
        assert ra['signature'] == rb['signature']
        assert ra['raw'] == pytest.approx(rb['raw'], abs=1e-12, rel=0)
        assert ra['curves'] == rb['curves']
        assert pa.board_value_by_type == pb.board_value_by_type
        # Actual executor paths, including every possible single blocking square,
        # independently check the geometry union used by the projection.
        ea, eb = SemanticEngine(a), SemanticEngine(b)
        template_a, template_b = ea._initial_position(), eb._initial_position()
        checked = 0
        for owner in (0, 1):
            for source in (0, 4, 12, 20, 24):
                for blocker in (None,) + tuple(i for i in range(25) if i != source):
                    board = [None] * 25
                    board[source] = Piece(owner, 'C', 'C')
                    if blocker is not None:
                        board[blocker] = Piece(1 - owner, 'N', 'N')
                    posa = replace(template_a, board=tuple(board), side_to_move=owner)
                    posb = replace(template_b, board=tuple(board), side_to_move=owner)
                    expected = set()
                    sx, sy = source % 5, source // 5
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        for distance in range(1, length + 1):
                            x, y = sx + dx * distance, sy + dy * distance
                            if not (0 <= x < 5 and 0 <= y < 5):
                                break
                            target = y * 5 + x
                            expected.add(target)
                            if target == blocker:
                                break
                    assert ea.attacked_squares(posa, owner) == expected
                    assert eb.attacked_squares(posb, owner) == expected
                    aa = {(x.source, x.target) for x in ea.legal_actions(posa)}
                    ab = {(x.source, x.target) for x in eb.legal_actions(posb)}
                    assert aa == ab == {(source, target) for target in expected}
                    checked += 1
        rows.append(dict(length=length, raw=ra['raw'], curves=ra['curves'],
            reference_raw=sa['types']['N']['raw'],
            fixed_reference_value=1000 * ra['raw'] / sa['types']['N']['raw'],
            excluded=ra['excluded'],
            board_values=pa.board_value_by_type, executor_positions=checked,
            endpoint_path_events=len(edge_sets(a))))
    for previous, current in zip(rows, rows[1:]):
        assert current['raw'] >= previous['raw'] - 1e-12
        for ca, cb in zip(previous['curves'], current['curves']):
            assert cb['quiet'] >= ca['quiet'] - 1e-12
            assert cb['capture'] >= ca['capture'] - 1e-12
    assert rows[-1]['raw'] == rows[-2]['raw']
    assert rows[-1]['curves'] == rows[-2]['curves']
    assert rows[-1]['board_values'] == rows[-2]['board_values']
    return rows


def test_supported_ray_encoding_equivalence_growth_and_board_plateau():
    assert len(measure_family()) == 5
