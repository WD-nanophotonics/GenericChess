"""Mechanism tests for the opt-in projection; no material-quality assertion."""
from dataclasses import replace
import itertools

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.semantic import (
    _clear_union, _path_union, semantic_opportunity, build_semantic_opportunity_profile,
)
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict, ruleset_to_dict
from generic_chess.rules.western_chess import build_western_chess_ruleset


def compile_variant(definition=None):
    return compile_ruleset_for_execution(definition or build_western_chess_ruleset())


def test_occupancy_condition_distinguishes_capture_only_and_empty_targets():
    definition = build_western_chess_ruleset()
    capture_only = replace(definition, semantic_actions=tuple(
        a for a in definition.semantic_actions if a.name not in ('pawn_one_step', 'pawn_double_step')))
    config = EvaluationConfig(density_points=(0., .5), density_weights=(.5, .5))
    row = semantic_opportunity(compile_variant(capture_only), 'P', config)
    assert row['quiet_endpoints'] == 0
    assert row['capture_endpoints'] == 98
    assert row['curves'][0]['total'] == 0
    assert row['curves'][1]['capture'] == pytest.approx(98 / 64 / 4)


def test_projection_is_not_legacy_atoms_or_full_semantic_mobility():
    compiled = compile_variant()
    config = EvaluationConfig()
    base = build_ruleset_profile(compiled, config)
    candidate, scope = build_semantic_opportunity_profile(compiled, config)
    assert base.board_value_by_type['P'] == 1
    assert candidate.board_value_by_type['P'] > 1
    assert candidate.board_value_by_type['K'] == 0
    assert candidate.piece_profiles['P'].raw_capability_score == pytest.approx(.8501171875)
    assert candidate.evaluator_version != base.evaluator_version
    assert not scope['complete_legal_mobility']
    assert any('state/zone/postcondition' in e['reasons'] for e in scope['types']['P']['excluded'])
    assert scope['types']['P']['quiet_endpoints'] == 56
    assert len(candidate.piece_profiles['P'].movement_signature) == 64
    # Building the explicit candidate must not mutate default/cache tables.
    assert build_ruleset_profile(compiled, config) == base


def test_type_rename_preserves_geometry_and_all_normalized_values():
    def rename(value):
        if isinstance(value, dict):
            return {('Z' if k == 'P' else k): rename(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rename(v) for v in value]
        return 'Z' if value == 'P' else value
    a, sa = build_semantic_opportunity_profile(compile_variant(), EvaluationConfig())
    b, sb = build_semantic_opportunity_profile(compile_variant(ruleset_from_dict(
        rename(ruleset_to_dict(build_western_chess_ruleset())))), EvaluationConfig())
    assert {('Z' if k == 'P' else k): v for k, v in a.board_value_by_type.items()} == b.board_value_by_type
    assert sa['types']['P']['signature'] == sb['types']['Z']['signature']
    assert sa['types']['P']['curves'] == sb['types']['Z']['curves']


def test_clear_path_union_matches_exhaustive_occupancy_and_subsumption():
    paths = {frozenset((1, 2)), frozenset((2, 3)), frozenset((1, 2, 3))}
    for density in (0., .25, .5, 1.):
        exact = 0
        for occupancy in itertools.product((False, True), repeat=3):
            occupied = {i + 1 for i, value in enumerate(occupancy) if value}
            probability = density ** len(occupied) * (1 - density) ** (3 - len(occupied))
            if any(not occupied.intersection(path) for path in paths):
                exact += probability
        assert _clear_union(paths, density) == pytest.approx(exact)
    assert _clear_union({frozenset(), frozenset((1,))}, .9) == 1


def test_duplicate_patterns_do_not_count_promotion_alternatives_twice():
    compiled = compile_variant()
    row = semantic_opportunity(compiled, 'P', EvaluationConfig())
    duplicated = replace(compiled, ir=replace(compiled.ir, patterns=compiled.ir.patterns * 2))
    other = semantic_opportunity(duplicated, 'P', EvaluationConfig())
    assert row['signature'] == other['signature']
    assert row['curves'] == other['curves']


@pytest.mark.parametrize('events', [
    {(frozenset(), frozenset((1, 2)), 1)},
    {(frozenset((1,)), frozenset((1, 2)), 1)},
    {(frozenset(), frozenset((1, 2)), 1), (frozenset(), frozenset((2, 3)), 1)},
    {(frozenset((1, 2)), frozenset(), None), (frozenset(), frozenset((2, 3)), 1)},
    {(frozenset(), frozenset((1, 2)), 0), (frozenset(), frozenset((1, 2)), 2)},
    {(frozenset((1, 2)), frozenset((1, 2)), 1)},
])
def test_counted_path_union_matches_exhaustive_occupancy(events):
    cells = set().union(*(clear | counted for clear, counted, _ in events))
    for density in (0., .125, .5, 1.):
        exact = 0
        for assignment in itertools.product((False, True), repeat=len(cells)):
            occupied = {cell for cell, value in zip(sorted(cells), assignment) if value}
            if any(not occupied.intersection(clear) and
                   (count is None or len(occupied.intersection(counted)) == count)
                   for clear, counted, count in events):
                exact += density ** len(occupied) * (1 - density) ** (len(cells) - len(occupied))
        assert _path_union(events, density) == pytest.approx(exact)


def test_cannon_screen_count_is_not_treated_as_clear_path():
    from rule_semantics_ir_fixtures import cannon_ruleset
    compiled = compile_variant(cannon_ruleset())
    config = EvaluationConfig(density_points=(0., .5), density_weights=(.5, .5))
    row = semantic_opportunity(compiled, 'C', config)
    assert row['curves'][0]['capture'] == 0
    assert row['curves'][1]['capture'] > 0
    # Independent analytic census: each path with L interior squares needs
    # one occupied screen and an enemy endpoint. This fixture has a unique
    # straight ray per endpoint, so no path-independence approximation.
    from generic_chess.rules.ir import geometry_candidates
    pattern = next(p for p in compiled.ir.patterns if p.name == 'cannon_capture')
    expected = 0
    for owner in ('0', '1'):
        for source in range(compiled.board_shape.area):
            for gid in pattern.geometry_ids:
                for _, path in geometry_candidates(compiled.ir.geometry[gid], owner, source):
                    if path:
                        expected += len(path) * .5 ** len(path) * .25
    expected /= 2 * compiled.board_shape.area
    assert row['curves'][1]['capture'] == pytest.approx(expected)
    assert pattern.pattern_id in row['included']


def test_foreign_legacy_atom_geometry_is_not_bound_to_another_actor_type():
    compiled = compile_variant()
    pattern = next(p for p in compiled.ir.patterns if p.name == 'n_quiet')
    foreign = next(g.geometry_id for g in compiled.ir.geometry.values()
                   if g.atom_source is not None and g.atom_source[0] == 'R')
    altered = replace(compiled, ir=replace(compiled.ir, patterns=tuple(
        replace(p, geometry_ids=p.geometry_ids + (foreign,)) if p == pattern else p
        for p in compiled.ir.patterns)))
    a = semantic_opportunity(compiled, 'N', EvaluationConfig())
    b = semantic_opportunity(altered, 'N', EvaluationConfig())
    assert a['signature'] == b['signature']
    # Independent semantic executor also declines foreign atom_source binding.
    from generic_chess.core.semantic_executor import semantic_engine_for, SemanticEngine
    from generic_chess.core.pieces import Piece
    # Construct engine directly, avoiding the unchanged IR fingerprint cache.
    engine = SemanticEngine(altered)
    template = engine._initial_position()
    board = [None] * 64
    board[27] = Piece(0, 'N', 'N')
    position = replace(template, board=tuple(board), side_to_move=0)
    targets = {a.target for a in engine.legal_actions(position) if a.source == 27}
    expected = {a.target for a in semantic_engine_for(compiled).legal_actions(position) if a.source == 27}
    assert targets == expected


def test_material_only_evaluator_does_not_probe_zero_contribution_dynamics(monkeypatch):
    from generic_chess.ai.evaluation.evaluator import Evaluator
    import generic_chess.ai.evaluation.evaluator as module
    from generic_chess.session.session import GameSession
    from generic_chess.core.pieces import Piece
    compiled = compile_variant()
    config = EvaluationConfig(dynamic_mobility_weight=0, anchor_escape_weight=0,
                              promotion_potential_weight=0)
    profile, _ = build_semantic_opportunity_profile(compiled, config)
    evaluator = Evaluator(compiled, profile, config)
    def forbidden(*args):
        raise AssertionError('disabled dynamic feature performed a probe')
    monkeypatch.setattr(module, 'pseudo_attacks', forbidden)
    monkeypatch.setattr(module, 'is_in_check', forbidden)
    monkeypatch.setattr(Evaluator, '_anchor_escape', forbidden)
    monkeypatch.setattr(Evaluator, '_promotion_bonus', forbidden)
    state = GameSession(compiled).state
    board = [None] * 64
    board[8] = Piece(0, 'P', 'P')
    board[50] = Piece(1, 'N', 'N')
    state = replace(state, position=replace(state.position, board=tuple(board)))
    expected = profile.board_value_by_type['P'] - profile.board_value_by_type['N']
    assert evaluator.evaluate(state) == expected
    assert evaluator.evaluate(replace(state, position=replace(state.position, side_to_move=1))) == -expected


def test_nonempty_identical_atoms_do_not_hide_different_capture_semantics():
    from rule_semantics_ir_fixtures import cannon_ruleset
    from generic_chess.core.pieces import PieceType
    definition = cannon_ruleset()
    actor = next(p for p in definition.piece_types if p.type_id == 'C')
    definition = replace(definition, piece_types=definition.piece_types + (
        PieceType('R', 'R', actor.movement_atoms),),
        drop_allowed={**definition.drop_allowed, 'R': ((False,) * 64, (False,) * 64)})
    compiled = compile_variant(definition)
    old = build_ruleset_profile(compiled, EvaluationConfig())
    candidate, scope = build_semantic_opportunity_profile(compiled, EvaluationConfig())
    assert old.board_value_by_type['C'] == old.board_value_by_type['R']
    assert scope['types']['C']['raw'] != scope['types']['R']['raw']
    assert candidate.board_value_by_type['C'] != candidate.board_value_by_type['R']


@pytest.mark.parametrize('config', [
    EvaluationConfig(density_points=(0.,), density_weights=(.5, .5)),
    EvaluationConfig(density_points=(1.1,), density_weights=(1.,)),
    EvaluationConfig(density_points=(.5,), density_weights=(-1.,)),
])
def test_candidate_rejects_invalid_declared_context_law(config):
    with pytest.raises(ValueError, match='density law'):
        build_semantic_opportunity_profile(compile_variant(), config)


@pytest.mark.parametrize('seed', [7, 21])
def test_generated_legacy_rules_use_existing_lowering_without_executor_change(seed):
    from generic_chess.generation.config import GeneratorConfig
    from generic_chess.generation.generator import generate_game
    from generic_chess.ai.evaluation.mobility import atoms_overlap, analytic_mobility_at_density
    from generic_chess.rules.compiled import CompiledRuleSet
    generated = generate_game(GeneratorConfig(seed=seed, board_size=4,
        setup_preset='bilateral_random', allow_hybrid=True))
    compiled = compile_ruleset_for_execution(generated.ruleset)
    assert isinstance(compiled, CompiledRuleSet)
    assert not generated.ruleset.semantic_actions
    candidate, scope = build_semantic_opportunity_profile(compiled, EvaluationConfig())
    assert scope['ir_source'] == 'existing_legacy_lowering'
    assert not hasattr(compiled, 'ir')
    assert candidate.ruleset_fingerprint == compiled.ruleset_fingerprint
    checked = 0
    for piece in compiled.piece_types:
        row = scope['types'][piece.type_id]
        assert semantic_opportunity(compiled, piece.type_id, EvaluationConfig()) == row
        if not atoms_overlap(piece.movement_atoms):
            checked += 1
            for curve in row['curves']:
                assert curve['total'] == pytest.approx(analytic_mobility_at_density(
                    4, piece.movement_atoms, curve['density']))
    assert checked
