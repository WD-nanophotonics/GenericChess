"""Prospective multi-rule pure-Leaper resource calibration, no new policy.
Labels are read only AFTER a Player return. Published data are never executed.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from dataclasses import replace
import json, time, hashlib, traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_certified_choice_timing import label
from scripts.leaper_iteration_choice_observer import IterationChoiceObserver
from scripts.leaper_ordinary_qorder_study import player, metrics, delta
from scripts.pure_leaper_search_study import append
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.benchmark.runner import play_game, RunConfig, _timing_invalid
from generic_chess.ai.benchmark.profiles import PROFILES
from tools.local_agent.common import write_json
from tools.local_agent import session


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class BatchStop(RuntimeError):
    pass


def run(d):
    d=Path(d);plan=L.load(d/'plan.json');data=L.load(d/'fresh-inputs.json')
    assert session.status()['id']==plan['session_id']
    assert sha(d/'fresh-inputs.json')==plan['inputs_sha256']
    for path,h in plan['sources'].items():
        assert sha(path)==h,path
    assert not(d/'queries.jsonl').exists() and not(d/'receipt.json').exists()
    origin=datetime.fromisoformat(plan['logical_origin'])
    assert (datetime.now(timezone.utc)-origin).total_seconds()+plan['total_batch_seconds']+plan['publication_reserve_seconds']<7200,'whole-chain forecast needs USER; do not reset'
    start=stamp();tick=time.perf_counter();count=0;games_done=0;status='FAILED';current=None;phase='curves';last_state=None
    cases={c['key']:c for c in data['cases']}
    class Cancel:
        last=0.;flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>=.25:
                self.last=now
                phase_cap=plan['curve_batch_seconds']if phase=='curves'else plan['game_batch_seconds']
                self.flag=(session.stopped() or now-tick>=plan['total_batch_seconds'] or
                    now-phase_tick>=phase_cap or
                    (datetime.now(timezone.utc)-origin).total_seconds()>=plan['science_end_seconds'])
            return self.flag
    cancel=Cancel();phase_tick=tick

    def query(compiled,state,budget,tag,p=None,observe=False):
        nonlocal count,last_state
        if cancel.is_cancelled():
            raise BatchStop('role/phase/logical budget stop')
        last_state=state;before=L.record_value(state.to_record());began=stamp();qt=time.perf_counter();p=p or player(compiled,'baseline');setup=time.perf_counter()-qt;before_service=metrics(p);obs=IterationChoiceObserver(qt)if observe else None
        limits=SearchLimits(max_time_seconds=budget,max_nodes=1000000)
        try:
            dec=p.choose_action(state,limits,cancel_token=cancel,progress_callback=obs)
        except BaseException:
            append(d/'query-failures.jsonl',dict(tag=tag,root_record=before,started_at=began,ended_at=stamp(),seconds=time.perf_counter()-qt,error=traceback.format_exc()))
            raise
        ended=stamp();row=dict(id=count,tag=tag,started_at=began,ended_at=ended,seconds=time.perf_counter()-qt,setup_seconds=setup,before_record=before,state_sha256=L.state_sha(state.state),limits=L.record_value(limits),decision=L.record_value(dec),profile=L.record_value(p.evaluation_profile),tuning=L.record_value(p._tuning),use_ordering=p._use_ordering,provider_present=before_service['provider'],provider_delta=delta(before_service,metrics(p)),iterations=obs.events if obs else [])
        case=cases[tag['case']]
        if tag['kind']=='curve':
            row['final_label']=label(case,L.record_value(dec.action))
            for e in row['iterations']:
                e['label']=label(case,e['action'])
        append(d/'queries.jsonl',row);count+=1
        if ended>began:
            session.record_work(began,ended,'research',f'{d.as_posix()}/queries.jsonl new source-metadata9rule baseline resource-curve/game query{count}; actual controller/limits/caller/Native counts')
        assert before==L.record_value(state.to_record()) and dec.runtime_pushes==dec.runtime_pops
        assert dec.action in state.legal_actions()
        # No literal PV/label lookup is used to choose, order or stop a move.
        return dec,row
    try:
        for i,slot in enumerate(plan['curve_slots']):
            current=slot;case=cases[slot['case']];c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record'])
            dec,row=query(c,s,slot['seconds'],dict(kind='curve',**slot),observe=True)
            append(d/'curve-results.jsonl',dict(query_id=row['id'],slot=slot,final_label=row['final_label']))
            print('BUDGET-CURVE',i+1,'/',len(plan['curve_slots']),slot['case'],slot['seconds'],dec.completed_depth,row['final_label']['own_WDL'],round(row['seconds'],3),flush=True)
            if i+1==len(cases):
                initial=[json.loads(x)for x in(d/'curve-results.jsonl').read_text().splitlines()]
                if all(r['final_label']['goal_met']is True for r in initial):
                    status='CLOSED_EASY_COHORT';break
        else:
            phase='games';phase_tick=time.perf_counter();cancel.last=0.
            for gslot in plan['game_slots']:
                current=gslot;case=cases[gslot['case']];c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record']);game=gslot['case']+'-high'+str(gslot['higher_color']);game_started=stamp();gt=time.perf_counter()
                class Arm:
                    def __init__(self,budget):
                        self.budget=budget;self.player=player(c,'baseline');self.last_session=None
                    def choose_action(self,state,limits):
                        self.last_session=state
                        return query(c,state,self.budget,dict(kind='game',case=gslot['case'],game=game,side=state.state.position.side_to_move,seconds=self.budget),p=self.player)[0]
                higher=Arm(3.);lower=Arm(1.5)
                try:
                    outcome,events=play_game(c,s.to_record().actions,gslot['case'],game,gslot['higher_color'],higher,lower,RunConfig(PROFILES['baseline'],PROFILES['baseline'],(),seconds=3,nodes=1000000,max_plies=s.state.ply_count+64))
                except BatchStop:
                    partial=higher.last_session or lower.last_session or s
                    append(d/'partial-games.jsonl',dict(game=game,slot=gslot,started_at=game_started,ended_at=stamp(),record=L.record_value(partial.to_record()),result=L.record_value(partial.result),reason='BATCH_STOP; no terminal/draw outcome invented'))
                    raise
                final=higher.last_session or lower.last_session or s
                own_invalid=[dict(ply=e.ply,side=e.side,budget=3. if e.candidate else 1.5,driver_seconds=e.elapsed_seconds)for e in events if _timing_invalid(e.elapsed_seconds,3. if e.candidate else 1.5)]
                eligible=not own_invalid and not outcome.candidate_fallback and not outcome.control_fallback
                append(d/'games.jsonl',dict(game=game,slot=gslot,started_at=game_started,ended_at=stamp(),seconds=time.perf_counter()-gt,outcome=L.record_value(outcome),eligible=eligible,actual_budget_timing_invalid=own_invalid,events=L.record_value(events),initial_record=case['record'],final_record=L.record_value(final.to_record()),final_result=L.record_value(final.result),scope='Same engine resource curve:3s vs1.5s; not equal-resource algorithm/Elo gain. Runner3s flags retained, strict per-arm driver timing separately controls eligibility.'))
                games_done+=1;print('RESOURCE-GAME',games_done,'/',len(plan['game_slots']),game,outcome.result,outcome.plies,eligible,flush=True)
            status='CLOSED'
    except BatchStop:
        status='STOPPED_UNKNOWN'
    except BaseException:
        write_json(d/'failure.json',dict(at=stamp(),current=current,queries=count,games=games_done,error=traceback.format_exc(),last_record=L.record_value(last_state.to_record())if last_state else None))
        raise
    finally:
        write_json(d/'receipt.json',dict(status=status,started_at=start,ended_at=stamp(),seconds=time.perf_counter()-tick,queries=count,games=games_done,current=current,phase=phase,plan_sha256=sha(d/'plan.json'),missing_slots='Any unreturned curve/game slot is NOT_RUN/UNKNOWN, no refill or cap extension.'))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
    run(p.parse_args().directory)
