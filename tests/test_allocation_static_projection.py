from fractions import Fraction as F
import pytest
from scripts.allocation_static_projection import token_weighted_prototypes,inventory_score_interval


def test_variable_counts_preserve_total_mean_only_with_token_sampling():
    frames=[(F(1,2),{'a':1},{'a':(1,1)}),(F(1,2),{'a':3},{'a':(0,0)})]
    w=token_weighted_prototypes(frames)
    assert w=={'a':(F(1,4),F(1,4))}
    mean=sum(q*inventory_score_interval(n,w)[0] for q,n,_ in frames)
    assert mean==F(1,2)
    # Independent root-average per-token calculation gives the wrong mean.
    root_average=F(1,2)*(F(1,1)+F(0,3))
    assert root_average==F(1,2)
    assert sum(q*n['a']*root_average for q,n,_ in frames)==1
    # Changing population destroys even the unconditional mean guarantee.
    assert inventory_score_interval({'a':3},w)==(F(3,4),F(3,4))


def test_zero_count_roots_do_not_disappear_or_get_per_root_normalized():
    frames=[(F(1,3),{'a':0},{'a':(0,0)}),(F(2,3),{'a':2},{'a':(1,1)})]
    assert token_weighted_prototypes(frames)=={'a':(F(1,2),F(1,2))}


def test_matched_knight_example_mean_matches_while_constant_predicts_better():
    frames=[(F(1,2),{'Nboard':1,'Nhand':0,'R':1},
             {'Nboard':(1,1),'Nhand':(0,0),'R':(0,0)}),
            (F(1,2),{'Nboard':0,'Nhand':1,'R':1},
             {'Nboard':(0,0),'Nhand':(F(1,2),F(1,2)),'R':(F(1,2),F(1,2))})]
    w=token_weighted_prototypes(frames)
    predictions=[inventory_score_interval(n,w)[0] for _,n,_ in frames]
    assert predictions==[F(5,4),F(3,4)]
    assert sum(predictions)/2==1
    assert sum((h-1)**2 for h in predictions)/2==F(1,16)
    assert sum((1-1)**2 for _ in predictions)==0


def test_signed_unknown_components_cannot_be_clipped_or_treated_independent():
    frames=[(1,{'a':1,'b':1},{'a':(-F(1,2),F(1,2)),'b':(F(1,2),F(3,2))})]
    # Individual allocations of one physical resource are in[-1,1].
    with pytest.raises(ValueError):token_weighted_prototypes(frames)
    w=token_weighted_prototypes([(1,{'a':1,'b':1},{'a':(-1,1),'b':(-1,1)})])
    assert inventory_score_interval({'a':1,'b':1},w)==(-2,2)
    # A caller may know the correlated efficiency sum is1. The component box
    # cannot invent this joint information, so[-2,2] is deliberately conservative.
    assert token_weighted_prototypes([(1,{'a':1,'b':1},
                                      {'a':(F(1,2),F(1,2)),'b':(-F(1,2),-F(1,2))})])['b']==(-F(1,2),-F(1,2))


def test_population_and_coverage_errors_fail_closed():
    bad=[[],[(1,{'a':0},{'a':(0,0)})],[(F(1,2),{'a':1},{'a':(1,1)})],
         [(1,{'a':1},{})],[(1,{'a':1},{'a':(0.0,1)})],[(1,{'a':True},{'a':(0,0)})],
         [(1,{'a':1},{'a':(1,0)})],[(1,{'a':0},{'a':(0,1)})]]
    for frames in bad:
        with pytest.raises(ValueError):token_weighted_prototypes(frames)
    with pytest.raises(ValueError):inventory_score_interval({'unseen':1},{'a':(0,1)})
    with pytest.raises(ValueError):token_weighted_prototypes([(1,{'a':1},{'a':(0,1)})]*129)
