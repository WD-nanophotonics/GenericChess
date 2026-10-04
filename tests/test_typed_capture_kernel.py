from fractions import Fraction
from itertools import product

import pytest

from scripts.audit_typed_capture_kernel import (
    cube_holds, matrix_report, rational_rank, sparse_incidence,
)


def test_sparse_semantics_union_branches_and_respect_blockers():
    key = (0, 'A', 0, 1, 'enemy', ((1, 'capture_to_hand'),), 'A')
    alias = (*key[:-1], 'PROMOTED')
    blocked = (0, 'A', 0, 3, 'enemy', ((3, 'capture_to_hand'),), 'A')
    quiet = (1, 'A', 2, 1, 'empty', (), 'A')
    off_target = (0, 'A', 2, 3, 'empty', ((1, 'remove_from_game'),), 'A')
    supports, edges = sparse_incidence({'coverage_complete': True, 'events': {
        key: (((1, ('enemy',)),),), alias: (((1, ('enemy',)),),),
        blocked: (((1, ('enemy', 'own')), (3, ('enemy',))),),
        quiet: (((1, ('empty',)),),),
        off_target: (((1, ('enemy',)), (3, ('empty',))),),
    }})
    assert supports == {0: {0, 2}, 1: {2}}
    assert edges == {0: {(0, 1), (2, 1)}, 1: set()}
    assert cube_holds(((0, ('own',)), (1, ('enemy',)), (2, ('empty',))), 0, 1)
    assert not cube_holds(((2, ('own',)),), 0, 1)


def test_unsupported_and_multiple_removals_fail_instead_of_becoming_zero():
    with pytest.raises(ValueError, match='unsupported intrinsic'):
        sparse_incidence({'coverage_complete': False})
    key = (0, 'A', 0, 1, 'enemy', ((1, 'remove_from_game'), (2, 'remove_from_game')), 'A')
    with pytest.raises(ValueError, match='multiple-victim'):
        sparse_incidence({'coverage_complete': True, 'events': {key: ((),)}})
    with pytest.raises(ValueError, match='unsupported occupancy'):
        cube_holds(((1, ('typed_enemy',)),), 0, 1)
    with pytest.raises(ValueError, match='distinct'):
        cube_holds((), 0, 0)


def test_pair_probabilities_against_explicit_population_enumeration():
    types = ['A', 'B', 'C']
    supports = {'A': {0: {0, 1}, 1: {2, 3}},
                'B': {0: {0, 1, 2, 3}, 1: {0, 1, 2, 3}},
                'C': {0: {1, 2}, 1: {0, 3}}}
    edges = {'A': {0: {(0, 2), (1, 2)}, 1: {(2, 1)}},
             'B': {0: {(0, 1), (2, 3)}, 1: {(1, 0), (3, 2)}},
             'C': {0: {(1, 3)}, 1: {(0, 2), (3, 1)}}}
    report = matrix_report(types, supports, edges)
    for actor, victim in product(types, repeat=2):
        means = []
        for owner in (0, 1):
            population = [(s, t) for s, t in product(supports[actor][owner], supports[victim][1-owner])
                          if s != t]
            successes = [pair for pair in population if pair in edges[actor][owner]]
            expected = Fraction(len(successes), len(population))
            actual = report['owner_pair_accounting'][f'{actor}/{victim}'][owner]
            assert actual['pairs'] == len(population)
            assert actual['captures'] == len(successes)
            assert Fraction(actual['probability']) == expected
            means.append(expected)
        assert Fraction(report['matrix'][types.index(actor)][types.index(victim)]) == sum(means) / 2
    assert report['rank'] > 1 and report['nonzero_minor'] is not None
    with pytest.raises(ValueError, match='empty pair population'):
        matrix_report(['A'], {'A': {0: {0}, 1: {0}}}, edges)


def test_exchangeable_support_collapses_columns_and_is_label_invariant():
    supports = {t: {o: set(range(4)) for o in (0, 1)} for t in ('A', 'B')}
    edges = {'A': {0: {(0, 1)}, 1: {(3, 2)}},
             'B': {0: {(s, t) for s in range(4) for t in range(4) if s != t},
                   1: {(s, t) for s in range(4) for t in range(4) if s != t}}}
    result = matrix_report(['A', 'B'], supports, edges)
    assert result['matrix'] == [['1/12', '1/12'], ['1', '1']]
    assert result['rank'] == 1 and result['nonzero_minor'] is None
    assert result['identical_column_groups'] == [['A', 'B']]
    reverse = matrix_report(['B', 'A'], supports, edges)
    assert reverse['matrix'] == [['1', '1'], ['1/12', '1/12']]
    # Reverse owners and squares: owner averaging must be invariant.
    mirrored_supports = {t: {o: {3-s for s in supports[t][1-o]} for o in (0, 1)} for t in supports}
    mirrored_edges = {t: {o: {(3-s, 3-v) for s, v in edges[t][1-o]} for o in (0, 1)} for t in edges}
    assert matrix_report(['A', 'B'], mirrored_supports, mirrored_edges)['matrix'] == result['matrix']


def test_exact_rank_controls_zero_dependent_and_full_rank():
    assert rational_rank([[0, 0], [0, 0]]) == 0
    assert rational_rank([[Fraction(1, 3), Fraction(2, 3)], [1, 2]]) == 1
    assert rational_rank([[0, 1, 0], [1, 0, 0], [0, 0, 1]]) == 3
    assert rational_rank([[1, 2, 3], [0, 0, 1]]) == 2
    with pytest.raises(ValueError, match='rectangular'):
        rational_rank([[1], [1, 2]])
