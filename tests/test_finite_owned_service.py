from fractions import Fraction as F
from itertools import permutations, product

import pytest

from scripts.finite_owned_service import exchangeable_hand_drop, finite_service


def test_finite_two_cycle_values_match_explicit_branch_rewards_and_collapse_control():
    modes = ('board', 'hand')
    rows = [(F(a, 2), F(b, 2)) for a, b in product(range(3), repeat=2) if a+b <= 2]
    for first, second, rewards in product(rows, rows, product((F(0), F(1, 2), F(1)), repeat=2)):
        g = dict(zip(modes, rewards)); p = dict(zip(modes, (dict(zip(modes, first)), dict(zip(modes, second)))))
        v = finite_service(g, p)
        for m in modes:
            # Independent enumerate next-mode branches plus absorbing loss;
            # first reward belongs to this cycle even if the tag subsequently dies.
            branches = [(p[m][n], g[m]+g[n]) for n in modes]
            branches.append((1-sum(p[m].values()), g[m]))
            assert v[m] == sum(prob*reward for prob, reward in branches)
            assert 0 <= v[m] <= 2*max(rewards)
        assert finite_service(g, p, horizon=1) == g
        assert finite_service(g, p, horizon=0) == dict.fromkeys(modes, F(0))
    g = {'A': F(1, 4), 'B': F(1, 4)}
    assert finite_service(g, {'A': {'A': 1, 'B': 0}, 'B': {'A': 0, 'B': 0}}) == {'A': F(1, 2), 'B': F(1, 4)}
    same_survival = {'A': {'A': F(1, 2), 'B': 0}, 'B': {'A': 0, 'B': F(1, 2)}}
    assert finite_service(g, same_survival) == {'A': F(3, 8), 'B': F(3, 8)}


def test_held_drop_can_have_future_service_without_a_guessed_hand_premium():
    # Synthetic mode transition, not estimates from a Chess/Shogi corpus.
    g = {'held': 0, 'board': F(1, 3)}
    p = {'held': {'held': F(1, 2), 'board': F(1, 2)},
         'board': {'held': 0, 'board': F(1, 4)}}
    assert finite_service(g, p) == {'held': F(1, 6), 'board': F(5, 12)}
    # Quiet/no-service construction stays zero for every survival kernel.
    assert finite_service(dict.fromkeys(g, 0), p) == dict.fromkeys(g, F(0))


def test_exchangeable_hidden_hand_tag_matches_all_distinguishable_drop_orders():
    for count in range(1, 7):
        orders = list(permutations(range(count)))
        for dropped_count in range(1, count+1):
            actual = F(sum(0 in order[:dropped_count] for order in orders), len(orders))
            held, accumulated = F(1), F(0)
            for remaining in range(count, count-dropped_count, -1):
                held, dropped = exchangeable_hand_drop(held, remaining)
                accumulated += dropped
            assert actual == accumulated == F(dropped_count, count)
            assert held+accumulated == 1
    assert exchangeable_hand_drop(F(1, 3), 2) == (F(1, 6), F(1, 6))


def test_mode_only_refresh_can_disagree_with_full_context_continuation():
    # One surviving mode has contexts with next rewards0/1. A real successor
    # chooses context1 deterministically, whereas frozen refresh chooses each
    # with probability1/2. Arithmetic is correct; the closure premise is false.
    approximate = finite_service({'R': F(1, 2)}, {'R': {'R': 1}})['R']
    full_context_value = F(1, 2) + F(1)
    assert approximate == 1 and full_context_value == F(3, 2)
    assert approximate != full_context_value


def test_unsupported_modes_invalid_mass_or_infinite_horizon_fail_closed():
    cases = [({'A': 1}, {}, {}),
             ({'A': 1}, {'A': {}}, {}),
             ({'A': -1}, {'A': {'A': 1}}, {}),
             ({'A': 1}, {'A': {'A': F(3, 2)}}, {}),
             ({'A': 1}, {'A': {'A': -1}}, {}),
             ({'A': .5}, {'A': {'A': 1}}, {}),
             ({'A': 1}, {'A': {'A': .5}}, {}),
             ({'A': 1}, {'A': {'A': 1}}, {'horizon': 3}),
             ({'A': 1}, {'A': {'A': 1}}, {'horizon': True})]
    for g, p, kwargs in cases:
        with pytest.raises(ValueError):
            finite_service(g, p, **kwargs)
    for mass, count in ((-1, 2), (F(3, 2), 2), (.5, 2), (1, 0), (1, True)):
        with pytest.raises(ValueError):
            exchangeable_hand_drop(mass, count)


def test_h2_context_residual_and_terminal_survival_are_separate():
    # Independent full-state branch calculation; no actual-game data.
    context = {'X': {'a': F(1, 2), 'b': F(1, 2)},
               'Y': {'c': F(1, 4), 'd': F(3, 4)}}
    mode = {'a': 'X', 'b': 'X', 'c': 'Y', 'd': 'Y'}
    reward = {'a': 0, 'b': 1, 'c': 1, 'd': 0}
    next_states = {'a': {'c': F(1)}, 'b': {'c': F(1)},
                   'c': {}, 'd': {'c': F(1, 2)}}
    g = {m: sum(prob*reward[s] for s, prob in mu.items()) for m, mu in context.items()}
    p = {m: {n: sum(prob*q for s, prob in mu.items()
                    for z, q in next_states[s].items() if mode[z] == n)
              for n in context} for m, mu in context.items()}
    full = {m: sum(prob*(reward[s]+sum(q*reward[z] for z, q in next_states[s].items()))
                   for s, prob in mu.items()) for m, mu in context.items()}
    approximate = finite_service(g, p)
    residual = {m: sum(prob*q*(reward[z]-g[mode[z]]) for s, prob in mu.items()
                        for z, q in next_states[s].items()) for m, mu in context.items()}
    assert residual == {'X': F(3, 4), 'Y': F(9, 32)}
    assert all(full[m]-approximate[m] == residual[m] for m in context)
    assert all(abs(residual[m]) <= sum(p[m].values())*F(3, 4) for m in context)
    # Physical tag survived a terminal action, but no next cycle is eligible.
    assert finite_service({'alive': 1}, {'alive': {'alive': 0}})['alive'] == 1
    assert finite_service({'alive': 1}, {'alive': {'alive': 1}})['alive'] == 2
