from fractions import Fraction as F
import pytest
from scripts.leaper_fork_tactical_scope import mechanism,uniform_floor_bounds


def root(value,bounds):return dict(wdl_bounds=[value,value],action_bounds=[dict(action={'n':i},wdl_bounds=b)for i,b in enumerate(bounds)])


def test_immediate_win_floor_never_uses_fallback():
    q=uniform_floor_bounds(root(1,[[1,1],[0,0],[-1,-1]]),True)
    assert q['action_WDL_mean']==['1','1']and q['lowering_probability']==['0','0']


def test_no_mate_uniform_fallback_retains_one_sided_uncertainty():
    q=uniform_floor_bounds(root(1,[[1,1],[0,0],[0,1]]),False)
    assert list(map(F,q['action_WDL_mean']))==[F(1,3),F(2,3)]
    assert list(map(F,q['lowering_probability']))==[F(1,3),F(2,3)]
    assert list(map(F,q['guarantee_gap_mean']))==[F(1,3),F(2,3)]


def test_ordinal_gap_is_not_binary_error_probability():
    q=uniform_floor_bounds(root(1,[[1,1],[-1,-1]]),False)
    assert list(map(F,q['guarantee_gap_mean']))==[F(1),F(1)]
    assert list(map(F,q['lowering_probability']))==[F(1,2),F(1,2)]


def test_draw_loss_fork_is_not_failed_win_search():
    assert mechanism([0,0],False)=='DRAW_avoid_LOSS'
    with pytest.raises(ValueError):mechanism([0,0],True)
    with pytest.raises(ValueError):mechanism([-1,-1],False)


def test_exact_loss_fork_has_no_distinct_lower_action_value():
    with pytest.raises(ValueError):mechanism([-1,-1],False)
