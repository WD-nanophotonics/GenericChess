"""Two small actual-Native parity qualifications, then ONE cold p49D4 trace.
This is not an old p53D6/D7 trace refill; no policy or horizon change.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,time,hashlib,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_ordinary_qorder_study import player,metrics,delta
from scripts.leaper_iteration_choice_observer import IterationChoiceObserver
from scripts.leaper_assignment_dependencies import AssignmentDependencies
from scripts.pure_leaper_search_study import append
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import write_json
from tools.local_agent import session


def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(d):
    plan=L.load(d/'plan.json');data=L.load(d/'inputs.json');cases={c['key']:c for c in data['cases']}
    assert sha(d/'inputs.json')==plan['inputs_sha256']
    assert session.status()['id']==plan['session_id']
    for f,h in plan['sources'].items():assert sha(f)==h,f
    assert not(d/'queries.jsonl').exists()and not(d/'receipt.json').exists()
    start=stamp();tick=time.perf_counter();count=0;status='FAILED';obs=None;current=None
    class Cancel:
        last=0.;flag=False
        def is_cancelled(self):
            t=time.perf_counter()
            if t-self.last>=.25:self.last=t;self.flag=session.stopped()or t-tick>=plan['batch_seconds']
            return self.flag
    token=Cancel()
    try:
        for slot in plan['slots']:
            assert not token.is_cancelled()
            if count==2:
                rows=[json.loads(x)for x in(d/'queries.jsonl').read_text().splitlines()];a,b=rows
                fields=['action','score','principal_variation','completed_depth','nodes','qnodes','tt_probes','tt_hits','tt_cutoffs','evaluation_calls','runtime_pushes','runtime_pops','pvs_researches']
                assert all(a['decision'][f]==b['decision'][f]for f in fields)
                assert a['provider_delta']==b['provider_delta']
                write_json(d/'qualification.json',dict(passed=True,new_queries=2,fields=fields))
            current=slot;case=cases[slot['case']];c=L.compile_rule(L.ruleset_from_dict(case['rule']));state=replay(c,case['record']);before=L.record_value(state.to_record())
            began=stamp();qt=time.perf_counter();p=player(c,'baseline');m=metrics(p);its=IterationChoiceObserver(qt)
            obs=AssignmentDependencies(depths=(1,2,3)if slot['depth']==3 else(3,4))if slot['observed']else None
            limits=SearchLimits(max_depth=slot['depth'],max_nodes=100000,max_time_seconds=30)
            try:
                if obs:obs.__enter__()
                decision=p.choose_action(state,limits,cancel_token=token,progress_callback=its)
            finally:
                if obs:obs.__exit__(None,None,None)
            ended=stamp();row=dict(slot=slot,started_at=began,ended_at=ended,seconds=time.perf_counter()-qt,before_record=before,state_sha256=L.state_sha(state.state),decision=L.record_value(decision),iterations=its.events,profile=L.record_value(p.evaluation_profile),tuning=L.record_value(p._tuning),provider_present=m['provider'],provider_delta=delta(m,metrics(p)))
            append(d/'queries.jsonl',row);count+=1
            if ended>began:session.record_work(began,ended,'research',f'{d.as_posix()}/queries.jsonl actual assignment-dependency shallowNative query{count}; full root preserved')
            if obs:write_json(d/(slot['key']+'-trace.json'),obs.export())
            assert before==L.record_value(state.to_record())and decision.runtime_pushes==decision.runtime_pops
            assert decision.completed_depth==slot['depth']
            if slot['depth']==4:
                old=L.load(Path(plan['baseline_file']))
                fields=['action','score','principal_variation','completed_depth','nodes','qnodes','tt_probes','tt_hits','tt_cutoffs','evaluation_calls','runtime_pushes','runtime_pops','pvs_researches']
                assert all(old['decision'][f]==row['decision'][f]for f in fields)
                assert old['provider_delta']==row['provider_delta']and old['profile']==row['profile']
                write_json(d/'p49-reused-baseline-parity.json',dict(passed=True,new_queries=1,reused_baseline_queries=1,baseline_sha256=sha(plan['baseline_file']),fields=fields,scope='Same source/controller completeD4 parity. Old baseline is reused evidence, not rerun/new credit. Observer time perturbed.'))
            print('ASSIGNMENT',count,slot,decision.completed_depth,decision.score,round(row['seconds'],3),len(obs.events)if obs else 0,flush=True)
        status='CLOSED'
    except BaseException:
        write_json(d/'failure.json',dict(at=stamp(),current=current,queries=count,error=traceback.format_exc()))
        if obs:write_json(d/'partial-trace.json',obs.export())
        raise
    finally:write_json(d/'receipt.json',dict(status=status,queries=count,started_at=start,ended_at=stamp(),seconds=time.perf_counter()-tick,plan_sha256=sha(d/'plan.json')))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);run(p.parse_args().directory)
