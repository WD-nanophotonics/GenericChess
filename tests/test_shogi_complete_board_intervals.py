from fractions import Fraction as F
import pytest
from scripts.shogi_complete_board_intervals import board_intervals,coupled_gap,moment


@pytest.mark.parametrize('law',['geometric_half','linear_mixture'])
def test_full_positive_board_scope_and_exact_rooks(law):
    w=board_intervals(law)
    assert len(w)==13 and all(F(0)<lo<=hi<F(1) for lo,hi in w.values())
    assert w['R'][0]==w['R'][1] and w['TR'][0]==w['TR'][1]
    assert w['G']==w['TP']==w['TL']==w['TN']==w['TS']
    assert w['TR'][0]>w['R'][0]>w['TB'][1]>w['B'][1]
    gap=w['TR'][0]-w['R'][0]
    assert gap>=coupled_gap(law,'TR','R')>0


def test_coupling_is_not_inferred_from_disjoint_boxes():
    w=board_intervals('linear_mixture')
    assert w['TP'][0]<w['P'][1]  # overlap still permits same-world strict inequality
    assert coupled_gap('linear_mixture','TP','P')>0
    with pytest.raises(ValueError):coupled_gap('linear_mixture','G','L')
    with pytest.raises(ValueError):board_intervals('midpoint')


def test_exact_rook_difference_keeps_second_and_third_mass():
    for law in ('geometric_half','linear_mixture'):
        w=board_intervals(law)
        assert w['TR'][0]-w['R'][0]==(
            20224*moment(law,1)-19972*moment(law,2)-252*moment(law,3))/511920


@pytest.mark.parametrize('law',['geometric_half','linear_mixture'])
def test_three_frontier_tightens_without_inventing_silver_gold_order(law):
    before=board_intervals(law);after=board_intervals(law,third=True)
    for t in ('S','N','G'):
        assert before[t][0]<after[t][0]<=after[t][1]<before[t][1]
    assert after['S'][0]<after['G'][1] and after['G'][0]<after['S'][1]
    assert after['G']==after['TP']==after['TL']==after['TN']==after['TS']
