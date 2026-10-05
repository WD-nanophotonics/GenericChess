from fractions import Fraction as F
import pytest
from scripts.coupled_material_choice import coupled_material_choice
from scripts.material_interval_choice import certified_ongoing_material_choice
from scripts.shogi_contact_interval_choice import shogi_contact_intervals
from scripts.shogi_board_hand_gap import board_hand_gap

@pytest.mark.parametrize('law',['geometric_half','linear_mixture'])
@pytest.mark.parametrize('owner',[0,1])
def test_complete_analytic68_partition_retains_drop_correlation(law,owner):
    sign=1 if owner==0 else -1
    quiet={('board','P'):sign,('hand','P'):sign}
    dropped={('board','P'):2*sign,('hand','P'):0}
    table={f'D:{rank}:{file}':dropped for rank in range(8) for file in range(1,9)}
    table.update({f'Q:{i}':quiet for i in range(4)})
    assert len(table)==68
    boxes=shogi_contact_intervals(law)
    gap=board_hand_gap(law,normalized=True)['P']['lower']
    proofs={'drop':({('board','P'):F(1),('hand','P'):F(-1)},gap)}
    witnesses={(a,b):{'drop':F(1)} for a in table if a.startswith('D:') for b in table if b.startswith('Q:')}
    assert certified_ongoing_material_choice(table,boxes,owner=owner,complete=True)['selected'] is None
    result=coupled_material_choice(table,boxes,proofs,witnesses,owner=owner,complete=True)
    assert result['selected']==min(k for k in table if k.startswith('D:'))
    assert all(v==gap for k,v in result['margins'].items() if k.startswith('Q:'))
    assert all(v==0 for k,v in result['margins'].items() if k.startswith('D:'))

def test_incomplete_or_missing_witness_stays_unresolved():
    b={('board','P'):(F(0),F(1)),('hand','P'):(F(0),F(1))}
    t={'a':{('board','P'):1},'b':{('hand','P'):1}}
    assert not coupled_material_choice(t,b,{}, {},owner=0)['complete']
    assert coupled_material_choice(t,b,{}, {},owner=0,complete=True)['selected'] is None

def test_unknown_and_negative_duals_are_rejected():
    b={'x':(F(0),F(1))};t={'a':{'x':1},'b':{'x':0}}
    with pytest.raises(ValueError,match='missing constraint'):
        coupled_material_choice(t,b,{}, {('a','b'):{'unknown':1}},owner=0,complete=True)
    with pytest.raises(ValueError,match='negative dual'):
        coupled_material_choice(t,b,{'p':({'x':1},F(1,2))},{('a','b'):{'p':-1}},owner=0,complete=True)

def test_equal_feature_canonical_ties_and_owner_orientation():
    b={'x':(F(1),F(1))}
    assert coupled_material_choice({'z':{'x':1},'a':{'x':1}},b,{}, {},owner=0,complete=True)['selected']=='a'
    assert coupled_material_choice({'a':{'x':1},'b':{'x':-1}},b,{}, {},owner=1,complete=True)['selected']=='b'
