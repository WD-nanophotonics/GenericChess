"""Independent discrete WDL completions test one-ply/cardinality deductions."""
from itertools import product
from copy import deepcopy
import pytest
from scripts.leaper_local_truth import derive,apply_layer
from scripts.leaper_explorer_truth import digest


def child(lo,hi,terminal='ongoing',winner=None):
    return dict(wdl_bounds=[lo,hi],terminal=terminal,terminal_winner=winner)


def test_every_interval_fork_deduction_against_all_discrete_completions():
    intervals=((-1,-1),(0,0),(1,1),(-1,0),(0,1),(-1,1))
    for n in (1,2,3):
        for bs in product(intervals,repeat=n):
            choices=[range(lo,hi+1)for lo,hi in bs]
            truths={len(set(vs))>1 for vs in product(*choices)}
            actual=next(iter(truths))if len(truths)==1 else None
            d=derive([child(*b)for b in bs])
            assert d['wdl_fork']is actual
            possible_root=[max(vs)for vs in product(*choices)]
            assert d['wdl_bounds']==[min(possible_root),max(possible_root)]


def test_single_unknown_action_closes_fork_only_not_wdl_or_cooperation():
    d=derive([child(-1,1)])
    assert d['wdl_fork']is False and d['wdl_bounds']==[-1,1]
    assert d['cooperative_decisive']is d['universal_draw']is None


def test_real_terminal_win_and_draw_branches_prove_fork_without_search():
    d=derive([child(1,1,'checkmate',0),child(0,0,'max_ply')])
    assert d==dict(wdl_bounds=[1,1],wdl_fork=True,cooperative_decisive=True,universal_draw=False)


def test_no_contest_is_not_a_draw_or_negative_cooperative_certificate():
    d=derive([child(-1,1,'no_contest')])
    assert d['wdl_bounds']==[-1,1]and d['universal_draw']is None


def test_layer_is_source_bound_and_cannot_contradict_a_known_label():
    truth=dict(roots=[dict(id='h',fingerprint='fp',wdl_bounds=[-1,1],wdl_fork=None,
        cooperative_decisive=None,universal_draw=None)])
    children=[child(1,1,'checkmate',0)|dict(action={'test':'synthetic'})]
    layer=dict(input_digest=digest(truth),rows=[dict(id='h',fingerprint='fp',children=children,derived=derive(children))])
    out=apply_layer(truth,layer)
    assert out['roots'][0]['wdl_bounds']==[1,1]and truth['roots'][0]['wdl_bounds']==[-1,1]
    forged=deepcopy(layer);forged['input_digest']='wrong'
    with pytest.raises(ValueError):apply_layer(truth,forged)
    bad=deepcopy(layer);bad['rows'][0]['derived']['wdl_fork']=True
    with pytest.raises(ValueError):apply_layer(truth,bad)
