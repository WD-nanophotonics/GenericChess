from itertools import product
from types import SimpleNamespace
import pytest
from generic_chess.core.terminal import TerminalStatus as S
from scripts.finite_terminal_window import leaf_intervals, combine_replies, tie_margin
from scripts.audit_chess_multimode_response import proposal


def terminal(status, winner=None, unresolved=False):
    return SimpleNamespace(status=status, winner=winner,
        is_terminal=status is not S.ONGOING, unresolved=unresolved)


def test_cutoff_is_window_zero_but_never_eventual_draw():
    assert leaf_intervals(terminal(S.ONGOING)) == {'window': (0, 0), 'eventual': (-1, 1)}
    assert leaf_intervals(terminal(S.CHECKMATE, 0)) == {'window': (1, 1), 'eventual': (1, 1)}
    assert leaf_intervals(terminal(S.CHECKMATE, 1)) == {'window': (-1, -1), 'eventual': (-1, -1)}
    assert leaf_intervals(terminal(S.STALEMATE)) == {'window': (0, 0), 'eventual': (0, 0)}
    for value in (terminal(S.NO_CONTEST), terminal(S.CHECKMATE, 0, True)):
        assert leaf_intervals(value) == {'window': (-1, 1), 'eventual': (-1, 1)}


def test_terminal_invalid_winners_fail_instead_of_zero():
    for value in (terminal(S.CHECKMATE), terminal(S.CHECKMATE, True),
                  terminal(S.CHECKMATE, 2), terminal(S.STALEMATE, 0)):
        with pytest.raises(ValueError): leaf_intervals(value)


def test_reply_intervals_enclose_every_adversarial_completion():
    choices = ((-1, -1), (0, 0), (1, 1), (-1, 1), (-1, 0), (0, 1))
    for pairs in product(choices, repeat=3):
        rows = [dict(window=p, eventual=p) for p in pairs]
        completions = list(product(*(range(lo, hi+1) for lo, hi in pairs)))
        for owner, operation in ((0, max), (1, min)):
            actual = [operation(values) for values in completions]
            bound = combine_replies(rows, owner=owner, complete=True)
            assert bound['window'] == (min(actual), max(actual))
            assert bound['eventual'] == bound['window']
            unknown = combine_replies(rows, owner=owner, complete=False)['window']
            assert unknown[0] <= min(actual) <= max(actual) <= unknown[1]
    assert combine_replies([], owner=1, complete=False)['window'] == (-1, 1)
    with pytest.raises(ValueError): combine_replies([], owner=1, complete=True)


def test_shared_selection_cancels_unknown_and_ties_retain_bad_alternative():
    intervals = {'a': (-1, 1), 'b': (1, 1), 'c': (-1, -1)}
    assert tie_margin(intervals, ['a'], ['a'], owner=0) == (0, 0)
    assert tie_margin(intervals, ['b'], ['b', 'c'], owner=0) == (0, 2)
    assert tie_margin(intervals, ['b'], ['c'], owner=1) == (-2, -2)


def test_generator_has_predeclared_inventory_and_pawn_domain():
    # Pure structural proposals only; no compiled rules, roots or goal labels.
    for i in range(128):
        rows = proposal(i)
        assert len({sq for sq, _, _ in rows}) == 7
        assert sorted((owner, mode) for _, owner, mode in rows) == sorted(
            [(0, 'K'), (0, 'P'), (0, 'R'), (1, 'K'), (1, 'N'), (1, 'B'), (1, 'Q')])
        assert all(24 <= sq < 48 for sq, _, mode in rows if mode == 'P')
