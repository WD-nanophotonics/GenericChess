"""Phase-targeted cancellation on unchanged pinned search, no wall comparison."""
import sys,time,json,importlib.util,collections,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
B=ROOT/'.local_agent/availability-core-20261011'
spec=importlib.util.spec_from_file_location('physical_probe',B/'physical_outcome.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
c=m.c;p=m.p;T=m.T
from generic_chess.ai.alphabeta import player as pm
from generic_chess.ai.alphabeta.statistics import SearchStatistics
original_factory=pm.SearchStatistics
class PhaseCancel:
    def __init__(self):self.flag=False;self.observed=0
    def is_cancelled(self):self.observed+=1;return self.flag
def matches(target):
    return (target=='root' and c.iteration==0) or (target=='main1' and c.iteration==1 and not c.qlevel) or (target=='main2' and c.iteration==2 and not c.qlevel) or (target=='q' and bool(c.qlevel))
rows=[];started=time.monotonic()
compiled=c.compile_ruleset_for_execution(c.build_builtin_ruleset('western_chess'));board=c.CoreBoard(c.CASES[0],compiled);e=c.cm.w.weighted(compiled,c.VALUES['chess'])
for target in ('root','main1','main2','q'):
    for order in range(2):
        pair=[]
        for measured in ((False,True) if order==0 else (True,False)):
            c.stopped();assert time.monotonic()-started<180
            p.stack=[];p.pending={};p.totals=collections.Counter();p.peak=0;c.iteration=c.qlevel=0;c.counts=collections.Counter();m.calls=[];m.outside=collections.Counter()
            m.install(measured)
            c.sm.negamax=c.negamax;c.sm._quiescence_runtime=c.quiescence
            wrapped=T._push_impl;attempts=collections.Counter();events=[];captured=[];token=PhaseCancel();trigger=None
            def counted(self,*args,**kwargs):
                global trigger
                phase=(c.iteration,bool(c.qlevel));attempts['attempted']+=1
                if trigger is None and matches(target):
                    token.flag=True;trigger={'iteration':phase[0],'qphase':phase[1],'attempt':attempts['attempted']}
                try:result=wrapped(self,*args,**kwargs)
                except BaseException:
                    attempts['failed']+=1;events.append({'iteration':phase[0],'qphase':phase[1],'status':'failed'});raise
                else:
                    attempts['successful']+=1;events.append({'iteration':phase[0],'qphase':phase[1],'status':'successful'});return result
            T._push_impl=counted
            def factory():
                value=SearchStatistics();captured.append(value);return value
            pm.SearchStatistics=factory
            s=c.GameSession(compiled);s._state=board.initial;s._search_history_witnesses=board.witnesses;before=(s.state,s._search_history_witnesses)
            try:d=c.AlphaBetaPlayer(compiled,evaluator_override=e,use_native_semantic_legality=True,use_disk_cache=False).choose_action(s,c.SearchLimits(max_depth=2,max_nodes=32768,max_time_seconds=10,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel_token=token)
            finally:m.install(False);pm.SearchStatistics=original_factory
            assert s.state is before[0] and s._search_history_witnesses==before[1]
            assert not m.calls and not p.stack and not p.pending and c.iteration==0 and c.qlevel==0
            stats=c.cm.clean(c.record_value(captured[0]));decision=c.cm.clean(c.record_value(d))
            classified=sum(v for (i,q,o,k),v in p.totals.items() if k=='children')
            assert attempts['successful']==stats['runtime_pushes']==stats['runtime_pops']
            if measured:assert classified==attempts['successful']
            for event in events:event['iteration_disposition']='outside_iteration' if event['iteration']==0 else ('completed' if event['iteration']<=d.completed_depth else 'aborted')
            signature={'decision':decision,'stats':stats,'attempts':dict(attempts),'budget_observations':token.observed,'trigger':trigger,'events':events}
            pair.append(signature);rows.append({'target':target,'order':order,'measured':measured,**signature,'reported_children':classified,'stages':[{'iteration':i,'qphase':q,'outcome':o,'metric':k,'value':v} for (i,q,o,k),v in sorted(p.totals.items())]})
        assert pair[0]==pair[1],(target,order)
report={'complete':True,'scope':'phase-targeted cancellation; identical phase observers on both arms; no time comparison','declared':{'targets':['root','main1','main2','q'],'orders':2,'depth':2,'q':4,'hard':8,'nodes':32768,'seconds_per_call':10,'fuse':180},'producer_sha256':hashlib.sha256((B/'physical_outcome.py').read_bytes()).hexdigest(),'rows':rows}
(Path(__file__).parent/'phase_cancellation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([{'target':r['target'],'order':r['order'],'measured':r['measured'],'trigger':r['trigger'],'depth':r['decision']['completed_depth'],'attempts':r['attempts'],'reported_children':r['reported_children']} for r in rows],indent=2))
