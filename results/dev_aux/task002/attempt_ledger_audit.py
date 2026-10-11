"""Transparent diagnostic adapters retain failed-attempt and outside phase values."""
import sys,time,json,collections,importlib.util,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
B=ROOT/'.local_agent/availability-core-20261011'
spec=importlib.util.spec_from_file_location('physical_probe',B/'physical_outcome.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
c=m.c;p=m.p;T=m.T
from generic_chess.ai.alphabeta import player as pm
from generic_chess.ai.alphabeta.statistics import SearchStatistics
original_factory=pm.SearchStatistics
class Token:
    def __init__(self):self.flag=False;self.observed=0
    def is_cancelled(self):self.observed+=1;return self.flag
class CaptureStack(list):
    def append(self,value):
        current['values']=value
        super().append(value)
class PhaseCounter(collections.Counter):
    def __setitem__(self,key,value):
        delta=value-self.get(key,0)
        outside_phases[(c.iteration,bool(c.qlevel),key)]+=delta
        super().__setitem__(key,value)
def observed(name,fn):
    def call(*args,**kwargs):
        key=(current is not None,c.iteration,bool(c.qlevel),name)
        method_entries[key]+=1
        result=fn(*args,**kwargs)
        if name=='transition' and current is not None and current['iteration']==2 and current['qphase'] and trigger is None:
            global_trigger({'iteration':2,'qphase':True,'attempt':len(events)+1,'after':'transition'})
        return result
    return call
def global_trigger(value):
    global trigger
    trigger=value;token.flag=True
rows=[];started=time.monotonic()
compiled=c.compile_ruleset_for_execution(c.build_builtin_ruleset('western_chess'));board=c.CoreBoard(c.CASES[0],compiled);e=c.cm.w.weighted(compiled,c.VALUES['chess'])
for order in range(2):
    pair=[]
    for measured in ((False,True) if order==0 else (True,False)):
        c.stopped();assert time.monotonic()-started<180
        p.stack=CaptureStack();p.pending={};p.totals=collections.Counter();p.peak=0;c.iteration=c.qlevel=0;c.counts=collections.Counter();m.calls=[]
        outside_phases=collections.Counter();m.outside=PhaseCounter();method_entries=collections.Counter();events=[];current=None;trigger=None;token=Token();captured=[]
        # Identical method-entry/trigger observer under the original stage wrappers.
        saved=m.originals[:];m.originals[:]=[observed(name,fn) for (_,_,name),fn in zip(m.targets,saved)]
        m.install(measured);c.sm.negamax=c.negamax;c.sm._quiescence_runtime=c.quiescence
        wrapped=T._push_impl
        def counted(self,*args,**kwargs):
            global current
            event={'iteration':c.iteration,'qphase':bool(c.qlevel),'values':collections.Counter()}
            current=event
            try:result=wrapped(self,*args,**kwargs)
            except BaseException:event['status']='failed';raise
            else:event['status']='successful';return result
            finally:
                event['values']=dict(event['values']);events.append(event);current=None
        T._push_impl=counted
        def factory():
            value=SearchStatistics();captured.append(value);return value
        pm.SearchStatistics=factory
        s=c.GameSession(compiled);s._state=board.initial;s._search_history_witnesses=board.witnesses;before=(s.state,s._search_history_witnesses)
        try:d=c.AlphaBetaPlayer(compiled,evaluator_override=e,use_native_semantic_legality=True,use_disk_cache=False).choose_action(s,c.SearchLimits(max_depth=2,max_nodes=32768,max_time_seconds=10,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel_token=token)
        finally:
            m.originals[:]=saved;m.install(False);pm.SearchStatistics=original_factory
        assert s.state is before[0] and s._search_history_witnesses==before[1]
        assert not m.calls and not p.stack and not p.pending
        stats=c.cm.clean(c.record_value(captured[0]));decision=c.cm.clean(c.record_value(d))
        for ev in events:ev['disposition']='outside_iteration' if ev['iteration']==0 else ('completed' if ev['iteration']<=d.completed_depth else 'aborted')
        success=[ev for ev in events if ev['status']=='successful'];failed=[ev for ev in events if ev['status']=='failed']
        assert len(success)==stats['runtime_pushes']==stats['runtime_pops']
        assert trigger is not None and len(failed)==1 and d.completed_depth==1
        if measured:
            assert sum(v for (i,q,o,k),v in p.totals.items() if k=='children')==len(success)
            for (_,_,name) in m.targets:
                key=name+'_calls'
                all_entries=sum(v for (inside,i,q,n),v in method_entries.items() if n==name)
                captured_entries=sum(ev['values'].get(key,0) for ev in events)+m.outside.get(key,0)
                assert all_entries==captured_entries,(name,all_entries,captured_entries)
                original_success=sum(v for (i,q,o,k),v in p.totals.items() if k==key)
                assert original_success==sum(ev['values'].get(key,0) for ev in success)
            for key,val in m.outside.items():assert abs(val-sum(v for (i,q,k),v in outside_phases.items() if k==key))<1e-9
        signature={'decision':decision,'stats':stats,'trigger':trigger,'events':[{k:v for k,v in ev.items() if k!='values'} for ev in events],'budget_observations':token.observed,'method_entries':[{'inside_push':inside,'iteration':i,'qphase':q,'stage':name,'calls':value} for (inside,i,q,name),value in sorted(method_entries.items())]}
        pair.append(signature)
        rows.append({'order':order,'measured':measured,**signature,'events_with_values':events,'original_stages':[{'iteration':i,'qphase':q,'outcome':o,'metric':k,'value':v} for (i,q,o,k),v in sorted(p.totals.items())],'outside_phases':[{'iteration':i,'qphase':q,'metric':k,'value':v} for (i,q,k),v in sorted(outside_phases.items())]})
    assert pair[0]==pair[1],order
report={'complete':True,'scope':'diagnostic adapters only; failed values/phase outside values retained; selected count conservation; descriptive seconds only','producer_sha256':hashlib.sha256((B/'physical_outcome.py').read_bytes()).hexdigest(),'rows':rows}
(Path(__file__).parent/'attempt_ledger.json').write_text(json.dumps(report,indent=2)+'\n')
for row in rows:
    counts=collections.Counter((ev['disposition'],ev['status']) for ev in row['events'])
    failed=[ev for ev in row['events_with_values'] if ev['status']=='failed']
    print(row['order'],row['measured'],'completed',row['decision']['completed_depth'],'counts',dict(counts),'failed values',failed[0]['values'])
