from fractions import Fraction as F
import pytest
from scripts.compatible_contact import SourceNode,contact_steps,discounted_contact_interval,integrate_contact_intervals


def event(current,source,destination,*,result=None,capture=False,extra=()):
    label='enemy' if capture else 'empty'
    key=(0,current,source,destination,label,((destination,'capture_to_hand'),) if capture else (),result or current)
    return key,(((destination,(label,)),*extra),)


def apply(node,events,*,target=2,blockers=None,goal_only=False):
    return contact_steps(node,events,area=4,owner=0,target=target,blockers=blockers or {},goal_only=goal_only)


def test_source_vacates_before_next_definite_occupancy_query():
    first,cube=event('R',0,1)
    steps=apply(SourceNode('R','R',0),{first:cube})
    next_node=steps[first].node
    second,need_old_empty=event('R',1,2,capture=True,extra=((0,('empty',)),))
    result=apply(next_node,{second:need_old_empty})
    assert result[second].completed and result[second].node.square==2
    # A stale board retaining source0 would reject this compatible path.
    assert next_node==SourceNode('R','R',1)


def test_promotion_changes_future_movements_without_erasing_native_origin():
    quiet,cube=event('P',0,1,result='G')
    promoted=apply(SourceNode('P','P',0),{quiet:cube})[quiet].node
    native_capture,nc=event('P',1,2,capture=True)
    gold_capture,gc=event('G',1,2,capture=True)
    result=apply(promoted,{native_capture:nc,gold_capture:gc})
    assert set(result)=={gold_capture}
    assert result[gold_capture].node.base=='P'


def test_fixed_blocker_and_event_union_do_not_become_union_graph_edges():
    capture,cube=event('R',0,2,capture=True,extra=((1,('empty',)),))
    assert not apply(SourceNode('R','R',0),{capture:cube},blockers={1:'own'})
    # Duplicate descriptions with compatible cubes preserve ONE physical event.
    result=apply(SourceNode('R','R',0),{capture:cube+cube})
    assert len(result)==1 and result[capture].completed
    with pytest.raises(ValueError):apply(result[capture].node,{capture:cube})


def test_goal_only_is_not_a_full_quiet_choice_set():
    quiet,qc=event('R',0,1);capture,cc=event('R',0,2,capture=True)
    full=apply(SourceNode('R','R',0),{quiet:qc,capture:cc})
    goal=apply(SourceNode('R','R',0),{quiet:qc,capture:cc},goal_only=True)
    assert len(full)==2 and set(goal)=={capture}


def test_bounds_contain_independent_tiny_chain_distance_and_unknown_frontier():
    # Independent explicit path count:0->1->2->3, contact at3 costs3.
    chain={0:(1,),1:(2,),2:(3,),3:()}
    frontier={0};depth=0
    while 3 not in frontier:
        frontier={n for s in frontier for n in chain[s]};depth+=1
    assert depth==3
    gamma=F(2,3);truth=gamma**depth
    for excluded in range(depth):
        lo,hi=discounted_contact_interval(gamma,excluded_through=excluded,witness_length=depth)
        assert lo<=truth<=hi
    assert discounted_contact_interval(gamma,excluded_through=2,witness_length=3)==(truth,truth)
    assert discounted_contact_interval(gamma,excluded_through=1)==(0,gamma**2)
    assert discounted_contact_interval(gamma,excluded_through=1,unreachable=True)==(0,0)


def test_unknown_demand_mass_never_disappears():
    assert integrate_contact_intervals({'known':F(1,4),'unknown':F(3,4)},
                                      {'known':(F(1,2),F(1,2)),'unknown':(0,1)})==(F(1,8),F(7,8))
    with pytest.raises(ValueError):integrate_contact_intervals({'known':F(1,4)},{'known':(0,1)})


def test_malformed_semantics_and_worlds_fail_closed():
    node=SourceNode('R','R',0);key,cube=event('R',0,2,capture=True)
    # An unsatisfied cube is a ruled-out edge, not unsupported semantics.
    assert not apply(node,{key:(((2,('own',)),),)})
    cases=[({(0,'R',0,2,'enemy',(),'R'):cube},{}),
           ({(0,'R',0,2,'enemy',((1,'capture_to_hand'),),'R'):cube},{}),
           ({(0,'R',0,2,'enemy',((2,'invented'),),'R'):cube},{}),
           ({key:(((4,('enemy',)),),)},{}),({key:cube},{1:'enemy'}),({key:cube},{0:'own'})]
    for events,blockers in cases:
        with pytest.raises(ValueError):apply(node,events,blockers=blockers)
    with pytest.raises(ValueError):apply(SourceNode(1,'R',0),{key:cube})


def test_incoherent_distance_proofs_and_nonexact_discount_rejected():
    for kwargs in [dict(gamma=0.5,excluded_through=0),dict(gamma=1,excluded_through=0),
                   dict(gamma=F(1,2),excluded_through=-1),dict(gamma=F(1,2),excluded_through=2,witness_length=2),
                   dict(gamma=F(1,2),excluded_through=0,witness_length=1,unreachable=True)]:
        with pytest.raises(ValueError):discounted_contact_interval(**kwargs)


def test_goal_only_still_counts_quiet_choices_against_cap():
    quiet,qc=event('R',0,1);capture,cc=event('R',0,2,capture=True)
    with pytest.raises(ValueError,match='cap exceeded'):
        contact_steps(SourceNode('R','R',0),{quiet:qc,capture:cc},area=4,owner=0,
                      target=2,blockers={},goal_only=True,max_choices=1)


def test_materialization_checkpoint_precedes_creation_and_propagates_limit():
    quiet,qc=event('R',0,1);capture,cc=event('R',0,2,capture=True)
    calls=[]
    def cap():
        calls.append('before')
        raise RuntimeError('materialization budget exhausted')
    with pytest.raises(RuntimeError,match='budget exhausted'):
        contact_steps(SourceNode('R','R',0),{quiet:qc,capture:cc},area=4,owner=0,
                      target=2,blockers={},checkpoint=cap)
    assert calls==['before']
