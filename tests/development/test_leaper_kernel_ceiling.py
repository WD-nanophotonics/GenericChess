from scripts.leaper_kernel_ceiling import NestedWall,partition

def test_nested_ownership_and_restoration():
    times=iter([0,2,7,10]);o=NestedWall(lambda:next(times))
    class Sample:
        def child(self):return 3
        def parent(self):return self.child()+1
    original=Sample.child;s=Sample()
    with o.installed([(Sample,'parent','outer'),(Sample,'child','inner')]):assert s.parent()==4
    assert Sample.child is original and not o.stack
    assert o.rows['outer']['inclusive_ns']==10 and o.rows['outer']['self_ns']==5
    assert o.rows['inner']['self_ns']==5 and sum(r['self_ns'] for r in o.rows.values())==10

def test_baseexception_propagates_and_restores():
    class Halt(BaseException):pass
    class Sample:
        def f(self):raise Halt('stop')
    original=Sample.f;o=NestedWall();s=Sample()
    try:
        with o.installed([(Sample,'f','halt')]):s.f()
    except Halt as e:assert str(e)=='stop'
    else:assert False
    assert Sample.f is original and o.rows['halt']['exceptions']==1 and not o.stack

def test_partition_does_not_sum_inclusive_nested_costs():
    r={'native_check':{'self_ns':20},'native_import':{'self_ns':30},'leaf_evaluation':{'self_ns':40}}
    p=partition(r,1e-6)
    assert abs(p['broad_observed_union_seconds']-50e-9)<1e-15
    assert abs(p['transport_binding_observed_union_seconds']-30e-9)<1e-15

def test_actual_Player_work_and_undo_parity():
    from test_leaper_threat_ordering import fixture
    from scripts.leaper_boolean_cost_pilot import signature
    from scripts.leaper_kernel_ceiling import targets
    from scripts.research_record import record_value
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.limits import SearchLimits
    c,s=fixture();before=s.to_record();values=[]
    for enabled in (False,True):
        p=AlphaBetaPlayer(c,use_disk_cache=False)
        if enabled:
            o=NestedWall()
            with o.installed(targets()):d=p.choose_action(s,SearchLimits(max_depth=2,max_nodes=50000,quiescence_max_depth=0))
            assert o.rows['runtime_push']['calls']==d.runtime_pushes and not o.stack
        else:d=p.choose_action(s,SearchLimits(max_depth=2,max_nodes=50000,quiescence_max_depth=0))
        assert d.completed_depth==2 and d.runtime_depth_balanced and before==s.to_record()
        values.append(signature(record_value(d)))
    assert values[0]==values[1]
