"""Join real C returns, provider attempts and phases in interrupted callers."""
import sys,time,json,collections,importlib.util,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
B=ROOT/'.local_agent/availability-core-20261011'
spec=importlib.util.spec_from_file_location('physical_probe',B/'physical_outcome.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
c=m.c;p=m.p;T=m.T
from generic_chess.ai.alphabeta import player as pm
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.native import _module
mod=_module();native_original=mod.semantic_transient_legal_actions
provider_original=T._legal_actions_from_provider;attach_original=T.attach_stats
factory_original=pm.SearchStatistics
class Token:
    def __init__(self):self.flag=False;self.observed=0
    def is_cancelled(self):self.observed+=1;return self.flag
class CaptureStack(list):
    def append(self,value):
        current['values']=value
        super().append(value)
def multiset(rt):
    return frozenset(collections.Counter((h,e.identity,int(e.count)) for h,b in rt._occurrences.items() for e in b).items())
def rootstate(rt):
    return (rt.position,rt.ply_count,rt.terminal_status,rt.current_identity,rt.runtime_hash,rt._snapshot,tuple(rt.history),rt._history_context,frozenset(rt._opaque_imported_keys),frozenset(rt._history_aliases.items()),multiset(rt))
def attach(rt,stats):
    result=attach_original(rt,stats);captured_runtime.append((rt,rootstate(rt)));return result
def native(*args,**kw):
    global trigger
    assert active_provider is not None
    ev={'provider_id':active_provider['id'],'iteration':c.iteration,'qphase':bool(c.qlevel),'push_id':None if current is None else current['id'],'returned':False}
    c_events.append(ev)
    result=native_original(*args,**kw);ev['returned']=True
    hit=(c.iteration==0) if target=='root' else (c.iteration==2 and bool(c.qlevel))
    if trigger is None and hit:
        trigger={'target':target,'C_event':len(c_events),'iteration':c.iteration,'qphase':bool(c.qlevel),'push_id':ev['push_id']}
        token.flag=True
    return result
def provider(rt,*args,**kw):
    global active_provider
    ev={'id':len(providers)+1,'iteration':c.iteration,'qphase':bool(c.qlevel),'push_id':None if current is None else current['id'],'accepted_before':rt.legal_provider_calls,'C_before':len(c_events)}
    providers.append(ev);previous=active_provider;active_provider=ev
    try:
        result=provider_original(rt,*args,**kw)
    except BaseException as exc:
        ev['status']='raised';ev['exception']=type(exc).__name__;raise
    else:
        ev['status']='returned';ev['Core_fallback']=result is None;return result
    finally:
        ev['accepted_delta']=rt.legal_provider_calls-ev['accepted_before']
        ev['C_delta']=len(c_events)-ev['C_before'];active_provider=previous
rows=[];started=time.monotonic()
compiled=c.compile_ruleset_for_execution(c.build_builtin_ruleset('western_chess'));board=c.CoreBoard(c.CASES[0],compiled)
evaluator=c.cm.w.weighted(compiled,c.VALUES['chess'])
try:
    mod.semantic_transient_legal_actions=native;T._legal_actions_from_provider=provider;T.attach_stats=attach
    for target in ('root','iteration2_q'):
        for order in range(2):
            pair=[]
            for measured in ((False,True) if order==0 else (True,False)):
                c.stopped();assert time.monotonic()-started<120
                p.stack=CaptureStack();p.pending={};p.totals=collections.Counter();p.peak=0
                c.iteration=c.qlevel=0;c.counts=collections.Counter();m.calls=[];m.outside=collections.Counter()
                current=None;active_provider=None;trigger=None;token=Token();events=[];providers=[];c_events=[];captured=[];captured_runtime=[]
                m.install(measured);c.sm.negamax=c.negamax;c.sm._quiescence_runtime=c.quiescence
                wrapped=T._push_impl
                def counted(rt,*args,**kw):
                    global current
                    previous=current
                    event={'id':len(events)+1,'iteration':c.iteration,'qphase':bool(c.qlevel),'values':collections.Counter()}
                    current=event;events.append(event)
                    try:result=wrapped(rt,*args,**kw)
                    except BaseException as exc:event['status']='failed';event['exception']=type(exc).__name__;raise
                    else:event['status']='successful';return result
                    finally:event['values']=dict(event['values']);current=previous
                T._push_impl=counted
                def factory():
                    stats=SearchStatistics();captured.append(stats);return stats
                pm.SearchStatistics=factory
                session=c.GameSession(compiled);session._state=board.initial;session._search_history_witnesses=board.witnesses
                before=(session.state,session._search_history_witnesses)
                try:
                    decision=c.AlphaBetaPlayer(compiled,evaluator_override=evaluator,use_native_semantic_legality=True,use_disk_cache=False).choose_action(session,c.SearchLimits(max_depth=2,max_nodes=32768,max_time_seconds=10,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel_token=token)
                finally:m.install(False);pm.SearchStatistics=factory_original
                assert trigger is not None
                assert session.state is before[0] and session._search_history_witnesses==before[1]
                assert not m.calls and not p.stack and not p.pending and current is None and active_provider is None
                assert len(captured_runtime)==1
                runtime,root_before=captured_runtime[0];assert rootstate(runtime)==root_before
                runtime.assert_balanced()
                stats=c.cm.clean(c.record_value(captured[0]));d=c.cm.clean(c.record_value(decision))
                for ev in events+providers+c_events:
                    ev['disposition']='outside_iteration' if ev['iteration']==0 else ('completed' if ev['iteration']<=decision.completed_depth else 'aborted')
                assert len(c_events)==sum(ev['C_delta'] for ev in providers)
                assert sum(ev['returned'] for ev in c_events)==len(c_events)
                assert stats['native_legality_calls']==sum(ev['accepted_delta'] for ev in providers)
                assert len(c_events)-stats['native_legality_calls']==1
                assert stats['runtime_pushes']==stats['runtime_pops']==sum(ev['status']=='successful' for ev in events)
                assert stats['native_legality_fallbacks']==stats['native_legality_operational_failures']==0
                assert decision.completed_depth==(0 if target=='root' else 1)
                signature={'decision':d,'stats':stats,'trigger':trigger,'budget_observations':token.observed,
                    'push_events':[{k:v for k,v in ev.items() if k!='values'} for ev in events],
                    'provider_attempts':providers,'C_events':c_events,'actual_multiset_root_restored':True}
                pair.append(signature)
                rows.append({'target':target,'order':order,'measured':measured,**signature,
                    'push_events_with_values':events,
                    'outside_selected_stages':dict(m.outside),
                    'original_completed_child_stages':[{'iteration':i,'qphase':q,'outcome':o,'metric':k,'value':v} for (i,q,o,k),v in sorted(p.totals.items())]})
                print(target,order,measured,'C',len(c_events),'accepted',stats['native_legality_calls'],'depth',decision.completed_depth,'trigger',trigger,flush=True)
            assert pair[0]==pair[1],(target,order)
finally:
    m.install(False);pm.SearchStatistics=factory_original
    mod.semantic_transient_legal_actions=native_original;T._legal_actions_from_provider=provider_original;T.attach_stats=attach_original
out={'complete':True,'baseline':'b4108a68a7ee06327be39cb3a222939644085a52',
    'native_binary_sha256':hashlib.sha256((ROOT/'generic_chess/_native_core.cp312-win_amd64.pyd').read_bytes()).hexdigest(),
    'scope':'eight frozen real caller controls; transparent entry observers in both arms; no timing claim; diagnostic C execution excludes opaque internal C work','rows':rows}
(Path(__file__).parent/'search_native_ledger.json').write_text(json.dumps(out,indent=2)+'\n')
