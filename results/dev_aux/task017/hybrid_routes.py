"""Actual Core/Native frontier routes in one fixed small public search."""
import ast,collections,hashlib,json,subprocess,sys,time
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.core.search_runtime import SearchPathRuntime as R
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.core.transition import legal_actions
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta import player as pm
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider as P
import generic_chess.ai.alphabeta.native_legality as provider_module
from generic_chess.ai.limits import SearchLimits
from generic_chess.native import _module
from generic_chess.session.session import GameSession
from scripts.search_backend_comparison import Material
from scripts.research_record import record_value
from scripts.reserve_refresh_diagnostic import stopped
PIN='558b497ba9ab4bd5464274571923959e628cbc03'
blob=subprocess.check_output(['git','show',PIN+':generic_chess/ai/alphabeta/native_legality.py'],cwd=ROOT)
cls=next(n for n in ast.parse(blob).body if isinstance(n,ast.ClassDef) and n.name=='NativeSemanticLegalityProvider')
node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='supports_position')
ns=dict(vars(provider_module));exec(compile(ast.Module(body=[node],type_ignores=[]),'published-support','exec'),ns)
native_module=_module();native_original=native_module.semantic_transient_legal_actions
frontier_original=R.legal_actions;core_original=SemanticEngine.iter_legal_action_bindings;attach_original=R.attach_stats
support_original=P.supports_position;factory_original=pm.SearchStatistics
def clean(value):
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if 'seconds' not in k and not k.startswith('time_')}
    if isinstance(value,list):return [clean(v) for v in value]
    return value
def actual(rt):
    return frozenset(collections.Counter((h,e.identity,int(e.count)) for h,b in rt._occurrences.items() for e in b).items())
def state(rt):
    return (rt.position,rt.ply_count,rt.terminal_status,rt.current_identity,rt.runtime_hash,rt._snapshot,
        tuple(rt.history),rt._history_context,actual(rt),frozenset(rt._opaque_imported_keys),frozenset(rt._history_aliases.items()))
def attach(rt,stats):
    result=attach_original(rt,stats);runtimes.append((rt,state(rt)));return result
def native(*args,**kwargs):
    assert active_event is not None
    active_event['C_entries']+=1
    result=native_original(*args,**kwargs);active_event['C_returns']+=1;return result
def core(*args,**kwargs):
    ev=active_event
    if ev is not None:ev['Core_iterator_entries']+=1
    for value in core_original(*args,**kwargs):
        if ev is not None:ev['Core_iterator_yields']+=1
        yield value
def frontier(rt,*args,**kwargs):
    global active_event
    previous=active_event
    ev={'id':len(events)+1,'ply':rt.ply_count,'terminal':rt.terminal_status.status.value,
        'cache_hit_before':rt._legal_cache is not None,'accepted_before':rt.legal_provider_calls,
        'fallback_before':rt.legal_provider_fallbacks,'C_entries':0,'C_returns':0,'Core_iterator_entries':0,'Core_iterator_yields':0}
    events.append(ev);active_event=ev
    try:
        result=frontier_original(rt,*args,**kwargs);ev['actions']=len(result);return result
    finally:
        ev['accepted_delta']=rt.legal_provider_calls-ev['accepted_before']
        ev['fallback_delta']=rt.legal_provider_fallbacks-ev['fallback_before'];active_event=previous
rows=[];started=time.monotonic()
compat=compile_ruleset_for_execution(replace(build_builtin_ruleset('standard_shogi'),max_ply=2))
pure=CompiledSemanticRuleset(ir=compat.ir,support=compat.support)
try:
    P.supports_position=ns['supports_position'];R.legal_actions=frontier;R.attach_stats=attach
    for carrier,compiled in [('compat',compat),('pure',pure)]:
        expected=set(legal_actions(GameSession(compiled).state,compiled))
        for requested in (False,True):
            for order in range(2):
                signatures=[]
                for measured in ((False,True) if order==0 else (True,False)):
                    stopped();assert time.monotonic()-started<120
                    events=[];active_event=None;runtimes=[];captured=[]
                    native_module.semantic_transient_legal_actions=native if measured else native_original
                    SemanticEngine.iter_legal_action_bindings=core if measured else core_original
                    def factory():
                        s=SearchStatistics();captured.append(s);return s
                    pm.SearchStatistics=factory
                    session=GameSession(compiled);before=(session.state,session._search_witnesses)
                    decision=AlphaBetaPlayer(compiled,evaluator_override=Material('shogi'),use_disk_cache=False,use_tt=False,
                        use_ordering=False,use_native_semantic_legality=requested,tuning=SearchTuning(use_root_tactical=False)).choose_action(
                        session,SearchLimits(max_depth=2,max_nodes=2048,max_time_seconds=10,quiescence_max_depth=0,quiescence_hard_max_depth=0))
                    assert session.state is before[0] and session._search_witnesses==before[1]
                    assert decision.completed_depth==2 and decision.action in expected
                    assert len(runtimes)==len(captured)==1
                    rt,root=runtimes[0];rt.assert_balanced();assert state(rt)==root and active_event is None
                    stats=clean(record_value(captured[0]));d=clean(record_value(decision))
                    diagnostic={'C_entries','C_returns','Core_iterator_entries','Core_iterator_yields'}
                    semantic_events=[{k:v for k,v in ev.items() if k not in diagnostic} for ev in events]
                    sig={'decision':d,'stats':stats,'frontier_events':semantic_events}
                    signatures.append(sig)
                    assert sum(ev['accepted_delta'] for ev in events)==stats['native_legality_calls']
                    assert sum(ev['fallback_delta'] for ev in events)==stats['native_legality_fallbacks']
                    assert stats['native_legality_operational_failures']==0
                    if measured:
                        assert sum(ev['C_entries'] for ev in events)==sum(ev['C_returns'] for ev in events)==stats['native_legality_calls']
                        if requested:
                            assert stats['native_legality_enabled']==1
                            assert stats['native_legality_calls']>=1 and stats['native_legality_fallbacks']>=1
                            assert all(ev['ply']==0 for ev in events if ev['C_returns'])
                            assert all(ev['ply']==1 for ev in events if ev['fallback_delta'])
                    rows.append({'carrier':carrier,'native_requested':requested,'order':order,'measured':measured,
                        'decision':d,'stats':stats,'events':events,'actual_root_multiset_restored':True})
                    print(carrier,requested,order,measured,'depth',decision.completed_depth,'nodes',decision.nodes,
                        'accepted',stats['native_legality_calls'],'fallback',stats['native_legality_fallbacks'],
                        'C',sum(ev['C_returns'] for ev in events),'Core',sum(ev['Core_iterator_entries'] for ev in events),flush=True)
                assert signatures[0]==signatures[1]
finally:
    native_module.semantic_transient_legal_actions=native_original;SemanticEngine.iter_legal_action_bindings=core_original
    R.legal_actions=frontier_original;R.attach_stats=attach_original;P.supports_position=support_original;pm.SearchStatistics=factory_original
# Different backend work fields are retained; only semantic output is aligned.
outputs={(row['carrier'],row['native_requested']):{k:row['decision'][k] for k in ('action','score','principal_variation','completed_depth','nodes','qnodes')} for row in rows}
assert all(value==next(iter(outputs.values())) for value in outputs.values())
out={'complete':True,'baseline':'b4108a68a7ee06327be39cb3a222939644085a52','published_support_method_pin':PIN,
    'evaluator':'frozen arbitrary Material(shogi), same own tracked implementation in all arms; no default price profile',
    'scope':'16 actual fixed D2 capability-crossing callers; selected Core full-frontier iterators only; no timing or generality/strength claim',
    'rows':rows}
(Path(__file__).parent/'hybrid_routes.json').write_text(json.dumps(out,indent=2)+'\n')
