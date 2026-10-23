"""Scientific observer controls: history barriers and calibration denominators."""
from copy import deepcopy
from itertools import product
import math

import pytest

from scripts.leaper_explorer_truth import family_key, score, materialize, digest
from scripts.leaper_cooperative_truth import cooperative_distances


def fixture_truth():
    return dict(roots=[dict(id=str(i), fingerprint='rule', mu_id='mu',
                           split='calibration_exposed', wdl_fork=y,
                           cooperative_decisive=None, universal_draw=None)
                       for i,y in enumerate((True,False,None,True))])


def prediction(i, p):
    return dict(id=str(i), fingerprint='rule', mu_id='mu', property='wdl_fork',
                probability=p, source_sha='a'*40, cost=dict(nodes=10,seconds=.1))


def scored(rows):
    return score(fixture_truth(), dict(format='leaper-explorer-predictions-v1',predictions=rows))['rows'][0]


def test_abstention_and_unknown_are_not_negative_labels():
    row=scored([prediction(0,.8),prediction(1,.6),prediction(2,.9)])
    assert (row['denominator'],row['truth_known'],row['predicted'],row['known'],row['abstained']) == (4,3,3,2,1)
    assert (row['tp'],row['fp'],row['tn'],row['fn']) == (1,1,0,0)
    assert math.isclose(row['brier_known'],.2)
    assert row['whole_denominator_brier_bounds'] == pytest.approx([(.04+.36+.01)/4,(.04+.36+.81+1)/4])


def test_absent_predictions_cannot_report_perfect_calibration():
    row=scored([])
    assert row['brier_known'] is None and row['abstained']==4
    assert row['whole_denominator_brier_bounds']==[0,1]
    assert row['fp']==row['fn']==0


def test_high_confidence_unknown_is_not_zero_selective_risk():
    out=score(fixture_truth(),dict(format='leaper-explorer-predictions-v1',predictions=[prediction(0,.8),prediction(2,.9)]))
    row=next(r for r in out['selective']if r['property']=='wdl_fork'and r['confidence_threshold']==.9)
    assert row['accepted']==1 and row['known']==0 and row['coverage']==.25
    assert row['conditional_error_bounds']==[0,1]


def test_equal_rule_macro_does_not_weight_longer_rule_trajectories_more():
    truth=dict(roots=[]);qs=[]
    for i,fp in enumerate(('A','A','A','B')):
        truth['roots'].append(dict(id=str(i),fingerprint=fp,mu_id=fp,split='calibration_exposed',wdl_fork=True,cooperative_decisive=None,universal_draw=None))
        qs.append(prediction(i,1 if fp=='A' else 0)|dict(fingerprint=fp,mu_id=fp))
    out=score(truth,dict(format='leaper-explorer-predictions-v1',predictions=qs))
    assert out['rows'][0]['brier_known']==.25
    assert out['macro'][0]['equal_rule_whole_brier_bounds']==[.5,.5]


@pytest.mark.parametrize('field,value', [('fingerprint','wrong'),('mu_id','wrong'),('id','absent'),('property','made_up'),
                                      ('probability',float('nan')),('probability',float('inf')),('probability',True),
                                      ('probability',1.1),('cost',{}),('source_sha','')])
def test_wrong_binding_and_invalid_data_rejected(field,value):
    q=prediction(0,.5);q[field]=value
    with pytest.raises(ValueError): scored([q])


def test_duplicate_prediction_is_not_an_extra_vote():
    with pytest.raises(ValueError):scored([prediction(0,.5),prediction(0,.4)])


def test_nonzero_wdl_implies_cooperative_route_but_draw_does_not():
    base=dict(roots=[dict(id='w',wdl_bounds=[1,1],cooperative_decisive=None,universal_draw=None),
                     dict(id='d',wdl_bounds=[0,0],cooperative_decisive=None,universal_draw=None)])
    q=dict(source_truth_digest=digest(base),rows=[])
    out=materialize(base,q)
    assert out['roots'][0]['cooperative_decisive']is True
    assert out['roots'][0]['universal_draw']is False
    assert out['roots'][1]['cooperative_decisive']is None
    assert base['roots'][0]['cooperative_decisive']is None
    q['rows']=[dict(id='w',cooperative_decisive=False,universal_draw=True)]
    with pytest.raises(ValueError):materialize(base,q)


def test_swapped_names_and_layouts_share_family_partition():
    assert family_key([1,8])==family_key([8,1])
    assert family_key([1,8])!=family_key([1,16])
    with pytest.raises(ValueError):family_key([True,8])


def test_blocked_root_may_leave_but_cannot_be_used_as_internal_exit():
    # 0 -> 1 -> decisive2. History already visited1 three times.
    ds,nxt=cooperative_distances([[1],[2],[]],{2},{1})
    assert ds=={1:1,2:0} and nxt=={1:2}
    # Mate has precedence: an already saturated decisive destination survives.
    assert cooperative_distances([[1],[]],{1},{1})[0]=={0:1,1:0}


def test_partial_graph_is_not_a_deadzone_proof():
    with pytest.raises(ValueError):cooperative_distances([[1],None],{0})
    with pytest.raises(ValueError):cooperative_distances([[5],[]],{1})


def literal_reachable(edges, root, counts, decisive, remaining):
    if root in decisive:return True  # Core mate before repetition/clock
    if counts[root]>=4 or not remaining:return False
    for ch in edges[root]:
        more=list(counts);more[ch]+=1
        if literal_reachable(edges,ch,tuple(more),decisive,remaining-1):return True
    return False


def test_cycle_shortening_against_full_history_unrolling():
    # Every directed graph on3 vertices with vertex2 a decisive sink. All
    # prehistory count combinations1..3, every ongoing root0/1 and horizon0..5.
    # This reference keeps all counts and cannot quotient histories.
    for bits in product((0,1),repeat=6):
        edges=[[j for j in range(3)if bits[3*i+j]]for i in range(2)]+[[]]
        for counts in product((1,2,3),repeat=3):
            ds,_=cooperative_distances(edges,{2},{i for i,n in enumerate(counts)if n==3})
            for root,remaining in product(range(2),range(6)):
                expected=root in ds and ds[root]<=remaining
                assert literal_reachable(edges,root,counts,{2},remaining)==expected
