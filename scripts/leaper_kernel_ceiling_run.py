"""One frozen nested-attribution run, no optimization/default activation."""
from contextlib import nullcontext
from datetime import datetime,timezone
import hashlib,json,time,statistics
from pathlib import Path
from scripts.leaper_kernel_ceiling import NestedWall,targets,partition
from scripts.leaper_pvs_quality_pilot import make_session,CallerDeadline,provider_metrics,metric_delta
from scripts.leaper_relative_history_pilot import native_identity,memory_snapshot,record_interval
from scripts.leaper_boolean_cost_pilot import signature
from scripts.research_record import write_record,record_value
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import read_json

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def call(c,s,observed,slot,depth,seconds,out,binary):
    begin=stamp();tick=time.perf_counter();cpu=time.process_time();before=s.to_record();observer=NestedWall() if observed else None
    try:
        with observer.installed(targets()) if observer else nullcontext():
            p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_plain_leaper_local_hash=True),use_native_semantic_legality=True,use_native_semantic_check=True,use_native_semantic_availability=True)
            native=p.native_legality_provider;assert native is not None and sha(native.native_rules.backend_module.__file__)==binary['sha256']
            prior=provider_metrics(p);ctor=time.perf_counter()-tick
            d=p.choose_action(s,SearchLimits(max_depth=depth,max_nodes=2000000,max_time_seconds=seconds-ctor,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel_token=CallerDeadline(tick+seconds))
        wall=time.perf_counter()-tick;used=time.process_time()-cpu;ended=stamp()
        row={'slot':slot,'depth':depth,'observed':observed,'started_at':begin,'ended_at':ended,'wall_seconds':wall,'cpu_seconds':used,'constructor_seconds':ctor,'decision':record_value(d),'observer_rows':observer.rows if observer else None,'partition':partition(observer.rows,wall) if observer else None,'Native_delta':metric_delta(prior,provider_metrics(p)),'binary_sha256':binary['sha256'],'record_before':record_value(before),'memory':memory_snapshot()}
        write_record(out/f'return-{slot:03d}.json',row)
        record_interval(begin,ended,'research',str(out/f'return-{slot:03d}.json'),out)
        v=stamp();assert s.to_record()==before and d.runtime_depth_balanced
        assert d.action in s.legal_actions()
        pv=type(s).replay(c,before)
        for action in d.principal_variation:pv.submit(action)
        assert d.native_legality_fallbacks==d.native_legality_operational_failures==0
        assert d.runtime_semantic_full_diff_fallbacks==0 and d.runtime_semantic_local_hash_updates>0
        assert not d.runtime_position_identity_hash_cached and wall<=seconds*1.10
        if observer:
            assert not observer.stack and not observer.originals
            assert row['partition']['outside_and_unwrapped_seconds']>=0
            assert observer.rows['runtime_push']['calls']==d.runtime_pushes+observer.rows['runtime_push']['exceptions']
        record_interval(v,stamp(),'validation',f'slot{slot} complete state/PV/provider/clock/observer restoration',out)
        return row
    except BaseException as exc:
        write_record(out/f'failure-{slot:03d}.json',{'slot':slot,'at':stamp(),'type':type(exc).__name__,'error':str(exc),'original_return_preserved':(out/f'return-{slot:03d}.json').exists(),'partial_observer':observer.rows if observer else None})
        raise

def run(inputs,protocol,out):
    out=Path(out);assert not out.exists();out.mkdir(parents=True)
    plan=read_json(Path(protocol));assert sha(inputs)==plan['inputs_sha256']
    rows=read_json(Path(inputs))['rows'];assert len(rows)==16
    binary=native_identity();prepared=[(r,*make_session(r)) for r in rows]
    sources=['scripts/leaper_kernel_ceiling.py','scripts/leaper_kernel_ceiling_run.py','generic_chess/core/search_runtime.py','generic_chess/core/terminal.py','generic_chess/core/semantic_executor.py','generic_chess/ai/alphabeta/native_legality.py','generic_chess/ai/alphabeta/search.py','generic_chess/ai/alphabeta/player.py']
    write_record(out/'frozen.json',{'plan':plan,'inputs':read_json(Path(inputs)),'binary':binary,'sources':{p:{'sha256':sha(p),'text':Path(p).read_text(encoding='utf-8-sig')} for p in sources},'new_Player_calls_before_freeze':0})
    tick=time.perf_counter();groups=[];slot=0;reason=None
    try:
        for depth,seconds in [(3,12),(5,60)]:
            if depth==5:
                early=[g for g in groups if g['depth']==3 and g['eligible']]
                if len(early)<12 or len({g['family'] for g in early})<8 or statistics.median(g['observer_ratio'] for g in early)>1.25:
                    reason='D3 qualification/overhead failed; all48 D5 NOT_RUN';break
            for row,c,s in prepared:
                calls=[]
                for observed in (False,True,False):
                    flags=read_json(Path('.local_agent/rollout.json'))
                    if any(flags.get(k) for k in ('stopped','user_paused','research_stopped','stop_requested')):raise RuntimeError('scoped_stop')
                    if time.perf_counter()-tick+seconds+2>plan['batch_seconds']:raise RuntimeError('batch including in-flight reserve')
                    if (datetime.fromisoformat(plan['whole_deadline_utc'])-datetime.now(timezone.utc)).total_seconds()<plan['delivery_reserve_seconds']+seconds+2:raise RuntimeError('whole delivery reserve')
                    if memory_snapshot().get('rss_bytes',0)>1536*1024**2:raise RuntimeError('RSScap1.5GiB')
                    r=call(c,s,observed,slot,depth,seconds,out,binary);slot+=1;calls.append(r)
                complete=all(x['decision']['completed_depth']==depth and x['decision']['result_source']=='main_iteration' for x in calls)
                parity=all(signature(x['decision'])==signature(calls[0]['decision']) for x in calls) if complete else None
                if complete and not parity:raise RuntimeError('observer changed full work/results')
                g={'id':row['id'],'family':row['family'],'depth':depth,'slots':[x['slot'] for x in calls],'complete':complete,'parity':parity,'eligible':complete and parity,'observer_ratio':calls[1]['wall_seconds']/((calls[0]['wall_seconds']+calls[2]['wall_seconds'])/2),'bracket_drift':calls[2]['wall_seconds']/calls[0]['wall_seconds'],'observer_wall':calls[1]['wall_seconds'],'partition':calls[1]['partition']}
                groups.append(g);write_record(out/'groups.json',groups);print(json.dumps({k:g[k] for k in ('id','depth','eligible','observer_ratio')}),flush=True)
    except Exception as exc:reason=type(exc).__name__+':'+str(exc)
    summary={'status':'COMPLETE_OBSERVED_CEILING' if slot==96 and reason is None else 'LIMITED_OR_INCOMPLETE','reason':reason,'returns':slot,'planned':96,'NOT_RUN':list(range(slot,96)),'seconds':time.perf_counter()-tick,'by_depth':{},'games':0,'builds':0,'default':'OFF'}
    for depth in (3,5):
        eligible=[g for g in groups if g['depth']==depth and g['eligible']];total=sum(g['observer_wall'] for g in eligible)
        summary['by_depth'][str(depth)]={'eligible_groups':len(eligible),'families':sorted({g['family'] for g in eligible}),'median_observer_ratio':statistics.median(g['observer_ratio'] for g in eligible) if eligible else None,'broad_observed_fraction':sum(g['partition']['broad_observed_union_seconds'] for g in eligible)/total if total else None,'transport_binding_observed_fraction':sum(g['partition']['transport_binding_observed_union_seconds'] for g in eligible)/total if total else None,'not_uninstrumented_or_removable_fraction':True}
    write_record(out/'summary.json',summary);print(json.dumps(summary),flush=True);return summary
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--inputs');p.add_argument('--protocol');p.add_argument('--output');a=p.parse_args();run(a.inputs,a.protocol,a.output)
