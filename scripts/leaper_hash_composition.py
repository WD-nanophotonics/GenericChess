"""Frozen new four-arm exact-hash composition, never old-slot refill; no refill."""
from contextlib import nullcontext
from datetime import datetime,timezone
import hashlib,json,time
from pathlib import Path
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.leaper_pvs_quality_pilot import make_session,CallerDeadline,provider_metrics,metric_delta
from scripts.leaper_relative_history_pilot import native_identity,memory_snapshot,record_interval
from scripts.leaper_boolean_cost_pilot import signature
from scripts.research_record import write_record,record_value
from tools.local_agent.common import read_json

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def stamp():return datetime.now(timezone.utc).isoformat()
def call(c,s,arm,slot,out,plan,binary):
    local,cached=arm
    begin=stamp();tick=time.perf_counter();cpu=time.process_time();before=s.to_record();model=None;decision=None
    try:
        p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_plain_leaper_local_hash=local,use_cached_position_identity_hash=cached),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True);native=p.native_legality_provider;assert native is not None;assert sha(native.native_rules.backend_module.__file__)==binary['sha256'];prior=provider_metrics(p)
        ctor=time.perf_counter()-tick;remaining=plan['cost']['single_service_seconds']-ctor
        assert remaining>0,'constructor exhausted callcap'
        with model.installed() if model is not None else nullcontext():decision=p.choose_action(s,SearchLimits(max_depth=3,max_nodes=500000,max_time_seconds=remaining,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel_token=CallerDeadline(tick+plan['cost']['single_service_seconds']))
        data=record_value(decision);wall=time.perf_counter()-tick;cpu_used=time.process_time()-cpu;end=stamp();row={'slot':slot,'arm':list(arm),'status':'RETURNED','started_at':begin,'ended_at':end,'wall_seconds':wall,'cpu_seconds':cpu_used,'constructor_seconds':ctor,'decision':data,'model_metrics':dict(model.metrics) if model else None,'model_stack_balanced':not model.undo if model else True,'Native_delta':metric_delta(prior,provider_metrics(p)),'record_before':record_value(before),'binary_sha256_checked':binary['sha256'],'process_memory':memory_snapshot()}
        write_record(out/f'return-{slot:03d}.json',row);record_interval(begin,end,'research',str(out/f'return-{slot:03d}.json'),out)
        assert s.to_record()==before and decision.runtime_depth_balanced and decision.action in s.legal_actions()
        pv=type(s).replay(c,before)
        for a in decision.principal_variation:pv.submit(a)
        assert decision.native_legality_fallbacks==decision.native_legality_operational_failures==0
        assert row['Native_delta']['availability'].get('declines',0)==0
        assert bool(data['runtime_semantic_local_hash_updates'])==local and data['runtime_position_identity_hash_cached']==cached
        assert (data['runtime_semantic_full_diff_fallbacks']==0)==local
        return row
    except BaseException as exc:
        write_record(out/f'failure-{slot:03d}.json',{'slot':slot,'type':type(exc).__name__,'error':str(exc),'started_at':begin,'ended_at':stamp(),'original_return_preserved':(out/f'return-{slot:03d}.json').exists(),'partial_model_metrics':dict(model.metrics) if model else None})
        raise


HASH_FIELDS={'runtime_semantic_local_hash_updates','runtime_position_identity_hash_cached','runtime_semantic_full_diff_fallbacks'}
def comparable(d):return {k:v for k,v in signature(d).items() if k not in HASH_FIELDS}

def run(inputs,protocol,out):
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);plan=json.loads(Path(protocol).read_text());assert sha(inputs)==plan['input_sha256'];rows=json.loads(Path(inputs).read_text())['rows'];assert len(rows)==16;binary=native_identity();prepared=[]
    for row in rows:
        c,s=make_session(row);prepared.append((row,c,s))
    sources=['scripts/leaper_hash_composition.py','generic_chess/core/search_runtime.py','generic_chess/ai/alphabeta/player.py','generic_chess/ai/alphabeta/search.py','generic_chess/ai/alphabeta/native_legality.py','scripts/leaper_boolean_cost_pilot.py','scripts/leaper_relative_history_pilot.py']
    write_record(out/'frozen.json',{'plan':plan,'binary':binary,'sources':{p:{'sha256':sha(p),'text':Path(p).read_bytes().decode('utf-8')} for p in sources},'compiled_IR_before_queries':{r['id']:c.ir.to_dict() for r,c,s in prepared},'inputs_sha256':sha(inputs),'ids':[r['id'] for r,c,s in prepared],'Player_queries_before_freeze':0})
    tick=time.perf_counter();groups=[];returns=[];reason=None;slot=0;order=((False,False),(True,False),(True,True),(False,True),(False,True),(True,True),(True,False),(False,False))
    try:
        for row,c,s in prepared:
            calls=[]
            for arm in order:
                flags=read_json(Path('.local_agent/rollout.json'))
                if any(flags.get(k) for k in ('user_paused','stopped','research_stopped','stop_requested')):raise RuntimeError('scoped_stop')
                remaining=(datetime.fromisoformat(plan['whole_deadline_utc'])-datetime.now(timezone.utc)).total_seconds()
                if remaining<plan['cost']['whole_delivery_reserve_seconds']+10:raise RuntimeError('whole_delivery_reserve')
                if time.perf_counter()-tick+10>=plan['cost']['batch_seconds']:raise RuntimeError('batch_inflight_reserve')
                if memory_snapshot().get('rss_bytes',0)>1536*1024*1024:raise RuntimeError('processRSS1.5GiBcap')
                r=call(c,s,arm,slot,out,plan,binary);returns.append(r);calls.append(r);slot+=1
            complete=all(r['decision']['completed_depth']==3 and r['decision']['result_source']=='main_iteration' for r in calls)
            parity=all(comparable(r['decision'])==comparable(calls[0]['decision']) for r in calls) if complete else None
            g={'id':row['id'],'family':row['family'],'complete':complete,'parity':parity,'slots':[r['slot'] for r in calls]}
            if complete:
                g['arms']={str(int(a))+str(int(b)):{metric:sum(x[metric+'_seconds'] for x in calls if x['arm']==[a,b]) for metric in ('wall','cpu')} for a,b in ((False,False),(True,False),(True,True),(False,True))}
            groups.append(g);write_record(out/'groups.json',groups);print(g,flush=True)
            if complete and not parity:raise RuntimeError('fullwork_parity_mismatch')
    except Exception as exc:reason=type(exc).__name__+':'+str(exc)
    eligible=[g for g in groups if g['complete'] and g['parity']];families=sorted({g['family'] for g in eligible});totals={arm:{m:sum(g['arms'][arm][m] for g in eligible) for m in ('wall','cpu')} for arm in ('00','10','11','01')};ratios={arm:{m:totals[arm][m]/totals['00'][m] if totals['00'][m] else None for m in ('wall','cpu')} for arm in ('10','11','01')};interaction={m:totals['11'][m]-totals['10'][m]-totals['01'][m]+totals['00'][m] for m in ('wall','cpu')};zero=sum(g['arms']['00']['cpu']==0 for g in eligible)
    gate=reason is None and len(returns)==128 and len(eligible)>=12 and len(families)==8 and zero==0 and ratios['11']['wall']<=.95 and ratios['11']['cpu']<=.95
    summary={'status':'PASS_SCOPED_COMBINATION_COST' if gate else 'NO_GO_OR_INCONCLUSIVE','reason':reason,'returns':len(returns),'planned':128,'NOT_RUN':list(range(slot,128)),'complete_parity_groups':len(eligible),'families':families,'totals':totals,'ratios_complete_groups':ratios,'interaction_seconds':interaction,'zero_offCPU_groups':zero,'seconds':time.perf_counter()-tick,'games':0,'Native_builds':0,'default':'OFF','claim':'finite development16roots;combinedcost/interaction only,not3independentwins/holdout/classstrength;old37factorialslotsremainNOT_RUN'}
    write_record(out/'summary.json',summary);print(json.dumps(summary));return summary
