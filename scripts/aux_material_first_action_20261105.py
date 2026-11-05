"""Two post-hoc causal first-action controls; original36slots remain closed.

Not a new strength denominator, training run, parameter selection or action-WDL
oracle. Forced TD first difference followed by Unit tail; fixed Uniform stream.
"""
from __future__ import annotations
import argparse, hashlib, json, random, time
from dataclasses import asdict
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_prior_td_pilot import restore
from scripts.leaper_microgames import role_stop_requested
from generic_chess.learning.incremental import FixedScaleSessionEnv, Model, play_episode, BudgetEnd

def write(p,x):p.write_text(json.dumps(x,allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8')
def read(p):return json.loads(p.read_bytes())
def match(env,raw):
    choices=[a for a in env.actions() if L.record_value(a)==raw]
    assert len(choices)==1
    return choices[0]
def prepare(study,out):
    out.mkdir(exist_ok=False)
    a=read(study/'analysis.json');cfg=read(study/'plan.json')
    cases=[p for p in a['pairs'] if p['difference']==-1]
    assert [(p['family'],p['role'],p['rep']) for p in cases]==[(1,0,0),(2,1,1)]
    plan=dict(study=str(study),cases=cases,source=cfg['source'],
        source_games_sha256=hashlib.sha256((study/'games.jsonl').read_bytes()).hexdigest(),
        source_cfg_sha256=hashlib.sha256((study/'plan.json').read_bytes()).hexdigest(),
        source_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        question='Is the first TD-selected action sufficient to destroy the recorded Unit win under the unchanged Unit tail and same Uniform random-number stream?',
        selection='Exactly both observed lost-win pairs, posthoc mechanism only; not blind/population/strength evidence.',
        treatment='Restore exact common full-history prefix; force TDfirst action; thereafter Unit model and unchanged q0D2 play against the same Uniform RNG after consuming its commonprefix draws. No learner.',
        ceiling=dict(games=2,total_seconds=60.,tail_seconds=20.,total_queries=64,total_nodes=131072),
        stopping='Execute2tails once, no replacements/refills/reverse controls/tuning. Original36slots remain closed, original allutilitycounts untouched.',
        interpretation='DRAW/LOSS would make this first action sufficient under the specified Unit tail; WIN means later learned-policy effects matter. Neither identifies minimaxQ or validates a general tie override. UNKNOWN remains unresolved.')
    write(out/'plan.json',plan);print(json.dumps(plan,indent=2))
def run(out):
    plan=read(out/'plan.json');study=Path(plan['study']);cfg=read(study/'plan.json')
    assert plan['source_code_sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert plan['source_games_sha256']==hashlib.sha256((study/'games.jsonl').read_bytes()).hexdigest()
    assert plan['source_cfg_sha256']==hashlib.sha256((study/'plan.json').read_bytes()).hexdigest()
    with (out/'execution.json').open('x',encoding='utf-8') as f:json.dump({'started_utc':time.time()},f)
    began=time.perf_counter();cpu=time.process_time();rows=[];total={'queries':0,'nodes':0}
    old=[json.loads(x) for x in (study/'games.jsonl').read_text().splitlines()]
    def guard():
        if role_stop_requested():raise BudgetEnd('USER_STOP')
        if time.perf_counter()-began>=plan['ceiling']['total_seconds']:raise BudgetEnd('CONTROL_SERVICE_UNKNOWN')
        if total['queries']>=plan['ceiling']['total_queries']:raise BudgetEnd('CONTROL_QUERY_UNKNOWN')
        if total['nodes']>=plan['ceiling']['total_nodes']:raise BudgetEnd('CONTROL_NODES_UNKNOWN')
    with (out/'tails.jsonl').open('x',encoding='utf-8',buffering=1) as stream:
        for case in plan['cases']:
            cb=time.perf_counter();cc=time.process_time();events=[]
            world=cfg['worlds'][str(case['family'])]['eval']
            env=FixedScaleSessionEnv(restore(L.compile_rule(L.ruleset_from_dict(world['RuleSet'])),world['record']),unit_type='A')
            unit=old[case['Unit_id']];td=old[case['TD_id']];rng=random.Random(case['seed'])
            k=case['common_prefix_plies']
            for i in range(k):
                ue,te=unit['events'][i],td['events'][i]
                if ue['kind']=='Uniform':
                    choices=sorted(env.actions(),key=lambda a:json.dumps(L.record_value(a),sort_keys=True))
                    choice=choices[rng.randrange(len(choices))]
                    assert L.record_value(choice)==ue['choice']==te['choice']
                else:
                    assert ue['receipt']['action']==te['receipt']['action']
                    choice=match(env,ue['receipt']['action'])
                env.push(choice)
            prefix=L.record_value(env.session.to_record());assert prefix['actions']==unit['final_record']['actions'][:k]==td['final_record']['actions'][:k]
            assert env.player()==case['role']
            forced=td['events'][k]['receipt']['action'];assert forced!=unit['events'][k]['receipt']['action']
            env.push(match(env,forced));after_forced=L.record_value(env.session.to_record())
            def opponent(e):
                choices=sorted(e.actions(),key=lambda a:json.dumps(L.record_value(a),sort_keys=True))
                choice=choices[rng.randrange(len(choices))]
                events.append(dict(kind='Uniform',actor=e.player(),choice=L.record_value(choice)))
                return choice
            def query(ply,actor,receipt):
                total['queries']+=1;total['nodes']+=receipt.nodes
                events.append(dict(kind='candidate',ply=k+1+ply,actor=actor,receipt=L.record_value(asdict(receipt))))
            guard()
            remaining=plan['ceiling']['tail_seconds']-(time.perf_counter()-cb)
            model=Model(cfg['initial'],scale=cfg['scale'])
            result=play_episode(env,model,opponent=Model(cfg['initial'],scale=cfg['scale']),learner=None,
                learner_color=case['role'],horizon=cfg['horizon']-k-1,depth=cfg['depth'],query_nodes=cfg['query_nodes'],
                max_nodes=min(cfg['game_nodes'],plan['ceiling']['total_nodes']-total['nodes']),seconds=remaining,
                seed=case['seed']+k+1,cancel=guard,on_query=query,search_backend='mainline',opponent_policy=opponent)
            actual=env.terminal();assert actual==result.outcome and result.update is None and model.weights==cfg['initial']
            row=dict(case=case,common_record=prefix,forced_choice=forced,after_forced=after_forced,
                events=events,result=asdict(result),terminal=L.record_value(env.session.result),
                final_record=L.record_value(env.session.to_record()),utility=None if actual is None else actual*(1 if case['role']==0 else -1),
                wall_seconds=time.perf_counter()-cb,cpu_seconds=time.process_time()-cc)
            stream.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n');rows.append(row)
            print(json.dumps({k:row[k] for k in ('utility','terminal','wall_seconds')}),flush=True)
    summary=dict(cases=len(rows),queries=total['queries'],nodes=total['nodes'],whole_wall_seconds=time.perf_counter()-began,
        whole_cpu_seconds=time.process_time()-cpu,utilities=[r['utility'] for r in rows],zero_training=True)
    write(out/'summary.json',summary);print(json.dumps(summary))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('prepare','run'));p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();prepare(a.study,a.output) if a.mode=='prepare' else run(a.output)
