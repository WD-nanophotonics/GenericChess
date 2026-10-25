"""Two frozen completed-depth TT numerical-eligibility counterfactuals."""
from pathlib import Path
from datetime import datetime,timezone
import json,time,hashlib,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_ordinary_qorder_study import player,metrics,delta
from scripts.leaper_iteration_choice_observer import IterationChoiceObserver
from scripts.leaper_certified_choice_timing import label
from scripts.leaper_tt_score_counterfactual import NoTTScoreReuse
from scripts.pure_leaper_search_study import append
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import write_json
from tools.local_agent import session


def stamp():return datetime.now(timezone.utc).isoformat()
def run(d):
    plan=L.load(d/'plan.json');assert session.status()['id']==plan['session_id']
    assert hashlib.sha256((d/'inputs.json').read_bytes()).hexdigest()==plan['inputs_sha256']
    for f,h in plan['sources'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h
    assert not(d/'queries.jsonl').exists()and not(d/'receipt.json').exists()
    case=next(c for c in L.load(d/'inputs.json')['cases']if c['key']==plan['case'])
    tick=time.perf_counter();start=stamp();count=0;status='FAILED'
    class Cancel:
        last=0.;flag=False
        def is_cancelled(self):
            t=time.perf_counter()
            if t-self.last>=.25:self.last=t;self.flag=session.stopped()or t-tick>=plan['batch_seconds']
            return self.flag
    token=Cancel()
    try:
        for depth in plan['depths']:
            assert not token.is_cancelled();c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record']);before=L.record_value(s.to_record());began=stamp();qt=time.perf_counter();p=player(c,'baseline');assert not p._tuning.require_full_pv;m=metrics(p);obs=IterationChoiceObserver(qt)
            with NoTTScoreReuse()as diag:
                dec=p.choose_action(s,SearchLimits(max_depth=depth,max_nodes=plan['max_nodes'],max_time_seconds=plan['max_time_seconds']),cancel_token=token,progress_callback=obs)
            ended=stamp();row=dict(depth=depth,started_at=began,ended_at=ended,seconds=time.perf_counter()-qt,before_record=before,decision=L.record_value(dec),iterations=obs.events,profile=L.record_value(p.evaluation_profile),tuning=L.record_value(p._tuning),provider_present=m['provider'],provider_delta=delta(m,metrics(p)),diagnostic=dict(probes=diag.probes,masked_hits=diag.masked_hits,returned_proxy_depth=-1,stored_entries_unchanged_by_probe=True),final_label=label(case,L.record_value(dec.action)))
            append(d/'queries.jsonl',row);count+=1
            if ended>began:session.record_work(began,ended,'research',f'{d.as_posix()}/queries.jsonl explicitTTscoreineligible counterfactual depth{depth}; not an observation-parity claim')
            assert before==L.record_value(s.to_record())and dec.runtime_pushes==dec.runtime_pops
            assert dec.completed_depth==depth and dec.termination_reason=='completed_depth'
            pv=replay(c,case['record'])
            for a in dec.principal_variation:assert a in pv.legal_actions();pv.submit(a)
            print('TT-COUNTERFACTUAL',depth,dec.score,row['final_label'],round(row['seconds'],3),diag.masked_hits,flush=True)
        status='CLOSED'
    except BaseException:
        write_json(d/'failure.json',dict(at=stamp(),queries=count,error=traceback.format_exc()));raise
    finally:write_json(d/'receipt.json',dict(status=status,queries=count,started_at=start,ended_at=stamp(),seconds=time.perf_counter()-tick,plan_sha256=hashlib.sha256((d/'plan.json').read_bytes()).hexdigest()))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);run(p.parse_args().directory)
