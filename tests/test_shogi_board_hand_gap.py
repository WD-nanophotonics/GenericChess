"""Same-parent different-mask proof, signed tails and retained dual information."""
from fractions import Fraction as F
import json
from pathlib import Path
import pytest
from scripts.shogi_board_hand_gap import board_hand_gap
from scripts.shogi_contact_interval_choice import shogi_contact_intervals
from scripts.shogi_complete_board_intervals import moment,BOUND,board_intervals
from scripts.coupled_linear_bounds import box_lower,certified_lower


@pytest.mark.parametrize('law',['geometric_half','linear_mixture'])
def test_complete_native_gap_is_positive_with_correct_shared_scale(law):
    raw=board_hand_gap(law);normalized=board_hand_gap(law,normalized=True)
    assert set(raw)==set('PLNSGBR')
    scale=board_intervals(law,third=True)['TR'][0]
    for mode,r in raw.items():
        assert r['lower']>0 and normalized[mode]['lower']*scale==r['lower']
        a=r['mask_ratio_bound'];cutoff=max(r['exact_masses'])+1
        assert r['tail_coefficient']==min(moment(law,t)-a*moment(law,t+1) for t in range(cutoff,BOUND[mode]+1))
    assert raw['P']['mask_ratio_bound']==F(2528,2205)
    assert raw['R']['mask_ratio_bound']==1


def test_signed_mixture_tail_keeps_negative_world_contribution():
    r=board_hand_gap('linear_mixture')
    assert all(r[mode]['tail_coefficient']<0 for mode in 'PLN')
    assert all(r[mode]['lower']>0 for mode in 'PLN')
    # This arithmetic would change if latent gamma were incorrectly separated.
    a=r['P']['mask_ratio_bound']
    assert moment('linear_mixture',2)-a*moment('linear_mixture',3)!=(1-a*moment('linear_mixture',1))*moment('linear_mixture',2)


@pytest.mark.parametrize('law',['geometric_half','linear_mixture'])
def test_exact_dual_retains_pure_drop_margin_lost_by_independent_box(law):
    boxes=shogi_contact_intervals(law);gap=board_hand_gap(law,normalized=True)['P']['lower']
    normal={('board','P'):1,('hand','P'):-1}
    assert box_lower(normal,boxes)<0
    proof={'same_parent_P_drop':(normal,gap)}
    assert certified_lower(normal,boxes,proof,{'same_parent_P_drop':F(1)})==gap>0
