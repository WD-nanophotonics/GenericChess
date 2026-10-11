"""Bounded deterministic cancellation audit; no product or probe rewrite."""
import sys,time,json,importlib.util,collections,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
B=ROOT/'.local_agent/availability-core-20261011'
spec=importlib.util.spec_from_file_location('physical_probe',B/'physical_outcome.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
c=m.c;p=m.p;T=m.T
from generic_chess.ai.alphabeta import player as pm
from generic_chess.ai.alphabeta.statistics import SearchStatistics
stats_factory=pm.SearchStatistics
class DeterministicCancel:
    def __init__(self,limit):self.limit=limit;self.observed=0
    def is_cancelled(self):self.observed+=1;return self.observed>=self.limit
rows=[];started=time.monotonic()
compiled=c.compile_ruleset_for_execution(c.build_builtin_ruleset('western_chess'));board=c.CoreBoard(c.CASES[0],compiled);e=c.cm.w.weighted(compiled,c.VALUES['chess'])
for limit in (32,128,512,2048):
    for order in range(2):
        pair=[]
        for measured in ((False,True) if order==0 else (True,False)):
            c.stopped();assert time.monotonic()-started<180
            p.stack=[];p.pending={};p.totals=collections.Counter();p.peak=0;c.iteration=c.qlevel=0;c.counts=collections.Counter();m.calls=[];m.outside=collections.Counter()
            m.install(measured);wrapped=T._push_impl;attempts=collections.Counter();captured=[]
            def counted(self,*args,**kwargs):
                attempts['attempted']+=1
                try:result=wrapped(self,*args,**kwargs)
                except BaseException:attempts['failed']+=1;raise
                else:attempts['successful']+=1;return result
            T._push_impl=counted
            def factory():
                value=SearchStatistics();captured.append(value);return value
            pm.SearchStatistics=factory
            s=c.GameSession(compiled);s._state=board.initial;s._search_history_witnesses=board.witnesses
            before=(s.state,s._search_history_witnesses);token=DeterministicCancel(limit)
            try:d=c.AlphaBetaPlayer(compiled,evaluator_override=e,use_native_semantic_legality=True,use_disk_cache=False).choose_action(s,c.SearchLimits(max_depth=2,max_nodes=32768,max_time_seconds=10,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel_token=token)
            finally:m.install(False);pm.SearchStatistics=stats_factory
            assert s.state is before[0] and s._search_history_witnesses==before[1]
            assert not m.calls and not p.stack and not p.pending
            stats=c.record_value(captured[0]);decision=c.record_value(d)
            classified=sum(v for (i,q,o,k),v in p.totals.items() if k=='children')
            assert attempts['successful']==stats['runtime_pushes']==stats['runtime_pops']
            if measured:assert classified==attempts['successful']
            signature={'decision':c.cm.clean(decision),'stats':c.cm.clean(stats),'attempts':dict(attempts),'budget_observations':token.observed}
            pair.append(signature)
            rows.append({'limit':limit,'order':order,'measured':measured,**signature,'reported_children':classified,'stages':[{'iteration':i,'qphase':q,'outcome':o,'metric':k,'value':v} for (i,q,o,k),v in sorted(p.totals.items())]})
        assert pair[0]==pair[1],(limit,order)
report={'declared':{'limits':[32,128,512,2048],'orders':2,'pairs':'plain/instrumented','max_depth':2,'q':4,'hard':8,'nodes':32768,'seconds_per_call':10,'fuse':180},'complete':True,'scope':'deterministic budget-observation cancellation, no timing comparison; full internal stats independently captured','producer_sha256':hashlib.sha256((B/'physical_outcome.py').read_bytes()).hexdigest(),'rows':rows}
(Path(__file__).parent/'cancellation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([{'limit':r['limit'],'order':r['order'],'measured':r['measured'],'attempts':r['attempts'],'reported_children':r['reported_children'],'depth':r['decision']['completed_depth'],'reason':r['decision']['termination_reason']} for r in rows],indent=2))
