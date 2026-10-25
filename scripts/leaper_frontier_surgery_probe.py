"""ONE pre-frozen p49D3 causal event replacement; no engine policy patch."""
from pathlib import Path
from datetime import datetime,timezone
import json,time,hashlib,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_ordinary_qorder_study import player,metrics,delta
from scripts.leaper_iteration_choice_observer import IterationChoiceObserver
from scripts.leaper_certified_choice_timing import label
from scripts.leaper_frontier_surgery import FrontierEventReplacement
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import write_json
from tools.local_agent import session


def stamp():return datetime.now(timezone.utc).isoformat()
def run(d):
    plan=L.load(d/'plan.json');data=L.load(d/'inputs.json');case=data['case']
    assert hashlib.sha256((d/'inputs.json').read_bytes()).hexdigest()==plan['inputs_sha256']
    for f,h in plan['sources'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h
    assert not(d/'result.json').exists()and not(d/'receipt.json').exists()
    c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record']);before=L.record_value(s.to_record())
    check=replay(c,case['record'])
    for a in data['target_path']:check.submit(L.match_action(check,a))
    assert L.record_value(check.to_record())==data['target_leaf_record']
    assert check.state.position.side_to_move==data['expected_actor']and check.state.ply_count==data['expected_absolute_ply']
    began=stamp();qt=time.perf_counter();p=player(c,'baseline');m=metrics(p);obs=IterationChoiceObserver(qt);hook=FrontierEventReplacement(data);status='FAILED'
    class Cancel:
        last=0.;flag=False
        def is_cancelled(self):
            t=time.perf_counter()
            if t-self.last>=.25:self.last=t;self.flag=session.stopped()or t-qt>=plan['limits']['batch_seconds']
            return self.flag
    try:
        with hook:dec=p.choose_action(s,SearchLimits(max_depth=3,max_nodes=100000,max_time_seconds=30),cancel_token=Cancel(),progress_callback=obs)
        ended=stamp();row=dict(started_at=began,ended_at=ended,seconds=time.perf_counter()-qt,decision=L.record_value(dec),iterations=obs.events,before_record=before,state_sha256=L.state_sha(s.state),profile=L.record_value(p.evaluation_profile),tuning=L.record_value(p._tuning),provider_delta=delta(m,metrics(p)),interventions=hook.interventions,final_label=label(case,L.record_value(dec.action)))
        write_json(d/'result.json',row)
        if ended>began:session.record_work(began,ended,'research',f'{d.as_posix()}/result.json ONE explicitqfrontier-event intervention,fullinputguard and actualrootoutcome;not a deployablepolicy')
        assert len(hook.interventions)==1 and before==L.record_value(s.to_record())
        assert dec.completed_depth==3 and dec.termination_reason=='completed_depth'and dec.runtime_pushes==dec.runtime_pops
        pv=replay(c,before)
        for a in dec.principal_variation:assert a in pv.legal_actions();pv.submit(a)
        status='CLOSED';print('FRONTIER-EVENT',dec.score,row['final_label'],round(row['seconds'],3),hook.interventions,flush=True)
    except BaseException:
        write_json(d/'failure.json',dict(at=stamp(),error=traceback.format_exc(),interventions=hook.interventions));raise
    finally:write_json(d/'receipt.json',dict(status=status,queries=1 if(d/'result.json').exists()else 0,started_at=began,ended_at=stamp(),seconds=time.perf_counter()-qt,plan_sha256=hashlib.sha256((d/'plan.json').read_bytes()).hexdigest()))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);run(p.parse_args().directory)
