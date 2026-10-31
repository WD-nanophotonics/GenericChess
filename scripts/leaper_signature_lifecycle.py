"""Frozen persistent-controller transfer of an exact signature memo; not games."""
import json,time,hashlib
from pathlib import Path
from contextlib import nullcontext
from datetime import datetime,timezone
from scripts.leaper_signature_memo import installed,reset,COUNTERS
from scripts.leaper_pvs_quality_pilot import make_session,CallerDeadline,provider_metrics,metric_delta
from scripts.leaper_relative_history_pilot import record_interval,native_identity,memory_snapshot
from scripts.leaper_boolean_cost_pilot import signature
from scripts.research_record import record_value,write_record
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_from_dict
from tools.local_agent.common import read_json

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(inputs,protocol,cold_summary,out):
    assert read_json(Path(cold_summary))['status']=='PASS_SCOPED_EXACT_COST','coldgateFAIL;0lifecyclecalls'
    out=Path(out);assert not out.exists();out.mkdir(parents=True);plan=read_json(Path(protocol));rows=read_json(Path(inputs))['rows'];assert len(rows)==16
    # Exact full history paths and terminal/missing tails are fixed before any Player exists.
    b=stamp();paths=[];preparation_transitions=0
    for row in rows:
        c,s=make_session(row);records=[]
        for step in range(4):
            if s.state.terminal_status.is_terminal:break
            records.append(record_value(s.to_record()))
            if step<3:
                actions=s.legal_actions();assert actions
                s.submit(actions[(3*step)%len(actions)]);preparation_transitions+=1
        paths.append({'root_id':row['id'],'family':row['family'],'records':records,'tail_missing':list(range(len(records),4))})
    binary=native_identity();sources=['scripts/leaper_signature_memo.py','scripts/leaper_signature_lifecycle.py','generic_chess/core/search_runtime.py','generic_chess/ai/alphabeta/player.py','generic_chess/ai/alphabeta/search.py']
    write_record(out/'frozen.json',{'plan':plan,'inputs':read_json(Path(inputs)),'inputs_sha256':sha(inputs),'paths':paths,'binary':binary,'preparation_direct_submits':preparation_transitions,'sources':{p:{'sha256':sha(p),'text':Path(p).read_bytes().decode('utf-8')} for p in sources},'new_Player_calls_before_freeze':0})
    record_interval(b,stamp(),'validation',str(out/'frozen.json')+' literal fullpaths beforeanyPlayer',out)
    tick=time.perf_counter();slot=0;groups=[];missing={f'{i}:{step}:{int(on)}' for i in range(16) for step in range(4) for on in (False,True)};constructors=[];reason=None;shared_core_seconds=0
    def bound():
        flags=read_json(Path('.local_agent/rollout.json'))
        if any(flags.get(k) for k in ('user_paused','stopped','research_stopped','stop_requested')):raise RuntimeError('userstop')
        if time.perf_counter()-tick+32>1500:raise RuntimeError('1500s batch inflightreserve')
        deadline=min(plan['whole_deadline_utc'],plan['parent_candidate_deadline'])
        if (datetime.fromisoformat(deadline)-datetime.now(timezone.utc)).total_seconds()<632:raise RuntimeError('whole deliveryreserve')
        if memory_snapshot().get('rss_bytes',0)>1536*1024**2:raise RuntimeError('RSS1.5GiBcap')
    try:
        for ri,(row,path) in enumerate(zip(rows,paths)):
            bound();c,s=make_session(row);players={}
            for on in (False,True):
                start=time.perf_counter();cpu=time.process_time();players[on]=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_plain_leaper_local_hash=True),use_native_semantic_legality=True,use_native_semantic_check=True,use_native_semantic_availability=True)
                constructors.append({'root':ri,'candidate':on,'wall_seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu})
            write_record(out/'constructors.json',constructors);history_clean=True
            for step,record in enumerate(path['records']):
                assert record_value(s.to_record())==record;pair={};prior_clean=history_clean
                for on in ((False,True) if step%2==0 else (True,False)):
                    bound();p=players[on];assert p.native_legality_provider is not None and sha(p.native_legality_provider.native_rules.backend_module.__file__)==binary['sha256']
                    reset();begin=stamp();t=time.perf_counter();cpu=time.process_time();prior=provider_metrics(p)
                    with installed() if on else nullcontext():d=p.choose_action(s,SearchLimits(max_depth=4,max_nodes=2000000,max_time_seconds=30,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel_token=CallerDeadline(t+30))
                    wall=time.perf_counter()-t;used=time.process_time()-cpu;end=stamp();r={'slot':slot,'root_index':ri,'root_id':row['id'],'family':row['family'],'prefix':step,'candidate':on,'history_clean_before_pair':prior_clean,'started_at':begin,'ended_at':end,'wall_seconds':wall,'cpu_seconds':used,'decision':record_value(d),'memo':dict(COUNTERS),'record_before':record,'binary_sha256':binary['sha256'],'Native_delta':metric_delta(prior,provider_metrics(p)),'memory':memory_snapshot()}
                    write_record(out/f'return-{slot:03d}.json',r);record_interval(begin,end,'research',str(out/f'return-{slot:03d}.json'),out);slot+=1;pair[on]=r;missing.remove(f'{ri}:{step}:{int(on)}')
                    v=stamp();assert record_value(s.to_record())==record and d.runtime_depth_balanced and d.action in s.legal_actions() and wall<=33
                    pv=type(s).replay(c,s.to_record())
                    for a in d.principal_variation:pv.submit(a)
                    assert d.native_legality_fallbacks==d.native_legality_operational_failures==0
                    if on:assert COUNTERS['runtimes']==1 and COUNTERS['fallbacks']==0 and COUNTERS['peak_entries']<=4096
                    else:assert not any(COUNTERS.values())
                    record_interval(v,stamp(),'validation',f'lifecycle{slot-1} fullhistory/action/PV/provider/Runtime reset',out)
                complete=all(r['decision']['completed_depth']==4 and r['decision']['result_source']=='main_iteration' for r in pair.values());parity=signature(pair[False]['decision'])==signature(pair[True]['decision']) if complete else None
                if prior_clean and complete and not parity:raise RuntimeError('clean persistent-TT fullwork mismatch')
                eligible=prior_clean and complete and parity;history_clean=bool(eligible)
                g={'root':ri,'root_id':row['id'],'family':row['family'],'prefix':step,'complete':complete,'parity':parity,'prior_clean':prior_clean,'eligible':bool(eligible),'slots':{str(k):v['slot'] for k,v in pair.items()}}
                for m in ('wall','cpu'):
                    g['OFF_'+m]=pair[False][m+'_seconds'];g['ON_'+m]=pair[True][m+'_seconds']
                groups.append(g);write_record(out/'groups.json',groups);print(json.dumps({k:g[k] for k in ('root_id','prefix','eligible','complete','parity')}),flush=True)
                if step+1<len(path['records']):
                    t=time.perf_counter();a=action_from_dict(path['records'][step+1]['actions'][-1]);s.submit(a);shared_core_seconds+=time.perf_counter()-t
    except Exception as exc:reason=type(exc).__name__+':'+str(exc);write_record(out/'failure.json',{'reason':reason,'at':stamp(),'returns_preserved':slot,'missing':sorted(missing)})
    eligible=[g for g in groups if g['prefix']>0 and g['eligible']];totals={side+'_'+m:sum(g[side+'_'+m] for g in eligible) for side in ('OFF','ON') for m in ('wall','cpu')};ratios={m:totals['ON_'+m]/totals['OFF_'+m] if totals['OFF_'+m] else None for m in ('wall','cpu')};families=sorted({g['family'] for g in eligible});passed=slot==128 and reason is None and len(eligible)>=36 and len(families)==8 and all(g['OFF_cpu']>0 for g in eligible) and all(v is not None and v<=.95 for v in ratios.values())
    summary={'status':'PASS_SCOPED_WARM_TRANSFER' if passed else 'NO_GO_OR_INCONCLUSIVE','reason':reason,'returns':slot,'planned':128,'NOT_RUN':sorted(missing),'eligible_warm_pairs':len(eligible),'families':families,'warm_totals':totals,'warm_ratios':ratios,'constructors':constructors,'common_Core_advance_seconds_measured_once':shared_core_seconds,'batch_seconds':time.perf_counter()-tick,'games':0,'default':'OFF','scope':'fixedcommoninputpaths,persistentPlayers/TT,querylocalmemo;not game/strength/holdout. CommonCorecost not silently assigned to either arm.'};write_record(out/'summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='constructors'}),flush=True);return summary
if __name__=='__main__':
    import sys;run(*sys.argv[1:])
