"""Bounded deeper-target cost/learning with unchanged library TDLeaf.

All starts come from the original complete input law. No truth is consulted.
Search depth/resources are explicit policies; completed depth remains evidence.
"""
from pathlib import Path
from dataclasses import asdict
import argparse,json,random,time
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import source_documents,restore,write
from scripts.leaper_microgames import role_stop_requested
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,TDLeafEpisode,play_episode,BudgetEnd

SOURCE='56560fb3e24102792f72a005c5c5bdb52526943f'


def cost_plan(output):
    output.mkdir(parents=True,exist_ok=False)
    world=json.loads(source_documents()['contact/inputs.json'])
    cfg=dict(source=SOURCE,producer_sha256=L.sha(Path(__file__)),worlds={'contact':world},
        question='What does one original-mu complete requestedD6 episode actually cost, expose and learn?',
        selection='First original contact root, role0, unit initialization; source order, no oracle/gradient/payoff selection. This cost episode is paid once and can only be reused under an exact matching later slot.',
        slots=[dict(id=0,phase='train',group='contact',root=0,role=0,arm='D6',seed=2026102600000,depth=6)],
        initial_models={'D6':[1.,1.,0.,0.]},search=dict(nodes=65536,qdepth=0,query_seconds=5,fresh_player_per_query=True,equal_capture_ordering=True),
        learner=dict(eta=.05,lam=.95,scale=10.,unit='A'),game_seconds=180,game_nodes=2000000,whole_seconds=200,
        expected_seconds=120,logical_budget='Cost episode plus implementation/qualification and a conditional small matched deeper-target study expected under120minutes in aggregate. Before choosing that study, inspect measured time/depth/UNKNOWN; no unchanged old run or cap refill.',
        stop='Exclusive execution; censor and unstarted UNKNOWN retained. No result-driven extension, selected checkpoint or oracle TRAIN starts.')
    write(output/'plan.json',cfg)
    return cfg


def one(world,slot,model,cfg,began):
    c=L.compile_rule(L.ruleset_from_dict(world['rule']))
    env=FixedScaleSessionEnv(restore(c,world['roots'][slot['root']]['record']),unit_type='A')
    assert L.state_sha(env.session.state)==world['roots'][slot['root']]['state_sha256']
    events=[];rng=random.Random(slot['seed']);before=list(model.weights)
    def cancel():
        if role_stop_requested():raise BudgetEnd('USER_STOP')
        if time.perf_counter()-began>=cfg['whole_seconds']:raise BudgetEnd('WHOLE_CAP_UNKNOWN')
    def uniform(e):
        actions=sorted(e.actions(),key=lambda a:json.dumps(L.record_value(a),sort_keys=True))
        action=actions[rng.randrange(len(actions))]
        events.append(dict(kind='Uniform',actor=e.player(),state_sha256=L.state_sha(e.session.state),choice=L.record_value(action)))
        return action
    def observed(ply,actor,r):
        events.append(dict(kind='candidate',actor=actor,state_sha256=L.state_sha(env.session.state),receipt=L.record_value(r)))
    remaining=min(cfg['game_seconds'],cfg['whole_seconds']-(time.perf_counter()-began))
    if remaining<=0:return None
    result=play_episode(env,model,opponent=Model((1,1,0,0)),opponent_policy=uniform,
        learner=TDLeafEpisode()if slot['phase']=='train'else None,learner_color=slot['role'],
        depth=slot['depth'],query_nodes=cfg['search']['nodes'],max_nodes=cfg['game_nodes'],
        horizon=64,seconds=remaining,cancel=cancel,on_query=observed,search_backend='mainline')
    env.replay()
    return dict(slot=slot,before=before,after=list(model.weights),events=events,initial_record=world['roots'][slot['root']]['record'],
        final_record=env.record(),terminal=L.record_value(env.session.result),result=asdict(result),
        utility=None if result.outcome is None else result.outcome*(1 if slot['role']==0 else-1))


def run(output):
    cfg=json.loads((output/'plan.json').read_bytes());assert cfg['producer_sha256']==L.sha(Path(__file__))
    with(output/'execution.json').open('x',encoding='utf8')as f:json.dump(dict(started=time.time(),source=SOURCE),f)
    began=time.perf_counter();models={k:Model(v)for k,v in cfg['initial_models'].items()};rows=[];frozen=False
    for slot in cfg['slots']:
        if role_stop_requested()or time.perf_counter()-began>=cfg['whole_seconds']:break
        if slot['phase']=='eval'and not frozen:
            write(output/'frozen-models.json',{k:m.weights for k,m in models.items()});frozen=True
        model=models[slot.get('model_key',slot['arm'])]
        row=one(cfg['worlds'][slot['group']],slot,model,cfg,began)
        if row is None:break
        write(output/f"game-{slot['id']:03d}.json",row)
        rows.append({k:row[k]for k in('slot','before','after','result','utility')})
        write(output/'partial.json',dict(rows=rows,models={k:m.weights for k,m in models.items()},seconds=time.perf_counter()-began))
        print(json.dumps(rows[-1]),flush=True)
    write(output/'frozen-models.json',{k:m.weights for k,m in models.items()})
    result=dict(status='CLOSED',rows=rows,unstarted=cfg['slots'][len(rows):],models={k:m.weights for k,m in models.items()},seconds=time.perf_counter()-began)
    write(output/'result.json',result)
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('cost_plan','run'));ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();globals()[a.mode](a.output)
