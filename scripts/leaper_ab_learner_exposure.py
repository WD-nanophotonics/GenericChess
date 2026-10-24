"""AUX consumption of PRIMARY's frozen A/B histories; no rule selection.

Replay retained trajectories, inspect the actual learner channels and literal
PV targets. A separate predeclared pilot calls the unchanged episode learner
on ALL original starts, never on oracle-selected diagnostic histories.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import argparse, hashlib, json, time

from scripts import leaper_design as L
from scripts.leaper_two_type_packet import read_packet
from scripts.leaper_prior_td_pilot import restore, write
from scripts.leaper_microgames import role_stop_requested
from generic_chess.learning.incremental import (
    FixedScaleSessionEnv, Model, TDLeafEpisode, play_episode, BudgetEnd,
)

SOURCE = 'aaa325e4286197ee731c7e61df5106251661f687'
DIRECTORY = Path('docs/research/data/leaper_price_exposure_20261024')


def source_documents():
    return read_packet(DIRECTORY/'packet.json.gz', DIRECTORY/'manifest.json')


def census(output):
    began=time.perf_counter();docs=source_documents();rows=[];worlds={}
    for group in ('two-type','contact'):
        world=json.loads(docs[group+'/inputs.json']);worlds[group]=world
        c=L.compile_rule(L.ruleset_from_dict(world['rule']))
        games=json.loads(docs[group+'/results.json'])['slots']
        for gi,slot in enumerate(games):
            if role_stop_requested():raise RuntimeError('USER_STOP')
            game=json.loads(docs[f'{group}/game-{gi:03d}.json'])
            s=restore(c,game['initial_record']);counts=Counter();features=Counter();pv_features=Counter();gradients=Counter()
            contexts=[]
            for q in game['queries']:
                assert L.state_sha(s.state)==q['state_sha256']
                env=FixedScaleSessionEnv(s,unit_type='A');phi=env.features()
                assert env.names==(('board','A'),('board','B'),('hand','A'),('hand','B'))
                assert phi[2:]==(0,0)
                model=Model((1,1,0,0));gradient=model.gradient(phi)
                features[str(tuple(phi))]+=1;gradients[str(tuple(gradient))]+=1
                counts['contexts']+=1;counts['active_B_root']+=int(gradient[1]!=0)
                leaf=L.GameSession.replay(c,s.to_record())
                for a in q['decision']['principal_variation']:leaf.submit(L.match_action(leaf,a))
                le=FixedScaleSessionEnv(leaf,unit_type='A');terminal=le.terminal()
                lp=None if terminal is not None else le.features()
                if lp is not None:
                    pv_features[str(tuple(lp))]+=1
                    counts['active_B_PV']+=int(model.gradient(lp)[1]!=0)
                    assert lp[2:]==(0,0)
                counts['terminal_PV']+=int(terminal is not None)
                contexts.append(dict(state_sha256=q['state_sha256'],ply=s.state.ply_count,
                    actor=s.state.position.side_to_move,phi=phi,gradient=gradient,
                    leaf_phi=lp,leaf_terminal=terminal,depth=q['decision']['completed_depth']))
                s.submit(L.match_action(s,q['action']))
            assert L.record_value(s.to_record())==game['final_record']
            rows.append(dict(group=group,game=gi,slot=slot,counts=dict(counts),
                root_features=dict(features),PV_features=dict(pv_features),
                gradients=dict(gradients),contexts=contexts))
    result=dict(source=SOURCE,packet_sha256=L.sha(DIRECTORY/'packet.json.gz'),
        seconds=time.perf_counter()-began,rows=rows,
        scope='Retained actual contexts and returned PVs only, not every searched leaf or closed reachability domain. No new Player calls, updates, training or root selection.')
    write(output,result);return result


def plan(output):
    output.mkdir(parents=True,exist_ok=False);docs=source_documents()
    worlds={g:json.loads(docs[g+'/inputs.json'])for g in ('two-type','contact')}
    slots=[]
    for group in worlds:
        for root in range(4):slots.append(dict(id=len(slots),phase='train',group=group,root=root,role=root%2,arm='TD'))
    for group in worlds:
        for root in range(4):
            for role in (0,1):
                # Alternate paired order without choosing from observed outcomes.
                for arm in (('Unit','TD')if (root+role)%2==0 else('TD','Unit')):
                    slots.append(dict(id=len(slots),phase='eval',group=group,root=root,role=role,arm=arm))
    cfg=dict(source=SOURCE,packet_sha256=L.sha(DIRECTORY/'packet.json.gz'),
        producer_sha256=L.sha(Path(__file__)),slots=slots,worlds=worlds,
        question='Does unchanged fixed-scale TDLeaf actually update its free B coordinate on complete original A/B mu, and does the frozen model change matched literal terminal utility?',
        selection='All four original quiet roots and all four original geometric contact roots, equal weights; no truth, frontier, payoff or oracle filtering. Two separate models. No new prefixes or rule selection. Exposed inputs, not holdout.',
        learner=dict(eta=.05,lam=.95,scale=10.,initial=[1.,1.,0.,0.],fixed=0),
        search=dict(backend='mainline',depth=4,nodes=8192,query_seconds=5.,qdepth=0,
            fresh_player_per_query=True,equal_capture_ordering=True,tt=True),
        opponent='Same public mainline q0 search at fixed unit weights, depth4/nodes8192; not Random or PRIMARY persistent Player. Identical opponent for matched Unit/TD.',
        game_seconds=90,game_nodes=1000000,whole_seconds=3000,
        expected_seconds=2400,logical_budget='Pilot<=3000s plus planned suffix<=900s, census/compatibility/analysis estimated<=1800s; total<120min. No artificial split or old-cap refill.',
        stop='One exclusive execution and cumulative cap. No refill/replacement; missing and censored remain UNKNOWN. Freeze both models after training including partial/no-update. No tuning or best-model choice.',
        interpretation='Parameter movement, policy change and literal paired payoff are separate. Do not infer price quality from movement or zero-value gradient. Actual terminal is sole final target; interior observed targets may survive censoring.')
    write(output/'plan.json',cfg);return cfg


def run(output):
    cfg=json.loads((output/'plan.json').read_bytes())
    assert cfg['producer_sha256']==L.sha(Path(__file__))
    assert cfg['packet_sha256']==L.sha(DIRECTORY/'packet.json.gz')
    with (output/'execution.json').open('x',encoding='utf8')as f:json.dump(dict(source=SOURCE,started=time.time()),f)
    began=time.perf_counter();models={g:Model(cfg['learner']['initial'])for g in cfg['worlds']}
    compiled={g:L.compile_rule(L.ruleset_from_dict(w['rule']))for g,w in cfg['worlds'].items()}
    results=[];frozen=False
    for slot in cfg['slots']:
        if role_stop_requested()or time.perf_counter()-began>=cfg['whole_seconds']:break
        if slot['phase']=='eval'and not frozen:
            write(output/'frozen-models.json',{g:m.weights for g,m in models.items()});frozen=True
        group=slot['group'];c=compiled[group];root=cfg['worlds'][group]['roots'][slot['root']]
        env=FixedScaleSessionEnv(restore(c,root['record']),unit_type='A');assert L.state_sha(env.session.state)==root['state_sha256']
        model=models[group]if slot['phase']=='train'else Model(models[group].weights if slot['arm']=='TD'else cfg['learner']['initial'])
        before=list(model.weights);queries=[]
        def cancel():
            if role_stop_requested():raise BudgetEnd('USER_STOP')
            if time.perf_counter()-began>=cfg['whole_seconds']:raise BudgetEnd('WHOLE_CAP_UNKNOWN')
        def observed(ply,actor,receipt):
            queries.append(dict(ply=ply,actor=actor,state_sha256=L.state_sha(env.session.state),
                receipt=L.record_value(receipt)))
        learner=TDLeafEpisode(eta=.05,lam=.95)if slot['phase']=='train'else None
        result=play_episode(env,model,opponent=Model(cfg['learner']['initial']),learner=learner,
            learner_color=slot['role'],depth=4,query_nodes=8192,max_nodes=cfg['game_nodes'],horizon=64,
            seconds=min(cfg['game_seconds'],cfg['whole_seconds']-(time.perf_counter()-began)),
            seed=202610240000+slot['id'],cancel=cancel,on_query=observed,search_backend='mainline')
        env.replay()
        row=dict(slot=slot,before=before,after=list(model.weights),queries=queries,
            initial_record=root['record'],final_record=env.record(),terminal=L.record_value(env.session.result),
            result=asdict(result),utility=None if result.outcome is None else result.outcome*(1 if slot['role']==0 else-1))
        write(output/f"game-{slot['id']:03d}.json",row);results.append(dict(slot=slot,result=asdict(result),before=before,after=list(model.weights),utility=row['utility']))
        write(output/'partial.json',dict(results=results,models={g:m.weights for g,m in models.items()}))
        print(json.dumps(dict(slot=slot,outcome=result.outcome,seconds=result.seconds,weights=model.weights,update=result.update)),flush=True)
    if not frozen:write(output/'frozen-models.json',{g:m.weights for g,m in models.items()})
    summary=dict(status='CLOSED',seconds=time.perf_counter()-began,results=results,
        unstarted=cfg['slots'][len(results):],models={g:m.weights for g,m in models.items()})
    write(output/'result.json',summary);return summary


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('mode',choices=('census','plan','run'));ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    result=globals()[a.mode](a.output)
    print(a.mode,'complete',flush=True)
