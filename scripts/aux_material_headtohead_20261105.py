"""Frozen-model q0-opponent control: nine physical games, no learning/tuning.

Unit/Unit has one physical baseline per family, reused for two seat views;
TD/Unit has both seat assignments. This is a new opponent endpoint, not a
refill of the closed Uniform comparison or a stronger-teacher training study.
"""
from __future__ import annotations
import argparse, hashlib, json, time
from dataclasses import asdict
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_prior_td_pilot import restore
from scripts.leaper_microgames import role_stop_requested
from generic_chess.learning.incremental import FixedScaleSessionEnv, Model, play_episode, BudgetEnd

def write(p,x):p.write_text(json.dumps(x,allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8')
def read(p):return json.loads(p.read_bytes())
def prepare(study,out):
    out.mkdir(exist_ok=False)
    cfg=read(study/'plan.json');weights=read(study/'frozen_weights.json')
    slots=[]
    for f in (0,1,2):
        for arm,role in (('Unit',0),('TD',0),('TD',1)):
            slots.append(dict(id=len(slots),family=f,arm=arm,role=role))
    plan=dict(study=str(study),source=cfg['source'],slots=slots,frozen_weights=weights,
        config_sha256=hashlib.sha256((study/'plan.json').read_bytes()).hexdigest(),
        producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        question='Does the same frozen learned policy improve or lose actual head-to-head play against pure Unit q0D2, rather than only changing exploitation of Uniform?',
        selection='Same three predeclared movement families and original eval layout1, all retained; no model/seed/family selection. Exposed posthoc opponent control, not independent strength validation.',
        opponent='Existing public q0D2 Unit material model, fresh player per query, same query node/time limits as candidate, no human prior or new search.',
        service=dict(whole_seconds=180.,game_seconds=20.,total_queries=640,total_nodes=1200000,game_nodes=65536,query_nodes=2048,depth=2,horizon=64),
        no_learning=True,stopping='Exactly3Unit/Unit baselines+6TD/Unit seat assignments, no refill/tuning/checkpoint selection. Original36and2causalcontrols stay CLOSED.',
        estimand='Six seat-qualified head-to-head comparisons. Only3physicalUnit baselines reused for two seat views, not6independentbaselinegames. WDLutility and gamepoints explicit; UNKNOWN retained.')
    write(out/'plan.json',plan);print(json.dumps({k:v for k,v in plan.items() if k!='frozen_weights'},indent=2))
def run(out):
    plan=read(out/'plan.json');study=Path(plan['study']);cfg=read(study/'plan.json');sv=plan['service']
    assert plan['producer_sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert plan['config_sha256']==hashlib.sha256((study/'plan.json').read_bytes()).hexdigest()
    with (out/'execution.json').open('x',encoding='utf-8') as f:json.dump({'started_utc':time.time()},f)
    began=time.perf_counter();cpu=time.process_time();total={'queries':0,'nodes':0};rows=[]
    def guard():
        if role_stop_requested():raise BudgetEnd('USER_STOP')
        if time.perf_counter()-began>=sv['whole_seconds']:raise BudgetEnd('HEADTOHEAD_SERVICE_UNKNOWN')
        if total['queries']>=sv['total_queries']:raise BudgetEnd('HEADTOHEAD_QUERY_UNKNOWN')
        if total['nodes']>=sv['total_nodes']:raise BudgetEnd('HEADTOHEAD_NODES_UNKNOWN')
    compiled={str(f):L.compile_rule(L.ruleset_from_dict(cfg['worlds'][str(f)]['eval']['RuleSet'])) for f in (0,1,2)}
    with (out/'games.jsonl').open('x',encoding='utf-8',buffering=1) as stream:
        for slot in plan['slots']:
            guard();cb=time.perf_counter();cc=time.process_time();f=str(slot['family']);events=[]
            env=FixedScaleSessionEnv(restore(compiled[f],cfg['worlds'][f]['eval']['record']),unit_type='A')
            w=cfg['initial'] if slot['arm']=='Unit' else plan['frozen_weights'][f]
            model=Model(w,scale=cfg['scale']);foe=Model(cfg['initial'],scale=cfg['scale'])
            before=list(model.weights)
            def query(ply,actor,receipt):
                total['queries']+=1;total['nodes']+=receipt.nodes
                events.append(dict(ply=ply,actor=actor,kind='candidate' if actor==slot['role'] else 'opponent',receipt=L.record_value(asdict(receipt))))
            result=play_episode(env,model,opponent=foe,learner=None,learner_color=slot['role'],horizon=sv['horizon'],
                depth=sv['depth'],query_nodes=sv['query_nodes'],max_nodes=min(sv['game_nodes'],sv['total_nodes']-total['nodes']),
                seconds=sv['game_seconds']-(time.perf_counter()-cb),seed=202611900+slot['family'],cancel=guard,on_query=query,search_backend='mainline')
            actual=env.terminal();assert actual==result.outcome and result.update is None and model.weights==before
            row=dict(slot=slot,before=before,after=model.weights,foe=foe.weights,result=asdict(result),events=events,
                initial_record=cfg['worlds'][f]['eval']['record'],final_record=L.record_value(env.session.to_record()),
                terminal=L.record_value(env.session.result),utility=None if actual is None else actual*(1 if slot['role']==0 else -1),
                wall_seconds=time.perf_counter()-cb,cpu_seconds=time.process_time()-cc)
            stream.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n');rows.append(row)
            print(json.dumps({k:row[k] for k in ('slot','utility','terminal','wall_seconds')}),flush=True)
    summary=dict(physical_games=len(rows),queries=total['queries'],nodes=total['nodes'],whole_wall_seconds=time.perf_counter()-began,
        whole_cpu_seconds=time.process_time()-cpu,zero_training=True)
    write(out/'summary.json',summary);print(json.dumps(summary))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('prepare','run'));p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();prepare(a.study,a.output) if a.mode=='prepare' else run(a.output)
