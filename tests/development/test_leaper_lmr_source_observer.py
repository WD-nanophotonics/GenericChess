"""Observed-need controls: dispatch counts, bounded capture and exception unwind."""
from types import SimpleNamespace
import pytest
from scripts.leaper_lmr_source_observer import DispatchObserver,work_signature
from generic_chess.ai.alphabeta.statistics import SearchStatistics


def exercise(limit,explode=False):
    ctx=SimpleNamespace(runtime=SimpleNamespace(position=object(),terminal_status=object()),stats=SearchStatistics())
    observer=None
    def original(state,depth,alpha,beta,ply,ctx,**kw):
        ctx.stats.nodes+=1
        if depth==0:return SimpleNamespace(score=42)
        if explode and depth==1:raise RuntimeError('synthetic_stop')
        move_index=4
        def child_search():
            return observer(state,depth-1,alpha,beta,ply+1,ctx,pv_node=False,prev_action='synthetic')
        return child_search()
    observer=DispatchObserver(original,limit)
    return ctx,observer


def test_dispatch_predicate_and_sample_bound_are_separate():
    ctx,o=exercise(1);r=o(None,4,-10,10,0,ctx)
    assert r.score==42 and ctx.stats.nodes==5 and not o.stack
    assert o.counts['all_main_entries']==5 and o.counts['late_nonPV_dispatches']==1
    assert len(o.samples)==1 and o.discarded==0
    x=o.samples[0]
    assert x['parent_depth']==3 and x['parent_ply']==1 and x['child_depth']==2
    assert x['node_delta']==3 and x['status']=='RETURNED'
    ctx,z=exercise(0);z(None,4,-10,10,0,ctx)
    assert z.counts['late_nonPV_dispatches']==1 and z.discarded==1 and not z.samples


def test_exception_propagates_and_every_frame_is_unwound():
    ctx,o=exercise(4,True)
    with pytest.raises(RuntimeError,match='synthetic_stop'):o(None,4,-10,10,0,ctx)
    assert not o.stack and o.samples[0]['status']=='EXCEPTION'
    assert o.samples[0]['error_type']=='RuntimeError'


def test_work_signature_excludes_time_but_keeps_actual_work_and_policy():
    a=SearchStatistics();b=SearchStatistics();b.evaluation_seconds=1.0;b.ordering_seconds=2.0
    assert work_signature(a)==work_signature(b)
    b.qnodes+=1
    assert work_signature(a)!=work_signature(b)
