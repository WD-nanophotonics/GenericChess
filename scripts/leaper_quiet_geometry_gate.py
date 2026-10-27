"""One frozen 40-call gate; no games, refill, retune or default activation."""
from __future__ import annotations
import argparse,gzip,json,time,hashlib,statistics
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timezone,timedelta
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_pvs_quality_pilot import CallerDeadline,provider_metrics,metric_delta
from scripts.research_record import record_value,write_record
from tools.local_agent import session as ledger
from tools.local_agent.common import read_json


def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(output):
    output=Path(output);assert not output.exists(),'no overwrite or refill'
    output.mkdir(parents=True)
    origin=stamp();tick=time.perf_counter()
    sources={str(p).replace('\\','/'):sha(p) for p in [Path(__file__),*Path('generic_chess/ai/alphabeta').glob('*.py'),Path('generic_chess/ai/decision.py'),Path('generic_chess/core/search_runtime.py'),Path('generic_chess/rules/ir.py'),Path('generic_chess/rules/compiler.py')]}
    packet=Path('docs/research/data/leaper_forward_design_20261022/observations.json.gz')
    assert sha(packet)=='65cbda6e861249f04914511f5bcdd1e83233879c276236df7caac1f7d5c0b761'
    worlds=json.loads(gzip.decompress(packet.read_bytes()))['runs']['pilot']['inputs']['worlds']
    expected=read_json(Path('docs/research/data/leaper_endpoint_qualification_20261027/qualification.json'))['rows']
    assert len(worlds)==len(expected)==10
    slots=[{'slot':4*i+j,'world':w['world'],'on':on,'status':'NOT_RUN'} for i,w in enumerate(worlds) for j,on in enumerate(([False,True,True,False] if i%2==0 else [True,False,False,True]))]
    write_record(output/'frozen.json',{'started_at':origin,'sources':sources,'packet_sha256':sha(packet),'slots':slots,'limits':{'depth':3,'total_nodes':500000,'whole_call_seconds':3,'q':4,'qhard':8},'query_batch_seconds':180,'single_run_cap_minutes':180,'admission':'No score/complete/provider/state/PV/cancellation mismatch;all40;>=3families reorder;wall and CPU aggregate+median ratios<=1.05','new_game':0})
    write_record(output/'executed-source.json',{f:Path(f).read_text(encoding='utf-8') for f in sources})
    halt=None;setup=[]
    for i,w in enumerate(worlds):
        if halt:break
        setup0=time.perf_counter();r=ruleset_from_dict(w['rule']);assert compute_fingerprint(r)==w['fingerprint']==expected[i]['fingerprint']
        c=compile_legacy_ruleset_for_semantic_execution(r)
        root=deserialize_game_record(json.dumps(w['initial_record']))
        s=GameSession.replay(c,root);assert not s.state.terminal_status.is_terminal
        setup.append({'world':w['world'],'seconds':time.perf_counter()-setup0,'record':record_value(root),'fingerprint':w['fingerprint']})
        for slot in slots[4*i:4*i+4]:
            flags=read_json(Path('.local_agent/rollout.json'))
            if any(flags.get(k) for k in ('user_paused','stopped','research_stopped','stop_requested')):halt='scoped_stop';break
            if time.perf_counter()-tick+4>=180:halt='query_batch_reserve';break
            began=stamp();wall=time.perf_counter();cpu=time.process_time()
            try:
                before=s.to_record()
                p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True,use_quiet_geometric_coverage=slot['on']),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
                metrics=provider_metrics(p);remaining=3-(time.perf_counter()-wall);assert remaining>0,'setup exhausted call'
                decision=p.choose_action(s,SearchLimits(max_depth=3,max_nodes=500000,max_time_seconds=remaining,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel_token=CallerDeadline(wall+3))
                raw=record_value(decision);outer=time.perf_counter()-wall;usedcpu=time.process_time()-cpu
                slot.update(status='RETURNED',started_at=began,ended_at=stamp(),decision=raw,wall_seconds=outer,cpu_seconds=usedcpu,provider_delta=metric_delta(metrics,provider_metrics(p)),profile_cache_hit=decision.evaluation_profile_cache_hit)
                # Original return is durable before any derived assertion.
                write_record(output/f"return-{slot['slot']:02d}.json",slot)
                assert s.to_record()==before,'mutated full history'
                assert decision.runtime_depth_balanced,'runtime imbalance'
                assert decision.action in s.legal_actions(),'illegal action'
                pv=GameSession.replay(c,before)
                for action in decision.principal_variation:pv.submit(action)
                assert decision.completed_depth==3,'incomplete D3'
                assert outer<=3.3,'whole-call overshoot'
                assert metrics['present'] and decision.native_legality_fallbacks==0 and decision.native_legality_operational_failures==0,'Native fallback'
                assert slot['provider_delta']['availability'].get('declines',0)==0,'availability decline'
                slot['qualification']='PASS'
            except Exception as exc:
                # Keep the original RETURNED separate from its validation failure.
                slot.setdefault('started_at',began);slot.setdefault('ended_at',stamp())
                slot['qualification']='FAILED';slot['error_type']=type(exc).__name__;slot['error']=str(exc)
                if slot['status']=='NOT_RUN':slot['status']='RAISED'
                halt='call_or_contract_failure'
            finally:
                ledger.record_work(began,stamp(),'research',str(output/f"return-{slot['slot']:02d}.json"))
                write_record(output/'slots.json',slots)
            if halt:break
        done=slots[4*i:4*i+4]
        if not halt and len({x['decision']['score'] for x in done})!=1:halt='same_completed_depth_value_mismatch'
    for slot in slots:
        if slot['status']=='NOT_RUN':slot['reason']=halt or 'not_dispatched'
    write_record(output/'slots.json',slots);write_record(output/'setup.json',setup)
    result=summarize(slots,halt)
    result.update(elapsed_seconds=time.perf_counter()-tick,ended_at=stamp())
    write_record(output/'summary.json',result);print(json.dumps(result))


def summarize(slots,halt=None):
    """Read saved returns only; unresolved CPU resolution never passes gate."""
    ratios=[];cpu_ratios=[];exposed=[]
    if not halt:
        for i in range(10):
            rows=slots[4*i:4*i+4]
            if len(rows)!=4 or any(x.get('qualification')!='PASS' for x in rows):
                halt='incomplete_or_failed_calls';break
            on=[x for x in rows if x['on']];off=[x for x in rows if not x['on']]
            if len(on)!=2 or len(off)!=2:halt='unbalanced_slots';break
            wall=sum(x['wall_seconds'] for x in off)
            cpu=sum(x['cpu_seconds'] for x in off)
            ratios.append(sum(x['wall_seconds'] for x in on)/wall if wall>0 else None)
            cpu_ratios.append(sum(x['cpu_seconds'] for x in on)/cpu if cpu>0 else None)
            if any(x['decision']['quiet_geometry_reorders']>0 for x in on):exposed.append(rows[0]['world'])
    on=[x for x in slots if x['on'] and x.get('qualification')=='PASS']
    off=[x for x in slots if not x['on'] and x.get('qualification')=='PASS']
    wall=sum(x['wall_seconds'] for x in off);cpu=sum(x['cpu_seconds'] for x in off)
    wallratio=sum(x['wall_seconds'] for x in on)/wall if wall>0 else None
    cpuratio=sum(x['cpu_seconds'] for x in on)/cpu if cpu>0 else None
    if not halt:
        if len(exposed)<3:halt='insufficient_feature_exposure'
        elif any(x is None for x in ratios+cpu_ratios) or wallratio is None or cpuratio is None:
            halt='unresolved_timing_resolution'
        elif max(wallratio,cpuratio,statistics.median(ratios),statistics.median(cpu_ratios))>1.05:
            halt='cost_gate_failed'
    return {'status':'GO_GAMES' if halt is None else 'STOP_NO_GAMES','reason':halt,
        'original_calls':sum(x['status']=='RETURNED' for x in slots),
        'qualified_calls':sum(x.get('qualification')=='PASS' for x in slots),
        'not_run':sum(x['status']=='NOT_RUN' for x in slots),
        'wall_ratio':wallratio,'cpu_ratio':cpuratio,'family_wall_ratios':ratios,
        'family_cpu_ratios':cpu_ratios,'reordered_families':exposed,'new_games':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output')
    parser.add_argument('--read-saved',help='derive only, never dispatch/repeat calls')
    args=parser.parse_args()
    if args.read_saved:
        output=Path(args.read_saved)
        rows=json.loads((output/'slots.json').read_text(encoding='utf-8'))
        result=summarize(rows);result.update(derived_from_saved_only=True,derived_at=stamp())
        assert not (output/'summary.json').exists(),'retain previous derived result'
        write_record(output/'summary.json',result);print(json.dumps(result))
    else:
        assert args.output;run(args.output)
