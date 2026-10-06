"""Comparison bookkeeping must not disguise execution failures as price errors."""
from dataclasses import replace
from pathlib import Path

import pytest
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.chess_development import (
    POLICIES, comparison_summary, compare_case, root_from_fen, play_game, evaluator, UciOpponent,
)


@pytest.fixture(scope='module')
def compiled():
    return compile_ruleset_for_execution(build_western_chess_ruleset())


def limits():
    return SearchLimits(max_depth=2, max_nodes=2048, max_time_seconds=1,
                        quiescence_max_depth=0, quiescence_hard_max_depth=0)


def test_preserves_rights_and_rejects_unrestorable_counters(compiled):
    s = root_from_fen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', compiled)
    assert s.ply_count == 0 and len(s.history) == 1
    assert sum(v == 1 for _, v in s.position.aux_state) == 4
    for fields in ('4 1', '0 22'):
        with pytest.raises(ValueError, match='history'):
            root_from_fen('7k/8/8/8/8/8/8/K7 w - - '+fields, compiled)


def test_misses_and_incomplete_searches_are_separate():
    def row(policy, completed, hit, move):
        return dict(policy=policy, completed=completed, reference_hit=hit, move=move)
    cases = [dict(rows=[row('geometric_half', True, True, 'a'), row('unit', True, False, 'b'),
                        row('linear_mixture', False, None, 'a')]),
             dict(rows=[row('geometric_half', True, False, 'b'), row('unit', True, True, 'a'),
                        row('linear_mixture', True, False, 'c')])]
    summary = comparison_summary(cases)
    assert summary['methods']['linear_mixture']['execution_failures'] == 1
    assert summary['methods']['linear_mixture']['reference_misses'] == 1
    assert summary['paired']['unit']['candidate_only_hit'] == 1
    assert summary['paired']['unit']['other_only_hit'] == 1
    assert summary['paired']['linear_mixture']['paired_completed'] == 1


def test_real_compare_and_play_use_legal_actions_without_mutating_root(compiled):
    case = dict(id='capture', fen='7K/8/8/8/8/1Rk5/2N5/8 b - - 0 1',
                accepted_uci=['c3b3'], answer_basis='known exposed source control')
    result = compare_case(case, compiled, limits())
    assert all(r['completed'] and r['reference_hit'] and r['state_preserved'] for r in result['rows'])
    game = play_game(case['fen'], compiled, 'geometric_half', 'unit', limits(), 3)
    assert game['plies_played'] == 3
    assert all(r['legal'] for r in game['moves'])
    assert len(game['final_state']['history']) == 4
    assert not game['finished'] and game['end'] == 'ply_limit'


def test_bad_answers_are_not_silently_scored(compiled):
    with pytest.raises(ValueError, match='declared answers'):
        compare_case(dict(id='bad', fen='7K/8/8/8/8/1Rk5/2N5/8 b - - 0 1',
                          accepted_uci=['c3c8'], answer_basis='bad'), compiled, limits())


def test_leaf_prices_vary_but_ordering_prices_are_shared():
    ev = [evaluator(policy) for policy in POLICIES]
    assert len({tuple(sorted(e.weights.items())) for e in ev}) == 3
    assert ev[0].order_values == ev[1].order_values == ev[2].order_values


def test_native_and_python_complete_search_parity(compiled):
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    native = NativeSemanticLegalityProvider.try_create(compiled, strict=True)
    if native is None:
        pytest.skip('optional supported native extension unavailable')
    case = dict(id='capture', fen='7K/8/8/8/8/1Rk5/2N5/8 b - - 0 1',
                accepted_uci=['c3b3'], answer_basis='exposed source control')
    a = compare_case(case, compiled, limits(), ordering=True, use_tt=True)
    b = compare_case(case, compiled, limits(), provider=native, ordering=True, use_tt=True)
    assert all(r['completed'] for r in a['rows']+b['rows'])
    assert [(r['move'],r['score']) for r in a['rows']] == [(r['move'],r['score']) for r in b['rows']]


def test_shared_dynamic_terms_do_not_change_leaf_prices(compiled):
    state = root_from_fen('7K/8/8/8/8/1Rk5/2N5/8 b - - 0 1', compiled)
    deltas = []
    for policy in POLICIES:
        base = evaluator(policy)
        full = evaluator(policy, compiled=compiled, dynamic=True)
        assert full.weights == base.weights
        deltas.append(full.evaluate(state)-base.evaluate(state))
        flipped = replace(state, position=replace(state.position, side_to_move=1-state.position.side_to_move))
        assert full.evaluate(flipped) == -full.evaluate(state)
    assert len(set(deltas)) == 1


def test_terminal_game_is_finished_without_inventing_a_move(compiled):
    game = play_game('7k/6Q1/5K2/8/8/8/8/8 b - - 0 1', compiled, 'unit', 'geometric_half', limits(), 3)
    assert game['finished'] and game['end'] == 'checkmate'
    assert game['winner'] == 0 and game['plies_played'] == 0


def test_external_illegal_output_is_execution_failure_not_played_ply(compiled):
    class BadExternal:
        def choose(self):
            return 'c3c8', dict(policy='uci_reference', move='c3c8', reason='uci_bestmove', statistics={})
        def push(self, *args):
            raise AssertionError('illegal move must not be applied')
    game = play_game('7K/8/8/8/8/1Rk5/2N5/8 b - - 0 1', compiled,
                     'unit', 'uci_reference', limits(), 3, external=BadExternal())
    assert game['end'] == 'execution_failure' and not game['finished']
    assert game['plies_played'] == 0 and game['plies_attempted'] == 1
    assert game['incomplete_searches'] == 1


def test_uci_alignment_preserves_raw_ep_and_detects_wrong_rights(compiled, monkeypatch):
    # Optional pinned author library used by the development UCI entry. No
    # network or dependency installation occurs in this test.
    author = Path('.local_agent/certificate_source/python-chess')
    if author.exists():
        monkeypatch.syspath_prepend(str(author.resolve()))
    pytest.importorskip('chess.engine')
    from generic_chess.core.movegen import iter_legal_actions
    from generic_chess.core.transition import apply_action
    from scripts.chess_development import uci
    fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    state = root_from_fen(fen, compiled)
    external = UciOpponent(None, fen, 1)
    for move in ('e2e4', 'a7a6', 'e4e5', 'd7d5', 'e5d6'):
        action = next(a for a in iter_legal_actions(state, compiled) if uci(a) == move)
        state = apply_action(state, action, compiled)
        external.push(move, state)
    # A board-identical state with an incorrectly cleared right must fail.
    move = 'e7d6'
    action = next(a for a in iter_legal_actions(state, compiled) if uci(a) == move)
    state = apply_action(state, action, compiled)
    aux = dict(state.position.aux_state)
    aux[(3, -1)] = 0
    bad = replace(state, position=replace(state.position, aux_state=tuple(sorted(aux.items()))))
    with pytest.raises(ValueError, match='w_ks mismatch'):
        external.push(move, bad)
