"""Independent enumeration of feasible integer max-relations."""
from itertools import product
import pytest
from scripts.leaper_path_constraints import max_consistency,constrain
from scripts.leaper_explorer_truth import digest


def test_local_max_interval_narrowing_equals_every_discrete_feasible_completion():
    intervals=([-1,-1],[-1,0],[-1,1],[0,0],[0,1],[1,1])
    for parent in intervals:
        for actions in product(intervals,repeat=3):
            feasible=[vs for vs in product(*(range(lo,hi+1)for lo,hi in actions))if parent[0]<=max(vs)<=parent[1]]
            if not feasible:
                with pytest.raises(ValueError):max_consistency(parent,actions)
            else:
                r,cs=max_consistency(parent,actions)
                assert r==[min(max(v)for v in feasible),max(max(v)for v in feasible)]
                assert cs==[[min(v[i]for v in feasible),max(v[i]for v in feasible)]for i in range(3)]


def fixture(parent_bounds,child_bounds,other_bounds):
    def root(h,ply,bounds,actions):
        return dict(id=h,ply=ply,fingerprint='fp',wdl_bounds=bounds,wdl_fork=None,
                    action_bounds=[dict(action={'id':a},wdl_bounds=b)for a,b in actions])
    roots=[root('p',0,parent_bounds,[('a',[-1,1]),('b',other_bounds)]),
           root('c',1,child_bounds,[('ct',child_bounds)])]
    e=dict(id='p',fingerprint='fp',ply=0,action={'id':'a'},child_id='c',child_ply=1,
           parent_mover=0,child_mover=1,terminal='ongoing',terminal_winner=None)
    local=dict(rows=[])
    t=dict(roots=roots,saved_child_packet_digest=digest(local))
    recorded=dict(input_digest=digest(t),rows=[e])
    return t,recorded,local


def test_known_parent_draw_and_only_remaining_safe_action_solves_unknown_child():
    t,r,l=fixture([0,0],[-1,1],[-1,-1])
    out,changes,stats=constrain(t,r,l)
    roots={r['id']:r for r in out['roots']}
    assert roots['c']['wdl_bounds']==[0,0]
    assert roots['p']['action_bounds'][0]['wdl_bounds']==[0,0]
    assert roots['p']['wdl_fork']is True
    assert stats['child_narrowings']>0


def test_parent_nonloss_does_not_label_arbitrary_unknown_child_winning():
    t,r,l=fixture([0,1],[-1,1],[0,1])
    out,_,_=constrain(t,r,l)
    assert out['roots'][1]['wdl_bounds']==[-1,1]


def test_parent_upper_bound_constrains_each_child_even_with_other_optimal_actions():
    t,r,l=fixture([-1,0],[-1,1],[0,0])
    out,_,_=constrain(t,r,l)
    assert out['roots'][0]['wdl_bounds']==[0,0]
    assert out['roots'][1]['wdl_bounds']==[0,1]


def test_wrong_packet_binding_or_child_rank_rejects():
    t,r,l=fixture([0,0],[-1,1],[-1,-1]);r['rows'][0]['child_ply']=0
    with pytest.raises(ValueError,match='rank'):constrain(t,r,l)
    t,r,l=fixture([0,0],[-1,1],[-1,-1]);l['unbound']='new'
    with pytest.raises(ValueError,match='local edge source'):constrain(t,r,l)
