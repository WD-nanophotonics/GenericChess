"""Finite policy portraits from the already saved mixed two-Fers opening.

Fresh per-game Player, retained within-game TT; complete original histories.
No WDL oracle, no learned prices, no result imputation or frozen-run refill.
"""
from __future__ import annotations
import argparse,json,random,time,traceback
from pathlib import Path
from datetime import datetime,timezone
from scripts import leaper_design as L
from scripts.semantic_probe_cost import unit_evaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import write_json
from tools.local_agent import session

POLICIES={'UNIT512':512,'UNIT65536':65536,'FLOOR':None}
def now():return datetime.now(timezone.utc).isoformat()

def game(world,policy,seed,path,deadline):
    assert not path.exists();start=now();tick=time.perf_counter();c=L.compile_rule(L.ruleset_from_dict(world['rule']))
    s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(world['roots'][0]['record'])))
    player=None if policy=='FLOOR' else AlphaBetaPlayer(c,evaluator_override=unit_evaluator(c),tuning=SearchTuning(),use_disk_cache=False)
    rng={0:random.Random(seed),1:random.Random(seed+1)}
    row=dict(status='RUNNING',started_at=start,policy=policy,seed=seed,initial_record=L.record_value(s.to_record()),queries=[],censor=None)
    write_json(path,row)
    while not s.state.terminal_status.is_terminal:
        if session.stopped():row['censor']='user_stop';break
        if time.perf_counter()>=deadline:row['censor']='whole_cap';break
        side=s.state.position.side_to_move;legal=s.legal_actions();t=time.perf_counter()
        q=dict(actor=side,root_ply=s.state.ply_count,state_sha256=L.state_sha(s.state),legal_count=len(legal))
        if side==1:action=legal[rng[1].randrange(len(legal))];q['policy']='RNG'
        elif policy=='FLOOR':action,detail=L.floor(s,rng[0]);q.update(policy='FLOOR',floor=detail)
        else:
            limits=SearchLimits(max_depth=64,max_nodes=POLICIES[policy],max_time_seconds=3,quiescence_max_depth=0,quiescence_hard_max_depth=8)
            d=player.choose_action(s,limits);action=d.action;q.update(policy=policy,decision=L.record_value(d),node_budget=POLICIES[policy],requested_depth=64)
        q.update(action=L.record_value(action),seconds=time.perf_counter()-t)
        row['queries'].append(q);row['current_record']=L.record_value(s.to_record());write_json(path,row)
        if action is None:row['censor']='no_action';break
        assert action in legal;s.submit(action)
    value=None if row['censor'] or not s.state.terminal_status.is_terminal else (0 if s.result.winner is None else (1 if s.result.winner==0 else -1))
    row.update(status='CLOSED',ended_at=now(),seconds=time.perf_counter()-tick,final_record=L.record_value(s.to_record()),final_state=L.record_value(s.state),terminal=L.record_value(s.result),value=value)
    row.pop('current_record',None);write_json(path,row)
    print('GAME',policy,seed,row['terminal'],s.state.ply_count,round(row['seconds'],2),flush=True)
    return row

def pilot(inputs,d):
    assert not d.exists();d.mkdir(parents=True);start=now();tick=time.perf_counter();world=L.load(inputs)['worlds'][1]
    plan=dict(started_at=start,input_sha256=L.sha(inputs),source_sha256=L.sha(Path(__file__)),question='Actual complete-game total cost for a prospective finite policy portrait on one already fixed mixed opening.',policies=['UNIT65536','UNIT512','FLOOR'],seed=202610240701,seconds_cap=600,expected_seconds=150,scope='Three cost games, excluded from later policy-estimation seeds. Complete original setup, H64/repeat4, Q0/check-onlyOFF, Nodebudget+3second cooperative request; all Native/unit leaf+ordering,dynamicsOFF. Bare defender Random. No new rule or fitness refill.')
    write_json(d/'plan.json',plan);rows=[]
    try:
        for policy in plan['policies']:
            if time.perf_counter()-tick>=600:break
            rows.append(game(world,policy,plan['seed'],d/(policy+'.json'),tick+600))
    finally:
        write_json(d/'execution.json',dict(started_at=start,ended_at=now(),seconds=time.perf_counter()-tick,status='CLOSED',finished_policies=[r['policy']for r in rows],source_sha256=plan['source_sha256']))
    return rows


def run(inputs,d,regfile):
    assert not d.exists();d.mkdir(parents=True);reg=L.load(regfile);assert L.sha(inputs)==reg['input_sha256'] and L.sha(Path(__file__))==reg['source_sha256']
    assert reg['expected_total_seconds']<7200 and reg['loop_cap_seconds']<7200
    start=now();tick=time.perf_counter();world=L.load(inputs)['worlds'][1];slots=[dict(seed=seed,policy=p,status='not_started',value=None)for seed in reg['seeds']for p in reg['policies']]
    order=list(range(len(slots)));random.Random(reg['execution_seed']).shuffle(order);out=dict(status='RUNNING',started_at=start,slots=slots,execution_order=order)
    write_json(d/'results.json',out)
    try:
        for ix in order:
            if session.stopped() or time.perf_counter()-tick>=reg['loop_cap_seconds']:break
            slot=slots[ix];path=d/f'game-{ix:03d}.json'
            try:
                row=game(world,slot['policy'],slot['seed'],path,tick+reg['loop_cap_seconds']);slot.update(status='finished',value=row['value'],seconds=row['seconds'],receipt=path.name,terminal=row['terminal'],censor=row['censor'])
            except Exception as exc:
                slot.update(status='failed',failure=repr(exc));write_json(d/f'error-{ix:03d}.json',dict(error=repr(exc),traceback=traceback.format_exc()))
            write_json(d/'results.json',out)
    finally:
        out.update(status='CLOSED',ended_at=now(),seconds=time.perf_counter()-tick,missing=[i for i,s in enumerate(slots)if s['status']!='finished' or s['value'] is None]);write_json(d/'results.json',out)
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['pilot','run']);ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--registration',type=Path);a=ap.parse_args()
    if a.mode=='pilot':pilot(a.input,a.output)
    else:run(a.input,a.output,a.registration)
