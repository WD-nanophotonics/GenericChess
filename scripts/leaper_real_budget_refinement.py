"""Paired actual-return study at existing desktop-derived budgets; no UI edit."""
from pathlib import Path
from datetime import datetime,timezone
from contextlib import nullcontext
from dataclasses import replace,asdict
import argparse,hashlib,time,traceback,json
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_first_q_refinement import FirstQRefinement
from scripts.pure_leaper_search_study import append
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped
from generic_chess.ai.budget import ThinkingConfig,ThinkingStrategy,ThinkingPreset,allocate_search_limits
from generic_chess.clock import TimeControl,TimeControlMode

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def limits_for(name):
    cfg=ThinkingConfig(strategy=ThinkingStrategy.FIXED_TIME,move_time_seconds=1.5)if name=='fixed1.5'else ThinkingConfig(preset=ThinkingPreset.BALANCED if name=='balanced50k'else ThinkingPreset.DEEP)
    raw=allocate_search_limits(None,TimeControl(mode=TimeControlMode.NONE),0,1,cfg)
    return raw,raw if name=='fixed1.5'else replace(raw,max_time_seconds=45)
def run(d):
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    plan=L.load(d/'plan.json');data=L.load(d/'inputs.json');assert sha(__file__)==plan['source_sha256']and sha(d/'inputs.json')==plan['inputs_sha256'];assert not(d/'queries.jsonl').exists()and not(d/'receipt.json').exists()
    for f,h in plan['dependencies'].items():assert sha(f)==h
    assert L.load(Path(plan['prior_receipt']))['status']=='CLOSED'
    cases={x['key']:x for x in data['cases']};tick=time.perf_counter();started=stamp();attempted=0;count=0;status='FAILED'
    class Cancel:
        last=0.;flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>=.25:self.last=now;self.flag=stopped()or now-tick>=plan['batch_seconds']
            return self.flag
    try:
        for slot in plan['slots']:
            if Cancel().is_cancelled():raise RuntimeError('role/batch stop, remaining slots UNKNOWN; no refill')
            setup=time.perf_counter();case=cases[slot['key']];c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]));s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256'];player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning());raw,limits=limits_for(slot['budget']);assert asdict(raw)==plan['budgets'][slot['budget']]['ui_allocated_limits']and asdict(limits)==plan['budgets'][slot['budget']]['actual_limits']
            setup_seconds=time.perf_counter()-setup;begin=stamp();qt=time.perf_counter();qc=time.process_time();policy=FirstQRefinement()if slot['arm']=='refined'else None
            with policy if policy else nullcontext():attempted+=1;decision=player.choose_action(s,limits,cancel_token=Cancel())
            end=stamp();row=dict(slot=slot,started_at=begin,ended_at=end,seconds=time.perf_counter()-qt,cpu_seconds=time.process_time()-qc,setup_seconds=setup_seconds,caller_seconds=time.perf_counter()-setup,decision=L.record_value(decision),state_sha256=L.state_sha(s.state),tuning=L.record_value(SearchTuning()),evaluation_profile=L.record_value(player.evaluation_profile),policy_counts=dict(policy.counts)if policy else{})
            append(d/'queries.jsonl',row);count+=1
            pv=replay(c,case['record']);steps=0
            for action in decision.principal_variation:assert action in pv.legal_actions();pv.submit(action);steps+=1
            labels={json.dumps(x['action'],sort_keys=True):x['truth']['value']for x in case['labelled_actions']};value=labels[json.dumps(L.record_value(decision.action),sort_keys=True)]
            append(d/'qualification.jsonl',dict(slot=slot,pv_steps=steps,chosen_global_WDL=value,correct=value==case['root_global_WDL'],node_target_censored=slot['budget']!='fixed1.5'and decision.termination_reason=='time_limit'))
            print('UI-BUDGET',count,slot['budget'],slot['key'],slot['arm'],decision.completed_depth,value,decision.termination_reason,round(row['seconds'],3),flush=True)
        status='CLOSED'
    except Exception:write_json(d/'failure.json',dict(at=stamp(),attempted=attempted,queries=count,traceback=traceback.format_exc()));raise
    finally:write_json(d/'receipt.json',dict(status=status,started_at=started,ended_at=stamp(),seconds=time.perf_counter()-tick,attempted=attempted,queries=count,source_sha256=plan['source_sha256']))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True,type=Path);run(p.parse_args().directory)
