"""Qualify attack coverage without treating pseudo-escapes as legal moves."""
import json
from dataclasses import replace
from pathlib import Path

import pytest

from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core.semantic_executor import semantic_engine_for
from scripts.chess_development import evaluator, root_from_fen, compile_ruleset_for_execution, build_western_chess_ruleset, iter_legal_actions, uci, record_value, play_game
from scripts.chess_shared_dynamic import CachedSharedDynamic, semantic_attack_maps


@pytest.fixture(scope='module')
def compiled():
    return compile_ruleset_for_execution(build_western_chess_ruleset())


@pytest.fixture(scope='module')
def provider(compiled):
    p = NativeSemanticLegalityProvider.try_create(compiled, strict=True)
    if p is None:
        pytest.skip('optional native extension unavailable')
    return p


@pytest.mark.parametrize('fen,counts,escapes,checks,residual', [
    ('8/7k/6P1/8/8/8/8/K7 b - - 0 1', [5, 5], [3, 4], [False, True], -45),
    ('8/6k1/8/5P2/8/8/8/K7 b - - 0 1', [5, 8], [3, 7], [False, False], 26),
])
def test_pawn_capture_controls(compiled, provider, fen, counts, escapes, checks, residual):
    s = root_from_fen(fen, compiled)
    before = record_value(s)
    ev = evaluator('geometric_half', compiled=compiled, dynamic='semantic', provider=provider)
    t = ev.terms(s)
    assert t == dict(attack_counts=counts, empty_escapes=escapes, checks=checks, residual=residual)
    engine = semantic_engine_for(compiled)
    assert counts == [sum(engine.is_square_attacked(s.position, sq, o) for sq in range(64)) for o in (0, 1)]
    assert checks == [engine.in_check(s.position, o) for o in (0, 1)]
    assert ev.queries == 128
    assert before == record_value(s)


def test_cached_legacy_preserves_all_exposed_suite_root_scores(compiled):
    path = Path(__file__).resolve().parents[1]/'docs/research/data/chess_development_suite.json'
    for case in json.loads(path.read_bytes())['cases']:
        state = root_from_fen(case['fen'], compiled)
        for policy in ('geometric_half', 'linear_mixture', 'unit'):
            old = evaluator(policy, compiled=compiled, dynamic=True)
            new = evaluator(policy, compiled=compiled, dynamic='cached_legacy')
            assert old.evaluate(state) == new.evaluate(state)
            assert old.weights == new.weights and old.order_values == new.order_values


def test_shared_residual_and_sign_without_changing_order_prices(compiled, provider):
    state = root_from_fen('8/7k/6P1/8/8/8/8/K7 b - - 0 1', compiled)
    residuals = []
    for policy in ('geometric_half', 'linear_mixture', 'unit'):
        base = evaluator(policy)
        ev = evaluator(policy, compiled=compiled, dynamic='semantic', provider=provider)
        residuals.append(ev.evaluate(state)-base.evaluate(state))
        assert ev.weights == base.weights and ev.order_values == base.order_values
        # Algebraic sign test only, not played history or a legal side flip.
        view = replace(state, position=replace(state.position, side_to_move=0))
        assert ev.evaluate(view) == -ev.evaluate(state)
    assert residuals == [-4500]*3


def test_current_occupancy_escape_is_explicitly_not_legal_escape(compiled, provider):
    state = root_from_fen('7k/8/8/8/8/8/8/r2K4 w - - 0 1', compiled)
    ev = evaluator('unit', compiled=compiled, dynamic='semantic', provider=provider)
    # e1 is shielded by d1 in the CURRENT attack map but unsafe after Kd1-e1.
    # This deliberately preserved heuristic must not claim full legality.
    legal = [uci(a) for a in iter_legal_actions(state, compiled)]
    assert 'd1e1' not in legal
    assert ev.terms(state)['empty_escapes'][0] > len(legal)


def test_requires_native_provider_and_valid_backend(compiled):
    with pytest.raises(ValueError, match='native provider'):
        evaluator('unit', compiled=compiled, dynamic='semantic')
    with pytest.raises(ValueError, match='backend'):
        evaluator('unit', compiled=compiled, dynamic='unknown')


def test_per_leaf_maps_do_not_reuse_another_position(compiled, provider):
    ev = CachedSharedDynamic(evaluator('unit'), compiled, provider=provider, semantic=True)
    a = root_from_fen('8/7k/6P1/8/8/8/8/K7 b - - 0 1', compiled)
    b = root_from_fen('8/6k1/8/5P2/8/8/8/K7 b - - 0 1', compiled)
    assert [ev.terms(s)['residual'] for s in (a, b, a)] == [-45, 26, -45]
    assert ev.queries == 384


def test_bulk_traversal_matches_independent_square_queries(compiled, provider):
    path = Path(__file__).resolve().parents[1]/'docs/research/data/chess_development_suite.json'
    for case in json.loads(path.read_bytes())['cases']:
        state = root_from_fen(case['fen'], compiled)
        maps = semantic_attack_maps(state.position, provider.engine)
        assert maps == tuple(frozenset(sq for sq in range(64) if
            provider.engine.is_square_attacked(state.position, sq, o)) for o in (0, 1))
        for policy in ('geometric_half', 'linear_mixture', 'unit'):
            query = evaluator(policy, compiled=compiled, dynamic='semantic', provider=provider)
            bulk = evaluator(policy, compiled=compiled, dynamic='semantic_bulk', provider=provider)
            assert bulk.terms(state) == query.terms(state)
            assert bulk.evaluate(state) == query.evaluate(state)
            assert bulk.queries == 0


@pytest.mark.parametrize('backend', ['cached_legacy', 'semantic_bulk'])
def test_playing_entry_retains_actual_history(compiled, provider, backend):
    from generic_chess.ai.limits import SearchLimits
    limits = SearchLimits(max_depth=2, max_nodes=2048, max_time_seconds=1,
                          quiescence_max_depth=0, quiescence_hard_max_depth=8)
    game = play_game('8/7k/6P1/8/8/8/8/K7 b - - 0 1', compiled,
        'geometric_half', 'unit', limits, 3, provider=provider, dynamic=backend)
    assert game['plies_played'] == 3
    assert all(row['legal'] for row in game['moves'])
    assert len(game['final_state']['history']) == 4
    assert all(row['statistics']['runtime_history_witness_misses'] == 0 for row in game['moves'])
