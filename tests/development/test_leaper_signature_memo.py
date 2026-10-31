"""Pure serializer equivalence, no Player queries in these unit controls."""
from types import SimpleNamespace
from dataclasses import replace
from scripts.leaper_signature_memo import canonical,signature_for,reset,COUNTERS
from generic_chess.core.actions import SemanticBoardMove,PassAction
from generic_chess.core.coordinates import Square

def action(i=0):
    return SemanticBoardMove(pattern_id='p'+str(i),geometry_id='g0',actor_type_id='A',from_square=Square(0,0),to_square=Square(1,1))

def owner(admitted=True):return SimpleNamespace(_signature_cache={},_signature_admitted=admitted)

def test_full_public_syntax_cached_exactly():
    reset();o=owner();a=action();expected=canonical(a)
    assert signature_for(o,a)==expected==signature_for(o,a)
    assert COUNTERS['hits']==1 and COUNTERS['misses']==1
    for b in [replace(a,pattern_id='other'),replace(a,geometry_id='g1'),replace(a,actor_type_id='B'),replace(a,to_square=Square(2,2)),replace(a,promotion_target_id='Z')]:
        assert signature_for(o,b)==canonical(b)!=expected
    assert len(o._signature_cache)==6

def test_bounded_clear_and_no_cross_runtime_state():
    reset();o=owner()
    for i in range(4100):assert signature_for(o,action(i))==canonical(action(i))
    assert COUNTERS['peak_entries']==4096 and COUNTERS['clears']==1
    other=owner();assert not other._signature_cache

def test_unsupported_and_nonadmitted_are_original_fallback():
    reset();o=owner(False);a=action()
    assert signature_for(o,a)==canonical(a) and not o._signature_cache
    p=PassAction();o=owner()
    assert signature_for(o,p)==canonical(p) and not o._signature_cache
    assert COUNTERS['fallbacks']==2

def test_actual_Player_work_undo_and_exact_history_signature(tmp_path):
    from test_leaper_threat_ordering import fixture
    from scripts.leaper_signature_memo import installed,reset
    from scripts.leaper_boolean_cost_pilot import signature
    from scripts.research_record import record_value,write_record
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.limits import SearchLimits
    from contextlib import nullcontext
    c,s=fixture();before=s.to_record();values=[]
    for enabled in (False,True):
        reset()
        with installed() if enabled else nullcontext():
            d=AlphaBetaPlayer(c,use_disk_cache=False).choose_action(s,SearchLimits(max_depth=2,max_nodes=50000,quiescence_max_depth=0))
        write_record(tmp_path/(str(enabled)+'.json'),{'decision':record_value(d),'cache':dict(COUNTERS)})
        assert s.to_record()==before and d.runtime_depth_balanced and d.completed_depth==2
        if enabled:assert COUNTERS['runtimes']==1 and COUNTERS['hits']>0
        values.append(signature(record_value(d)))
    assert values[0]==values[1]

def test_bool_int_public_action_alias_keeps_distinct_original_JSON():
    reset();o=owner();a=action();alias=replace(a,from_square=Square(False,0))
    assert a==alias and canonical(a)!=canonical(alias)
    assert signature_for(o,a)==canonical(a)
    assert signature_for(o,alias)==canonical(alias)
    assert len(o._signature_cache)==1 and COUNTERS['fallbacks']==1

def test_installed_runtime_restores_after_baseexception():
    from scripts.leaper_signature_memo import installed,BASE
    import generic_chess.ai.alphabeta.search as search
    class Halt(BaseException):pass
    try:
        with installed():
            assert search.SearchPathRuntime is not BASE
            raise Halt()
    except Halt:pass
    assert search.SearchPathRuntime is BASE
