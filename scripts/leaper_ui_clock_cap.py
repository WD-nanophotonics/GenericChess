"""Three preselected clock-cap candidates against already acquired UI controls."""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace,asdict
import argparse,hashlib,time,traceback,json
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_real_budget_refinement import limits_for
from scripts.pure_leaper_search_study import append
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(d):
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    plan=L.load(d/'plan.json');data=L.load(d/'inputs.json');assert sha(__file__)==plan['source_sha256']and sha(d/'inputs.json')==plan['inputs_sha256']
    for f,h in plan['dependencies'].items():assert sha(f)==h
    assert L.load(Path(plan['prior_receipt']))['status']=='CLOSED','one producer; prior acquisition complete first'
    assert not(d/'receipt.json').exists()and not(d/'queries.jsonl').exists(),'no refill'
    baseline={r['slot']['key']:r for r in map(json.loads,Path(plan['controls']).read_text(encoding='utf-8').splitlines())if r['slot']['arm']=='default'and r['slot']['budget']=='balanced50k'};cases={c['key']:c for c in data['cases']};started=stamp();tick=time.perf_counter();attempted=0;count=0;status='FAILED'
    class Cancel:
        last=0.;flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>=.25:self.last=now;self.flag=stopped()or now-tick>=plan['batch_seconds']
            return self.flag
    try:
        for key in plan['keys']:
            if Cancel().is_cancelled():raise RuntimeError('role/batch stop; remainingUNKNOWN')
            case=cases[key];c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]));s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256']
            player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(),cap_pure_leaper_rule_clock=True);raw,limits=limits_for('balanced50k');assert asdict(limits)==plan['limits'];ts=stamp();qt=time.perf_counter();attempted+=1;dec=player.choose_action(s,limits,cancel_token=Cancel());te=stamp();row=dict(key=key,started_at=ts,ended_at=te,seconds=time.perf_counter()-qt,decision=L.record_value(dec),actual_requested_depth_cap=player.last_rule_clock_cap,remaining_clock=c.max_ply-s.state.ply_count,state_sha256=L.state_sha(s.state),tuning=L.record_value(SearchTuning()),evaluation_profile=L.record_value(player.evaluation_profile));append(d/'queries.jsonl',row);count+=1
            b=baseline[key];assert row['state_sha256']==b['state_sha256']and row['tuning']==b['tuning']and row['evaluation_profile']==b['evaluation_profile'];pv=replay(c,case['record'])
            for a in dec.principal_variation:pv.submit(a)
            labels={json.dumps(x['action'],sort_keys=True):x['truth']['value']for x in case['labelled_actions']};value=labels[json.dumps(L.record_value(dec.action),sort_keys=True)];old=labels[json.dumps(b['decision']['action'],sort_keys=True)]
            append(d/'qualification.jsonl',dict(key=key,chosen_global_WDL=value,control_global_WDL=old,correct=value==case['root_global_WDL'],control_correct=old==case['root_global_WDL'],same_action=L.record_value(dec.action)==b['decision']['action'],same_score=dec.score==b['decision']['score'],pv_steps=len(dec.principal_variation),PV_result=L.record_value(pv.result),control_seconds=b['seconds'],control_depth=b['decision']['completed_depth'],control_events=b['decision']['nodes']+b['decision']['qnodes'],candidate_events=dec.nodes+dec.qnodes))
            print('CLOCK-UI',key,'cap',row['actual_requested_depth_cap'],'D',dec.completed_depth,'WDL',value,'seconds',round(row['seconds'],4),flush=True)
        status='CLOSED'
    except Exception:write_json(d/'failure.json',dict(at=stamp(),attempted=attempted,queries=count,traceback=traceback.format_exc()));raise
    finally:write_json(d/'receipt.json',dict(status=status,started_at=started,ended_at=stamp(),seconds=time.perf_counter()-tick,attempted=attempted,queries=count,source_sha256=plan['source_sha256']))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True,type=Path);run(p.parse_args().directory)
