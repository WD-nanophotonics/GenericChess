"""Observed runtime-view regression and reversible observer contracts, zero queries."""
import ast,json
from scripts.leaper_clock_horizon_trace import instrument,runtime_projection
from scripts import leaper_design as L
from generic_chess.core.search_runtime import SearchPathRuntime

def test_runtime_view_projection_does_not_serialize_mutable_owner():
    c=L.compile_rule(L.definition(5,7));s=L.GameSession(c);r=SearchPathRuntime.from_state(s.state,c)
    start=(r.position,r.ply_count,r.terminal_status,len(r.history))
    with r.pushed(s.legal_actions()[0]):
        projection=runtime_projection(r)
        assert projection['ply_count']==1 and len(projection['history'])==len(r.history)
        assert json.loads(json.dumps(projection))==projection
        assert '_runtime' not in json.dumps(projection)
    assert (r.position,r.ply_count,r.terminal_status,len(r.history))==start

def test_return_observer_preserves_branch_values_and_single_evaluation():
    source='''def q(alpha,beta,ply,qdepth,ctx):
    if qdepth: return ctx()
    return -ctx()
'''
    tree,sites=instrument(source);events=[];ns={'_clock_trace_return':lambda site,value,*args:(events.append((site,value)),value)[1]}
    exec(compile(tree,'<test>','exec'),ns)
    calls=[]
    def value():calls.append(1);return 23
    assert ns['q'](-100,100,0,0,value)==-23
    assert ns['q'](-100,100,0,1,value)==23
    assert len(calls)==2 and [x[1]for x in events]==[-23,23] and len(sites)==2

def test_return_observer_does_not_mask_abort_or_emit_false_return():
    source='''def q(alpha,beta,ply,qdepth,ctx):
    return ctx()
'''
    tree,_=instrument(source);events=[];ns={'_clock_trace_return':lambda *args:events.append(args)}
    exec(compile(tree,'<test>','exec'),ns)
    class Abort(Exception):pass
    def abort():raise Abort()
    import pytest
    with pytest.raises(Abort):ns['q'](0,1,0,0,abort)
    assert not events
