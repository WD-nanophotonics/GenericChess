"""Frozen pure action-signature memo fixed-work cost test, no games/refill."""
from contextlib import nullcontext
from datetime import datetime,timezone
from pathlib import Path
import json,time,hashlib
from scripts.leaper_signature_memo import installed,COUNTERS,reset
from scripts.leaper_pvs_quality_pilot import make_session,CallerDeadline,provider_metrics,metric_delta
from scripts.leaper_relative_history_pilot import native_identity,memory_snapshot,record_interval
from scripts.leaper_boolean_cost_pilot import signature
from scripts.research_record import record_value,write_record
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import read_json

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stamp():return datetime.now(timezone.utc).isoformat()
def call(c,s,on,slot,out,plan,binary):
    begin=stamp();tick=time.perf_counter();cpu=time.process_time();before=s.to_record();reset()
    try:
        with installed() if on else nullcontext():
            p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_plain_leaper_local_hash=True),use_native_semantic_legality=True,use_native_semantic_check=True,use_native_semantic_availability=True)
            native=p.native_legality_provider;assert native is not None and sha(native.native_rules.backend_module.__file__)==binary['sha256'];prior=provider_metrics(p);ctor=time.perf_counter()-tick
            d=p.choose_action(s,SearchLimits(max_depth=4,max_nodes=2000000,max_time_seconds=30-ctor,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel_token=CallerDeadline(tick+30))
        wall=time.perf_counter()-tick;used=time.process_time()-cpu;end=stamp();row={'slot':slot,'candidate':on,'started_at':begin,'ended_at':end,'wall_seconds':wall,'cpu_seconds':used,'constructor_seconds':ctor,'decision':record_value(d),'memo':dict(COUNTERS),'Native_delta':metric_delta(prior,provider_metrics(p)),'record_before':record_value(before),'binary_sha256':binary['sha256'],'memory':memory_snapshot()}
        write_record(out/f'return-{slot:03d}.json',row);record_interval(begin,end,'research',str(out/f'return-{slot:03d}.json'),out)
        v=stamp();assert before==s.to_record() and d.runtime_depth_balanced and d.action in s.legal_actions();pv=type(s).replay(c,before)
        for a in d.principal_variation:pv.submit(a)
        assert d.native_legality_fallbacks==d.native_legality_operational_failures==0 and wall<=33
        if on:assert COUNTERS['runtimes']==1 and COUNTERS['fallbacks']==0 and COUNTERS['hits']>0
        else:assert all(v==0 for v in COUNTERS.values())
        record_interval(v,stamp(),'validation',f'slot{slot} fullroot/history/PV/Native/cache activation',out);return row
    except BaseException as e:
        write_record(out/f'failure-{slot:03d}.json',{'slot':slot,'type':type(e).__name__,'error':str(e),'original_return_preserved':(out/f'return-{slot:03d}.json').exists(),'memo':dict(COUNTERS),'at':stamp()});raise

def run(inputs,protocol,out):
    out=Path(out);assert not out.exists();out.mkdir(parents=True);plan=read_json(Path(protocol));assert sha(inputs)==plan['inputs_sha256'];rows=read_json(Path(inputs))['rows'];assert len(rows)==16
    binary=native_identity();prepared=[(r,*make_session(r)) for r in rows]
    paths=['scripts/leaper_signature_memo.py','scripts/leaper_signature_cost.py','generic_chess/core/search_runtime.py','generic_chess/core/actions.py','generic_chess/ai/alphabeta/search.py','generic_chess/ai/alphabeta/player.py']
    write_record(out/'frozen.json',{'plan':plan,'binary':binary,'inputs':read_json(Path(inputs)),'sources':{p:{'sha256':sha(p),'text':Path(p).read_bytes().decode('utf-8')} for p in paths},'new_research_Player_calls':0})
    slot=0;groups=[];tick=time.perf_counter();reason=None
    try:
        for row,c,s in prepared:
            calls=[]
            for on in (False,True,True,False):
                flags=read_json(Path('.local_agent/rollout.json'))
                if any(flags.get(k) for k in ('stopped','user_paused','stop_requested','research_stopped')):raise RuntimeError('scoped_stop')
                if time.perf_counter()-tick+32>1200:raise RuntimeError('batch including inflightreserve')
                if (datetime.fromisoformat(plan['whole_deadline_utc'])-datetime.now(timezone.utc)).total_seconds()<932:raise RuntimeError('whole deliveryreserve')
                if memory_snapshot().get('rss_bytes',0)>1536*1024**2:raise RuntimeError('RSS1.5GiBcap')
                calls.append(call(c,s,on,slot,out,plan,binary));slot+=1
            complete=all(r['decision']['completed_depth']==4 and r['decision']['result_source']=='main_iteration' for r in calls)
            parity=all(signature(r['decision'])==signature(calls[0]['decision']) for r in calls) if complete else None
            if complete and not parity:raise RuntimeError('fullwork mismatch')
            g={'id':row['id'],'family':row['family'],'slots':[r['slot'] for r in calls],'complete':complete,'parity':parity}
            if complete:
                for m in ('wall','cpu'):
                    g['OFF_'+m]=sum(calls[i][m+'_seconds'] for i in (0,3));g['ON_'+m]=sum(calls[i][m+'_seconds'] for i in (1,2))
            groups.append(g);write_record(out/'groups.json',groups);print(json.dumps(g),flush=True)
    except Exception as exc:reason=type(exc).__name__+':'+str(exc)
    eligible=[g for g in groups if g['complete'] and g['parity']];families=sorted({g['family'] for g in eligible});totals={s+'_'+m:sum(g[s+'_'+m] for g in eligible) for s in ('OFF','ON') for m in ('wall','cpu')};ratios={m:totals['ON_'+m]/totals['OFF_'+m] if totals['OFF_'+m] else None for m in ('wall','cpu')}
    gate=slot==64 and reason is None and len(eligible)>=12 and len(families)==8 and all(g['OFF_cpu']>0 for g in eligible) and all(ratios[m]<=.95 for m in ('wall','cpu'))
    summary={'status':'PASS_SCOPED_EXACT_COST' if gate else 'NO_GO_OR_INCONCLUSIVE','reason':reason,'returns':slot,'planned':64,'NOT_RUN':list(range(slot,64)),'complete_groups':len(eligible),'families':families,'totals':totals,'ratios':ratios,'seconds':time.perf_counter()-tick,'games':0,'default':'OFF','claim':'Exposed16completehistorydevelopmentcontexts,exactruntimecostonly;notstrength/holdout/classsuccess'};write_record(out/'summary.json',summary);print(json.dumps(summary),flush=True);return summary
if __name__=='__main__':
    import sys;run(sys.argv[1],sys.argv[2],sys.argv[3])
