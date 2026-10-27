"""Frozen relative-history pilot; no refill or production activation."""
from __future__ import annotations
import argparse,gzip,json,hashlib,random,time,sys,platform
from pathlib import Path
from datetime import datetime,timezone,timedelta
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.schema import ruleset_from_dict,ruleset_to_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.native import _module,native_available
from scripts.leaper_design import definition,PAIRS
from scripts.leaper_pvs_quality_pilot import CallerDeadline,provider_metrics,metric_delta
from scripts.research_record import record_value,write_record
from tools.local_agent import session as ledger
from tools.local_agent.common import read_json


def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def memory_snapshot():
    """Process totals only, not per-arm attributable allocation."""
    if sys.platform != 'win32':return {'status':'UNAVAILABLE'}
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(n,ctypes.c_size_t) for n in ('peak_rss','rss','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
    kernel=ctypes.windll.kernel32;kernel.GetCurrentProcess.restype=wintypes.HANDLE
    api=ctypes.windll.psapi.GetProcessMemoryInfo
    api.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    value=Counters();value.cb=ctypes.sizeof(value)
    if not api(kernel.GetCurrentProcess(),ctypes.byref(value),value.cb):return {'status':'UNAVAILABLE'}
    return {'status':'MEASURED_PROCESS_TOTAL','rss_bytes':value.rss,'peak_rss_bytes':value.peak_rss}
def point(g):
    if g.get('status')!='TERMINAL':return None
    t=g['Core_terminal'];assert t['status']!='ongoing'
    return .5 if t['winner'] is None else int(t['winner']==g['on_seat'])


def native_identity():
    assert native_available(),'requested Native unavailable'
    module=_module();path=Path(module.__file__)
    return {'module_file':path.name,'sha256':sha(path),'bytes':path.stat().st_size,'python':platform.python_version(),'platform':platform.system(),'machine':platform.machine()}


def stop_reason(plan,batch_tick=None):
    flags=read_json(Path('.local_agent/rollout.json'))
    if any(flags.get(k) for k in ('user_paused','stopped','research_stopped','stop_requested')):return 'scoped_stop'
    deadline=datetime.fromisoformat(plan['started_at'])+timedelta(minutes=plan['single_run_cap_minutes'])
    if (deadline-datetime.now(timezone.utc)).total_seconds()<plan['delivery_reserve_seconds']+2:return 'whole_run_delivery_reserve'
    if batch_tick is not None and time.perf_counter()-batch_tick+2>=plan['game_batch_seconds']:return 'game_batch_inflight_reserve'
    return None


def make_player(c,on):
    return AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True,use_relative_history=on),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)


def choose(c,s,player,on,seconds,depth,qid,out,binary):
    began=stamp();tick=time.perf_counter();cpu=time.process_time();raw_end=None
    try:
        before=s.to_record()
        created = player is None
        if created:player=make_player(c,on)
        provider=player.native_legality_provider;assert provider is not None
        loaded=Path(provider.native_rules.backend_module.__file__)
        assert loaded.name==binary['module_file']
        if created:
            assert sha(loaded)==binary['sha256'],'loaded Native identity changed'
        # The binary was hashed before queries; unchanged on-disk identity at each new Player.
        metrics=provider_metrics(player)
        remaining=seconds-(time.perf_counter()-tick)
        assert remaining>0,'setup consumed whole query budget'
        d=player.choose_action(s,SearchLimits(max_depth=depth,max_nodes=500000,max_time_seconds=remaining,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel_token=CallerDeadline(tick+seconds))
        value=record_value(d)
        wall=time.perf_counter()-tick;cpu_used=time.process_time()-cpu;raw_end=stamp()
        row={'query_id':qid,'on':on,'started_at':began,'ended_at':raw_end,'status':'RETURNED','wall_seconds':wall,'cpu_seconds':cpu_used,'decision':value,'provider_delta':metric_delta(metrics,provider_metrics(player)),'record_before_sha256':hashlib.sha256(json.dumps(record_value(before),sort_keys=True).encode()).hexdigest(),'process_memory_after_query':memory_snapshot()}
        write_record(out/'returns'/(qid+'.json'),row)
        ledger.record_work(began,raw_end,'research',str(out/'returns'/(qid+'.json')))
        valid0=stamp()
        assert s.to_record()==before,'query mutated state/history'
        assert d.runtime_depth_balanced,'unbalanced search'
        assert d.action in s.legal_actions(),'illegal chosen action'
        pv=GameSession.replay(c,before)
        for a in d.principal_variation:pv.submit(a)
        assert d.native_legality_fallbacks==d.native_legality_operational_failures==0,'Native fallback'
        assert row['provider_delta']['availability'].get('declines',0)==0,'availability decline'
        assert wall<=seconds*1.1,'whole service exceeded tolerance'
        ledger.record_work(valid0,stamp(),'validation',qid+' full-history/action/PV/provider/time checks')
        return player,d,row
    except BaseException as exc:
        failure={'query_id':qid,'started_at':began,'failed_at':stamp(),'status':'FAILED','type':type(exc).__name__,'error':str(exc),'returned_original_exists':raw_end is not None}
        write_record(out/'failures'/(qid+'.json'),failure)
        if raw_end is None:ledger.record_work(began,stamp(),'research',str(out/'failures'/(qid+'.json')))
        raise


def prepare(plan,out):
    assert not out.exists(),'no refill/resume into old output'
    out.mkdir(parents=True);(out/'returns').mkdir();(out/'failures').mkdir()
    packet=Path('docs/research/data/leaper_forward_design_20261022/observations.json.gz')
    assert sha(packet)=='65cbda6e861249f04914511f5bcdd1e83233879c276236df7caac1f7d5c0b761'
    old=json.loads(gzip.decompress(packet.read_bytes()))['runs']['pilot']['inputs']['worlds']
    rng=random.Random(plan['prospective_sampling_seed'])
    rest=[i for i in range(10) if i not in (5,8)];rng.shuffle(rest);old_ids=[5,8]+rest[:4]
    options=[(a,b) for a in range(1,32) for b in range(a+1,32) if (a,b) not in PAIRS];rng.shuffle(options);new_pairs=options[:6]
    roots=[]
    # Interleave old/new before any outcomes, then each root's two colors.
    for i in range(6):
        w=old[old_ids[i]]
        roots.append({'root_id':f'dev{w["world"]}','cohort':'exposed_development','rule':w['rule'],'fingerprint':w['fingerprint'],'record':w['initial_record'],'masks':w['masks']})
        r=definition(*new_pairs[i]);roots.append({'root_id':f'prospective{i}','cohort':'unplayed_with_geometry_metadata_exposure','rule':ruleset_to_dict(r),'fingerprint':compute_fingerprint(r),'record':None,'masks':new_pairs[i]})
    write_record(out/'frozen-inputs-before-compile.json',{'plan':plan,'roots':roots,'old_ids':old_ids,'new_pairs':new_pairs,'sampling':'fixed seed;no outcome-conditioned eligibility refill','packet_sha256':sha(packet)})
    started=stamp();tick=time.perf_counter();compiled={};initial={}
    for root in roots:
        r=ruleset_from_dict(root['rule']);assert compute_fingerprint(r)==root['fingerprint']
        c=compile_legacy_ruleset_for_semantic_execution(r)
        s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record']))) if root['record'] is not None else GameSession(c)
        assert not s.state.terminal_status.is_terminal
        assert r.max_ply==128 and r.repetition_limit==4
        compiled[root['root_id']]=c;initial[root['root_id']]=s.to_record()
        root['record']=record_value(s.to_record())
    binary=native_identity()
    paths=[*Path('generic_chess/ai/alphabeta').glob('*.py'),Path('generic_chess/ai/decision.py'),Path('generic_chess/core/search_runtime.py'),Path('generic_chess/core/semantic_executor.py'),Path('generic_chess/rules/ir.py'),Path('generic_chess/rules/compiler.py'),Path(__file__)]
    write_record(out/'frozen-execution.json',{'roots':roots,'binary':binary,'python':sys.version,'source_hashes':{str(p).replace('\\','/'):sha(p) for p in paths},'sources':{str(p).replace('\\','/'):p.read_text(encoding='utf-8') for p in paths},'setup_seconds':time.perf_counter()-tick})
    ledger.record_work(started,stamp(),'validation',str(out/'frozen-execution.json')+' input admission/native identity/source freeze')
    return roots,compiled,initial,binary


def run(plan_path,output):
    plan=read_json(Path(plan_path));out=Path(output)
    roots,compiled,initial,binary=prepare(plan,out)
    qualification=[];halt=None
    for i,root in enumerate(roots):
        for on in ([False,True] if i%2==0 else [True,False]):
            slot={'slot':len(qualification),'root_id':root['root_id'],'on':on,'status':'NOT_RUN'}
            halt=halt or stop_reason(plan)
            if not halt:
                try:
                    s=GameSession.replay(compiled[root['root_id']],initial[root['root_id']])
                    p,d,row=choose(compiled[root['root_id']],s,None,on,2,2,f'q{slot["slot"]:02d}',out,binary)
                    slot.update(status='RETURNED',decision=row['decision'])
                    assert d.completed_depth==2,'semantic qualifier incomplete'
                except Exception as exc:slot.update(status='FAILED',error=type(exc).__name__+':'+str(exc));halt='qualification_failure'
            else:slot['reason']=halt
            qualification.append(slot);write_record(out/'qualification.json',qualification)
        pair=qualification[-2:]
        if not halt and pair[0]['decision']['score']!=pair[1]['decision']['score']:halt='fixed_depth_value_mismatch'
    games=[{'slot':2*i+j,'root_id':root['root_id'],'cohort':root['cohort'],'on_seat':seat,'status':'NOT_STARTED','queries':[]} for i,root in enumerate(roots) for j,seat in enumerate(([0,1] if i%2==0 else [1,0]))]
    write_record(out/'games.json',games);batch=time.perf_counter()
    for game in games:
        halt=halt or stop_reason(plan,batch)
        if halt:game['reason']=halt;write_record(out/'games.json',games);continue
        c=compiled[game['root_id']];s=GameSession.replay(c,initial[game['root_id']]);players={0:None,1:None};game['initial_record']=record_value(s.to_record());game['started_at']=stamp();game['status']='ONGOING';game['timing_qualified']=True
        try:
            while not s.state.terminal_status.is_terminal:
                halt=halt or stop_reason(plan,batch)
                if halt:game['reason']=halt;break
                actor=s.state.position.side_to_move;on=actor==game['on_seat'];qid=f'g{game["slot"]:02d}-p{s.state.ply_count:03d}'
                players[actor],d,row=choose(c,s,players[actor],on,1,64,qid,out,binary)
                game['queries'].append(qid);game['last_decision']=row['decision']
                start=stamp();s.submit(d.action);ledger.record_work(start,stamp(),'research',qid+' actual Core game transition')
                game['final_record']=record_value(s.to_record());game['Core_terminal']=record_value(s.state.terminal_status)
                if s.state.terminal_status.is_terminal:game['status']='TERMINAL';game['ended_at']=stamp()
                write_record(out/'games.json',games)
        except Exception as exc:
            game.update(status='FAILED',error=type(exc).__name__+':'+str(exc));halt='game_contract_failure'
        write_record(out/'games.json',games)
        print(json.dumps({'slot':game['slot'],'root':game['root_id'],'status':game['status'],'plies':s.state.ply_count,'halt':halt,'batch_seconds':time.perf_counter()-batch}),flush=True)
    result={'halt':halt,'games':len(games),'terminal':sum(g['status']=='TERMINAL' for g in games),'points':[point(g) for g in games],'not_started':sum(g['status']=='NOT_STARTED' for g in games),'batch_seconds':time.perf_counter()-batch,'ended_at':stamp(),'new_refill':False}
    write_record(out/'summary.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.plan,a.output)
