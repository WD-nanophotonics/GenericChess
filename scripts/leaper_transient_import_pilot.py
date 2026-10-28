"""One default-OFF state-only Native import cost assessment; no games."""
from __future__ import annotations
import argparse,gzip,json,hashlib,time,importlib.util,sys
from pathlib import Path
from datetime import datetime,timezone,timedelta
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime
from scripts.leaper_pvs_quality_pilot import make_session,provider_metrics,metric_delta,CallerDeadline
from scripts.leaper_relative_history_pilot import record_interval,native_identity,memory_snapshot
from scripts.research_record import record_value,write_record
from tools.local_agent.common import read_json


def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
TIMES={'elapsed_seconds','time_to_first_legal_action','time_to_first_completed_iteration','ordering_seconds','legal_generation_seconds','evaluation_seconds','evaluation_profile_cache_hit','quiet_geometry_build_seconds'}
def signature(d):return {k:v for k,v in d.items() if k not in TIMES}


def stop(plan,tick):
    flags=read_json(Path('.local_agent/rollout.json'))
    if any(flags.get(k) for k in ('user_paused','stopped','research_stopped','stop_requested')):return 'scoped_stop'
    if time.perf_counter()-tick+plan['call_seconds']+1>=plan['batch_seconds']:return 'batch_reserve'
    deadline=datetime.fromisoformat(plan['single_run_origin'])+timedelta(minutes=plan['cap_minutes'])
    if (deadline-datetime.now(timezone.utc)).total_seconds()<=plan['whole_delivery_reserve_seconds']+plan['call_seconds']+1:return 'whole_delivery_reserve'
    return None


def validate_inputs(rows,output):
    inputs={}
    for row in rows:
        c,session=make_session(row)
        p=AlphaBetaPlayer(c,use_disk_cache=False,use_native_transient_imports=True)
        assert p.native_legality_provider is not None and p.native_legality_provider.transient_imports
        inputs[row['id']]=(c,session)
    write_record(output/'preflight.json',{'roots':len(inputs),'status':'PASS','proof':'Separate34contract tests passed beforefrozenqueries;thisonlybindsinputs/candidateadmission.'})
    return inputs


def call(c,session,on,depth,slot,out,plan,binary):
    began=stamp();tick=time.perf_counter();cpu=time.process_time();raw_saved=False
    try:
        before=session.to_record()
        p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True,use_native_transient_imports=on)
        assert p.native_legality_provider is not None and p.native_legality_provider.transient_imports==on
        loaded=Path(p.native_legality_provider.native_rules.backend_module.__file__);assert sha(loaded)==binary['sha256']
        ctor=time.perf_counter()-tick;metrics=provider_metrics(p)
        remaining=plan['call_seconds']-ctor;assert remaining>0
        d=p.choose_action(session,SearchLimits(max_depth=depth,max_nodes=plan['total_nodes'],max_time_seconds=remaining,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel_token=CallerDeadline(tick+plan['call_seconds']))
        data=record_value(d);ended=stamp();wall=time.perf_counter()-tick;cpu_used=time.process_time()-cpu
        row={'slot':slot['slot'],'case_id':slot['case_id'],'depth':depth,'on':on,'started_at':began,'ended_at':ended,'status':'RETURNED','decision':data,'outer_seconds':wall,'cpu_seconds':cpu_used,'constructor_seconds':ctor,'Native_delta':metric_delta(metrics,provider_metrics(p)),'transient_imports_active':p.native_legality_provider.transient_imports,'process_memory':memory_snapshot()}
        write_record(out/f"return-{slot['slot']:03d}.json",row);raw_saved=True
        record_interval(began,ended,'research',str(out/f"return-{slot['slot']:03d}.json"),out)
        v=stamp();assert session.to_record()==before and d.runtime_depth_balanced
        assert d.action in session.legal_actions()
        from generic_chess.session.session import GameSession
        pv=GameSession.replay(c,before)
        for action in d.principal_variation:pv.submit(action)
        assert d.native_legality_fallbacks==d.native_legality_operational_failures==0
        assert row['Native_delta']['availability'].get('declines',0)==0
        slot.update(status='RETURNED',complete=d.completed_depth==depth,decision=data,outer_seconds=wall,cpu_seconds=cpu_used)
        record_interval(v,stamp(),'validation',f'slot{slot["slot"]} fullhistory/undo/PV/provider checks',out)
        return row
    except BaseException as exc:
        failure={'slot':slot['slot'],'status':'FAILED','error_type':type(exc).__name__,'error':str(exc),'raw_return_preserved':raw_saved,'at':stamp()}
        write_record(out/f"failure-{slot['slot']:03d}.json",failure)
        slot.update(status='FAILED',error=failure['error']);raise


def analyze(slots):
    groups=[]
    for depth in (6,8):
        rows=[r for r in slots if r['depth']==depth]
        for start in range(0,len(rows),4):
            g=rows[start:start+4];ok=all(x['status']=='RETURNED' and x.get('complete') for x in g)
            parity=ok and len({json.dumps(signature(x['decision']),sort_keys=True) for x in g})==1
            on=[x for x in g if x['on']];off=[x for x in g if not x['on']]
            cpu=sum(x.get('cpu_seconds',0) for x in off)
            groups.append({'depth':depth,'case_id':g[0]['case_id'],'eligible':parity,'wall_on':sum(x.get('outer_seconds',0) for x in on) if parity else None,'wall_off':sum(x.get('outer_seconds',0) for x in off) if parity else None,'cpu_on':sum(x.get('cpu_seconds',0) for x in on) if parity else None,'cpu_off':cpu if parity else None,'cpu_resolution_known':cpu>0 if parity else False})
    result={'groups':groups,'counts':{s:sum(x['status']==s for x in slots) for s in ('RETURNED','FAILED','NOT_RUN')},'new_games':0,'native_builds':1,'limits':'Exposed exact-cost controls;not strength/holdout. Censored groups excluded from ratios,retainedfixedslots.'}
    for depth in (6,8):
        eligible=[r for r in groups if r['depth']==depth and r['eligible']]
        result[str(depth)]={'eligible_root_groups':len(eligible),'wall_ratio':sum(r['wall_on'] for r in eligible)/sum(r['wall_off'] for r in eligible) if eligible else None,'cpu_ratio':sum(r['cpu_on'] for r in eligible)/sum(r['cpu_off'] for r in eligible) if eligible and all(r['cpu_resolution_known'] for r in eligible) else None}
    return result


def run(plan_path,output):
    out=Path(output);assert not out.exists(),'no refill';out.mkdir(parents=True)
    plan=read_json(Path(plan_path));path=Path(plan['benchmark_source']);assert sha(path)==plan['input_sha256'];
    for p,h in plan['sources'].items():assert sha(p)==h,p
    allrows=json.loads(gzip.decompress(path.read_bytes()))['rows'];rows=[r for r in allrows if r['prefix_length']==2];assert len(rows)==12
    slots=[{'slot':48*di+4*i+j,'case_id':r['id'],'depth':depth,'on':on,'status':'NOT_RUN'} for di,depth in enumerate((6,8)) for i,r in enumerate(rows) for j,on in enumerate(([False,True,True,False] if i%2==0 else [True,False,False,True]))]
    sourcefiles=[Path(__file__),Path('generic_chess/_native/native_module.c'),Path('generic_chess/ai/alphabeta/native_legality.py'),*Path('generic_chess/ai/alphabeta').glob('*.py'),Path('generic_chess/core/search_runtime.py'),Path('generic_chess/core/semantic_executor.py'),Path('generic_chess/rules/ir.py'),Path('generic_chess/rules/compiler.py')]
    load_private_native(plan['binary_path'])
    binary=native_identity();write_record(out/'frozen.json',{'plan':plan,'input_sha256':sha(path),'case_ids':[r['id'] for r in rows],'slots':slots,'binary':binary,'sources':{str(p).replace('\\','/'):p.read_bytes().decode('utf-8') for p in sourcefiles},'source_hashes':{str(p).replace('\\','/'):sha(p) for p in sourcefiles}})
    try:inputs=validate_inputs(allrows,out)
    except Exception as exc:
        write_record(out/'preflight-failure.json',{'type':type(exc).__name__,'error':str(exc),'at':stamp()});raise
    halt=None;tick=time.perf_counter()
    for depth in (6,8):
        for i,r in enumerate(rows):
            group=slots[(0 if depth==6 else 48)+4*i:(0 if depth==6 else 48)+4*i+4]
            for slot in group:
                halt=halt or stop(plan,tick)
                if halt:slot['reason']=halt
                else:
                    try:call(*inputs[r['id']],slot['on'],depth,slot,out,plan,binary)
                    except Exception:halt='contract_failure'
                write_record(out/'slots.json',slots)
            complete=all(x['status']=='RETURNED' and x.get('complete') for x in group)
            if complete and len({json.dumps(signature(x['decision']),sort_keys=True) for x in group})!=1:halt='complete_work_or_value_mismatch'
            print(json.dumps({'depth':depth,'case':r['id'],'complete4':complete,'halt':halt,'seconds':time.perf_counter()-tick}),flush=True)
        if depth==6:
            summary=analyze(slots);eligible=[g for g in summary['groups'] if g['depth']==6 and g['eligible']]
            import statistics
            ratios=[g['wall_on']/g['wall_off'] for g in eligible]
            qualified=len(eligible)>=10
            cost_go=qualified and summary['6']['wall_ratio']<=.95 and statistics.median(ratios)<=.95
            if not cost_go:halt=halt or 'D6_cost_or_coverage_NO_GO'

    result=analyze(slots);result.update(halt=halt,ended_at=stamp(),batch_seconds=time.perf_counter()-tick);write_record(out/'summary.json',result);print(json.dumps(result),flush=True)


def load_private_native(path):
 import generic_chess.native as native
 path=Path(path).resolve()
 if native._MODULE is not None:
  assert Path(native._MODULE.__file__).resolve()==path,'cannot mix loaded Native backends'
  return native._MODULE
 spec=importlib.util.spec_from_file_location('generic_chess._native_core',path)
 assert spec and spec.loader
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 assert hasattr(module,'semantic_pack_transient_position')
 sys.modules['generic_chess._native_core']=module;native._MODULE=module
 return module


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.plan,a.output)
