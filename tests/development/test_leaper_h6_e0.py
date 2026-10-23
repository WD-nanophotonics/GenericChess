from fractions import Fraction as F
from scripts.leaper_h6_e0_bounds import contrast,contrast_family_rate
from scripts.leaper_h6_e0 import graph,safe_geometry
from scripts import leaper_design as L

def test_conditional_brier_gain_does_not_imply_rate_gain():
    families=[{'family':0}]
    # A positive root gets a perfect local correction, but the other root
    # was overpredicted. Averaging predictions can therefore worsen rateMSE.
    rows=[{'family':0,'literal_oneply_positive':True,'proposed_colour_negative':False,'predictions':{'before':0,'after':1}},
          {'family':0,'literal_oneply_positive':False,'proposed_colour_negative':True,'predictions':{'before':1,'after':1}}]
    root=contrast(rows,families,'after','before',True)
    rate=contrast_family_rate(rows,families,'after','before',True)
    assert root['lower']==root['upper']=='-1/2'
    assert rate['lower']==rate['upper']=='1/4'

def test_unknown_is_shared_between_model_and_baseline():
    rows=[{'family':0,'literal_oneply_positive':False,'proposed_colour_negative':False,'predictions':{'p':.75,'q':1}}]
    c=contrast(rows,[{'family':0}],'p','q',False)
    # Compute both possible labels directly; never subtract separate score
    # extrema that assign contradictory labels to the same root.
    exact=[F(3,4)**2-1,(F(3,4)-1)**2]
    assert F(c['lower'])==min(exact)==F(-7,16)
    assert F(c['upper'])==max(exact)==F(1,16)

def test_three_board_graph_really_uses_three_board():
    # Only the two opposite-corner pairs can use a 2x2 diagonal leap.
    assert graph(16)['components']==[1,1,1,1,1,2,2]
    assert graph(16)['mean_degree']==4/9

def test_full_offset_vocabulary_has_no_both_safe_initial_layout():
    # Mask31 attacks EVERY other square of a3x3board. Since B and K0
    # occupy different squares, K0 cannot be initially safe; this is a
    # structural admission failure, never a sampled losing outcome.
    for b in range(9):
        x,y=b%3,b//3
        for k in range(9):
            if k==b:continue
            assert (k%3-x,k//3-y) in L.offsets(31)
    import itertools
    assert not any(safe_geometry(spec,13,31) for spec in itertools.permutations(range(9),4))
