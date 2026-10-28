"""Frozen full-history equalservice localhash resource curve; no refill."""
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
def call(c,s,on,slot,out,plan,binary,seconds):
    begin=stamp();tick=time.perf_counter();cpu=time.process_time();before=s.to_record();model=None;decision=None
    try:
        p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_plain_leaper_local_hash=on),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True);native=p.native_legality_provider;assert native is not None;assert sha(native.native_rules.backend_module.__file__)==binary['sha256'];prior=provider_metrics(p)
        ctor=time.perf_counter()-tick;remaining=seconds-ctor
        assert remaining>0,'constructor exhausted callcap'
        with model.installed() if model is not None else nullcontext():decision=p.choose_action(s,SearchLimits(max_depth=64,max_nodes=500000,max_time_seconds=remaining,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel_token=CallerDeadline(tick+seconds))
        data=record_value(decision);wall=time.perf_counter()-tick;cpu_used=time.process_time()-cpu;end=stamp();row={'slot':slot,'on':on,'status':'RETURNED','started_at':begin,'ended_at':end,'wall_seconds':wall,'cpu_seconds':cpu_used,'constructor_seconds':ctor,'decision':data,'model_metrics':dict(model.metrics) if model else None,'model_stack_balanced':not model.undo if model else True,'Native_delta':metric_delta(prior,provider_metrics(p)),'record_before':record_value(before),'binary_sha256_checked':binary['sha256'],'process_memory':memory_snapshot()}
        write_record(out/f'return-{slot:03d}.json',row);record_interval(begin,end,'research',str(out/f'return-{slot:03d}.json'),out)
        assert s.to_record()==before and decision.runtime_depth_balanced and decision.action in s.legal_actions()
        pv=type(s).replay(c,before)
        for a in decision.principal_variation:pv.submit(a)
        assert decision.native_legality_fallbacks==decision.native_legality_operational_failures==0
        assert row['Native_delta']['availability'].get('declines',0)==0
        assert decision.runtime_position_identity_hash_cached is False
        return row
    except BaseException as exc:
        write_record(out/f'failure-{slot:03d}.json',{'slot':slot,'type':type(exc).__name__,'error':str(exc),'started_at':begin,'ended_at':stamp(),'original_return_preserved':(out/f'return-{slot:03d}.json').exists(),'partial_model_metrics':dict(model.metrics) if model else None})
        raise



def run(inputs,protocol,out):
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);plan=json.loads(Path(protocol).read_text());assert sha(inputs)==plan['input_sha256'];rows=json.loads(Path(inputs).read_text())['rows'];assert len(rows)==16;binary=native_identity();prepared=[(r,*make_session(r)) for r in rows];sources=['scripts/leaper_service_curve.py','generic_chess/core/search_runtime.py','generic_chess/ai/alphabeta/player.py','generic_chess/ai/alphabeta/search.py','generic_chess/ai/alphabeta/native_legality.py']
    write_record(out/'frozen.json',{'plan':plan,'binary':binary,'sources':{p:{'sha256':sha(p),'text':Path(p).read_bytes().decode('utf-8')} for p in sources},'compiled_IR_before_queries':{r['id']:c.ir.to_dict() for r,c,s in prepared},'inputs_sha256':sha(inputs),'ids':[r['id'] for r,c,s in prepared],'Player_queries_before_freeze':0})
    tick=time.perf_counter();groups=[];slot=0;reason=None
    try:
        for row,c,s in prepared:
            for seconds in plan['services']:
                calls=[]
                for on in (False,True,True,False):
                    flags=read_json(Path('.local_agent/rollout.json'))
                    if any(flags.get(k) for k in ('user_paused','stopped','research_stopped','stop_requested')):raise RuntimeError('scoped_stop')
                    if time.perf_counter()-tick+4>=plan['batch_seconds']:raise RuntimeError('batchreserve')
                    if (datetime.fromisoformat(plan['whole_deadline_utc'])-datetime.now(timezone.utc)).total_seconds()<plan['whole_delivery_reserve_seconds']+4:raise RuntimeError('whole_deliveryreserve')
                    value=call(c,s,on,slot,out,plan,binary,seconds);slot+=1;calls.append(value)
                actions=[json.dumps(x['decision']['action'],sort_keys=True) for x in calls];stable=actions[0]==actions[3] and actions[1]==actions[2];g={'id':row['id'],'family':row['family'],'seconds':seconds,'slots':[x['slot'] for x in calls],'stable_choice_difference':stable and actions[0]!=actions[1],'OFFdepths':[calls[i]['decision']['completed_depth'] for i in (0,3)],'ONdepths':[calls[i]['decision']['completed_depth'] for i in (1,2)],'sources':[x['decision']['result_source'] for x in calls],'timing_eligible':all(x['wall_seconds']<=seconds*1.1 for x in calls)};groups.append(g);write_record(out/'groups.json',groups);print(g,flush=True)
    except Exception as exc:reason=type(exc).__name__+':'+str(exc)
    summary={'status':'COMPLETE_RESOURCE_CURVE' if reason is None and slot==192 else 'INCOMPLETE_UNKNOWN','reason':reason,'returns':slot,'planned':192,'NOT_RUN':list(range(slot,192)),'groups':len(groups),'seconds':time.perf_counter()-tick,'by_budget':{str(t):{'groups':sum(g['seconds']==t for g in groups),'stable_choice_difference_families':sorted({g['family'] for g in groups if g['seconds']==t and g['stable_choice_difference'] and g['timing_eligible']}),'ONhigher_uniform_depth_groups':sum(min(g['ONdepths'])>max(g['OFFdepths']) for g in groups if g['seconds']==t)} for t in plan['services']},'games':0,'default':'OFF','claim':'equalfullservice retainedwork/actionbehavior only;neitherchangedactionnordepthprovesquality;nocrossruleheldout/strength'};write_record(out/'summary.json',summary);print(json.dumps(summary));return summary
