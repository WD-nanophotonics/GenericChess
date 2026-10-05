from fractions import Fraction as F
import pytest
from scripts.coupled_linear_bounds import box_lower,certified_lower
from scripts.shogi_complete_board_intervals import board_intervals,coupled_gap


@pytest.mark.parametrize('law',['geometric_half','linear_mixture'])
def test_joint_same_world_constraints_recover_strict_exchange(law):
    boxes=board_intervals(law,third=True)
    constraints={k:({a:1,b:-1},coupled_gap(law,a,b)) for k,a,b in (('LP','L','P'),('TPP','TP','P'))}
    c={'L':1,'TP':1,'P':-2}
    assert box_lower(c,boxes)<0
    lower=certified_lower(c,boxes,constraints,{'LP':1,'TPP':1})
    assert lower==coupled_gap(law,'L','P')+coupled_gap(law,'TP','P')>0


def test_residual_dual_is_sound_at_all_feasible_vertices():
    boxes={'x':(F(0),F(3)),'y':(F(0),F(2))}
    constraints={'gap':({'x':1,'y':-1},F(1))}
    # Vertices of rectangle intersected with x-y>=1.
    vertices=[(1,0),(3,0),(3,2)]
    for c in ({'x':1,'y':-1},{'x':2,'y':-1},{'x':-1,'y':2}):
        for multiplier in (F(0),F(1,2),F(1),F(2)):
            lower=certified_lower(c,boxes,constraints,{'gap':multiplier})
            assert all(lower<=c['x']*x+c['y']*y for x,y in vertices)


def test_missing_proof_negative_multiplier_and_unknown_coordinate_rejected():
    with pytest.raises(ValueError,match='missing'):certified_lower({'x':1},{'x':(0,1)},{},{'missing':1})
    with pytest.raises(ValueError,match='negative'):certified_lower({'x':1},{'x':(0,1)},{'p':({'x':1},0)},{'p':-1})
    with pytest.raises(ValueError,match='unsupported'):box_lower({'hand':1},{'x':(0,1)})
