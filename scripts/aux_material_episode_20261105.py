"""One bounded AUX TDLeaf/play study using committed mixed-Leaper inputs.

Uses the unchanged public learner, q0 and GameSession. No new rules/search,
source capsule execution, oracle starts, policy defaults or old-panel replay.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, random, subprocess, time
from dataclasses import asdict
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_prior_td_pilot import restore
from scripts.leaper_microgames import role_stop_requested
from generic_chess.learning.incremental import (
    FixedScaleSessionEnv, Model, TDLeafEpisode, play_episode, BudgetEnd,
)

SOURCE = '05a056ad984d7d4be7419b91e746514b606a3b2c'
INPUT = 'docs/research/data/leaper_bound_trials_20261031/q-bound-quality-20261031/inputs.json.gz'
def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, allow_nan=False,
        separators=(',', ':'))+'\n', encoding='utf-8')
def load(path):
    return json.loads(path.read_bytes())
def code_sha():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

def freeze(out):
    out.mkdir(parents=True, exist_ok=False)
    raw = subprocess.check_output(['git','show',SOURCE+':'+INPUT])
    data = json.loads(gzip.decompress(raw))
    worlds = {}
    admission = []
    for family in (0,1,2):
        worlds[str(family)] = {}
        for layout, phase in ((0,'train'),(1,'eval')):
            row = next(x for x in data['rows']
                       if x['family']==family and x['layout']==layout)
            worlds[str(family)][phase] = row
            c = L.compile_rule(L.ruleset_from_dict(row['RuleSet']))
            env = FixedScaleSessionEnv(restore(c,row['record']),unit_type='A')
            assert env.names == (('board','A'),('board','B'),('board','C'),
                                 ('hand','A'),('hand','B'),('hand','C'))
            assert env.terminal() is None
            admission.append(dict(family=family,phase=phase,names=env.names,
                root_phi=env.features(),legal_actions=len(env.actions())))
    slots = []
    for f in (0,1,2):
        for rep in (0,1):
            for role in (0,1):
                slots.append(dict(id=len(slots),phase='train',family=f,role=role,
                    rep=rep,arm='TD',seed=202611050+f*100+rep*10+role))
    for f in (0,1,2):
        for role in (0,1):
            for rep in (0,1):
                for arm in (('Unit','TD') if (f+role+rep)%2==0 else ('TD','Unit')):
                    slots.append(dict(id=len(slots),phase='eval',family=f,role=role,
                        rep=rep,arm=arm,seed=202611500+f*100+rep*10+role))
    cfg=dict(source=SOURCE,input_path=INPUT,input_sha256=hashlib.sha256(raw).hexdigest(),
        producer_sha256=code_sha(),worlds=worlds,admission=admission,slots=slots,
        initial=[1.,1.,1.,0.,0.,0.],eta=.05,lam=.95,scale=10.,
        depth=2,query_nodes=2048,game_nodes=65536,game_seconds=30.,
        total_seconds=900.,total_queries=1200,total_nodes=2400000,horizon=64,
        question='Do actual free B/C TDLeaf updates change paired terminal play on another literal layout in the SAME movement family?',
        selection='Families0/1/2,layout0train/layout1eval,source order fixed without outcome labels; DEVELOPMENT, not population holdout or a price law.',
        changed_premise='New6x6 ABC inputs and actual q0 TDLeaf versus prior homogeneous fixed-feature examples. No closed producer/fitness source is executed.',
        opponent='Fixed legal Uniform policy; sorted complete actions, fresh declared RNG per episode; seed paired across Unit/TD. Not minimax.',
        scope='12train+24eval ceiling; no replacements/refills/tuning. Skip both eval arms for an exactly unchanged family model. No new solver/Native build/default/worker.',
        service='Shared compilation charged to whole900s. Per-episode30s includes restore/env/return packing; cooperative limits, no hard OS preemption.',
        outcomes='Actual scoring terminal only; UNKNOWN neverDRAW. Weights, actions and terminal quality are separate; no full-WDL oracle or strength claim.')
    write(out/'plan.json',cfg)
    return dict(slots=len(slots),admitted=admission,output=str(out))

def run(out):
    cfg=load(out/'plan.json')
    assert cfg['producer_sha256']==code_sha()
    assert cfg.get('opponent_policy','Uniform') in ('Uniform','Unit')
    with (out/'execution.json').open('x',encoding='utf-8') as f:
        json.dump(dict(started_utc=time.time(),source=cfg['source']),f)
    began=time.perf_counter();cpu=time.process_time()
    compiled={}
    for f,world in cfg['worlds'].items():
        for phase,row in world.items():
            compiled[f,phase]=L.compile_rule(L.ruleset_from_dict(row['RuleSet']))
    models={f:Model(cfg['initial'],scale=cfg['scale']) for f in cfg['worlds']}
    totals=dict(queries=0,nodes=0)
    rows=[];frozen=False;fatal=None
    def guard():
        if role_stop_requested():raise BudgetEnd('USER_STOP')
        if time.perf_counter()-began>=cfg['total_seconds']:raise BudgetEnd('STUDY_TIME_UNKNOWN')
        if totals['queries']>=cfg['total_queries']:raise BudgetEnd('STUDY_QUERY_UNKNOWN')
        if totals['nodes']>=cfg['total_nodes']:raise BudgetEnd('STUDY_NODES_UNKNOWN')
    def snapshot():
        return {f:list(m.weights) for f,m in models.items()}
    with (out/'games.jsonl').open('x',encoding='utf-8',buffering=1) as stream:
        for slot in cfg['slots']:
            f=str(slot['family']);phase=slot['phase']
            if phase=='eval' and not frozen:
                write(out/'frozen_weights.json',snapshot());frozen=True
            row=dict(slot=slot)
            if fatal:
                row.update(status='NOT_STARTED',reason=fatal)
            elif phase=='eval' and models[f].weights==cfg['initial']:
                row.update(status='NOT_STARTED_UNCHANGED_MODEL')
            else:
                try:
                    guard()
                except BudgetEnd as exc:
                    fatal=str(exc);row.update(status='NOT_STARTED',reason=fatal)
                else:
                    episode_began=time.perf_counter();episode_cpu=time.process_time()
                    world=cfg['worlds'][f][phase];events=[]
                    model=models[f] if phase=='train' else Model(
                        cfg['initial'] if slot['arm']=='Unit' else models[f].weights,
                        scale=cfg['scale'])
                    row.update(before=list(model.weights),initial_record=world['record'])
                    env=FixedScaleSessionEnv(restore(compiled[f,phase],world['record']),unit_type='A')
                    rng=random.Random(slot['seed'])
                    def opponent(env):
                        choices=sorted(env.actions(),key=lambda x:json.dumps(L.record_value(x),sort_keys=True))
                        action=choices[rng.randrange(len(choices))]
                        events.append(dict(kind='Uniform',actor=env.player(),choice=L.record_value(action)))
                        return action
                    def query(ply,actor,receipt):
                        totals['queries']+=1;totals['nodes']+=receipt.nodes
                        events.append(dict(kind='candidate' if actor==slot['role'] else 'Unit',ply=ply,actor=actor,
                            receipt=L.record_value(asdict(receipt))))
                    try:
                        remaining=cfg['game_seconds']-(time.perf_counter()-episode_began)
                        if remaining<=0:raise BudgetEnd('CONSTRUCTION_TIME_UNKNOWN')
                        ep=play_episode(env,model,opponent=Model(cfg['initial'],scale=cfg['scale']),
                            learner=TDLeafEpisode(eta=cfg['eta'],lam=cfg['lam']) if phase=='train' else None,
                            learner_color=slot['role'],horizon=cfg['horizon'],depth=cfg['depth'],
                            query_nodes=cfg['query_nodes'],max_nodes=min(cfg['game_nodes'],cfg['total_nodes']-totals['nodes']),
                            seconds=remaining,seed=slot['seed'],cancel=guard,
                            on_query=query,search_backend='mainline',opponent_policy=opponent if cfg.get('opponent_policy','Uniform')=='Uniform' else None)
                        actual=env.terminal()
                        assert ep.outcome==actual
                        if phase=='eval':assert row['before']==model.weights
                        row.update(status='RETURNED',result=asdict(ep),after=list(model.weights),
                            utility=None if actual is None else actual*(1 if slot['role']==0 else -1))
                    except Exception as exc:
                        fatal=type(exc).__name__+':'+str(exc)
                        row.update(status='ERROR',error=fatal,after=list(model.weights))
                    row.update(events=events,final_record=L.record_value(env.session.to_record()),
                        terminal=L.record_value(env.session.result))
                    row.update(wall_seconds=time.perf_counter()-episode_began,
                        cpu_seconds=time.process_time()-episode_cpu)
            rows.append(row)
            stream.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n')
            print(json.dumps(dict(id=slot['id'],phase=phase,family=f,status=row['status'],
                ending=row.get('result',{}).get('ending'),outcome=row.get('result',{}).get('outcome'),
                weights=row.get('after'),wall=row.get('wall_seconds')),separators=(',',':')),flush=True)
    if not frozen:write(out/'frozen_weights.json',snapshot())
    summary=dict(source=cfg['source'],whole_wall_seconds=time.perf_counter()-began,
        whole_cpu_seconds=time.process_time()-cpu,totals=totals,
        training_returned=sum(r['status']=='RETURNED' and r['slot']['phase']=='train' for r in rows),
        eval_returned=sum(r['status']=='RETURNED' and r['slot']['phase']=='eval' for r in rows),
        final_weights=snapshot(),fatal=fatal,all_planned_slots=len(rows))
    write(out/'summary.json',summary)
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['freeze','run']);p.add_argument('output',type=Path)
    a=p.parse_args();print(json.dumps(freeze(a.output) if a.mode=='freeze' else run(a.output),separators=(',',':')))
if __name__=='__main__':main()

