"""Changed-opponent natural learning on all original A/B source starts.

Unchanged TDLeaf/library search; Uniform legal opponent supplies exploration.
No truth-selected start, oracle target, hyperparameter or best-model selection.
"""
from pathlib import Path
from dataclasses import asdict
import argparse,json,time,random
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import source_documents,SOURCE,restore,write
from scripts.leaper_microgames import role_stop_requested
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,TDLeafEpisode,play_episode,BudgetEnd


def plan(output):
    output.mkdir(parents=True,exist_ok=False);docs=source_documents();worlds={g:json.loads(docs[g+'/inputs.json'])for g in('two-type','contact')};slots=[]
    for episode in range(128):
        for wi,group in enumerate(worlds):slots.append(dict(id=len(slots),phase='train',group=group,root=episode%4,role=(episode//4)%2,episode=episode,arm='TD',seed=2026102400000+wi*10000+episode))
    for wi,group in enumerate(worlds):
        for root in range(4):
            for role in(0,1):
                for rep in(0,1):
                    for arm in(('Unit','TD')if(root+role+rep)%2==0 else('TD','Unit')):
                        slots.append(dict(id=len(slots),phase='eval',group=group,root=root,role=role,rep=rep,arm=arm,seed=2026102490000+wi*10000+root*100+role*10+rep))
    cfg=dict(source=SOURCE,worlds=worlds,slots=slots,producer_sha256=L.sha(Path(__file__)),
        question='Can Uniform-opponent natural exploration activate unit-start free-B learning, and does the frozen result improve actual matched W-L beyond Unit on these original source roots?',
        changed_premise='Previous unit-opponent deterministic pilot had no unit-start update; initialization intervention activated gradients but not payoff. Change ONLY opponent to IID Uniform actual legal actions and use new fixed train/eval RNG streams. Reinitialize Unit, no warm continuation or old-slot refill.',
        selection='All4 original quiet and4 original contact complete starts, root index cycle, alternating learner role per4episodes. No prefix, WDL, payoff, gradient or oracle filtering. Separate models per input law. Exposed rules/layouts; new prospective episode seeds are not independent rule holdouts.',
        learner=dict(initial=[1.,1.,0.,0.],eta=.05,lam=.95,scale=10.,unit='A'),
        search=dict(backend='unchanged mainline learner adapter',depth=4,nodes=8192,qdepth=0,fresh_per_query=True,equal_capture_ordering=True),
        train_seconds=1200,eval_seconds=600,whole_seconds=1800,game_seconds=30,game_nodes=250000,expected_seconds=1400,
        budget='New changed-opponent study expected<24min, hard30min; earlier experiments are CLOSED at actual costs. Full logical remaining work including qualification expected<120min. No splitting a long run or result-driven extension.',
        stop='One exclusive run; phase/whole caps preserve unfinished and unstarted UNKNOWN. Freeze the one final model per group including partial/no-update. No checkpoint, seed, rule or parameter selection.',
        comparison='32matched eval pairs, same root/role/opponent RNG seed, two fresh evaluation streams per root/role. After path divergence the same stream acts on different legal sets; not common action trajectories or independent rule samples. Final actual Core W/L/D only.')
    write(output/'plan.json',cfg)


def run(output):
    cfg=json.loads((output/'plan.json').read_bytes());assert cfg['producer_sha256']==L.sha(Path(__file__))
    with(output/'execution.json').open('x')as f:json.dump(dict(started=time.time(),source=SOURCE),f)
    cs={g:L.compile_rule(L.ruleset_from_dict(w['rule']))for g,w in cfg['worlds'].items()};models={g:Model((1,1,0,0))for g in cs};began=time.perf_counter();phase_start=began;phase='train';rows=[]
    for slot in cfg['slots']:
        if slot['phase']!=phase:
            phase=slot['phase'];phase_start=time.perf_counter();write(output/'frozen-models.json',{g:m.weights for g,m in models.items()})
        if role_stop_requested()or time.perf_counter()-began>=1800:break
        allowance=cfg[phase+'_seconds']
        if time.perf_counter()-phase_start>=allowance:continue
        c=cs[slot['group']];world=cfg['worlds'][slot['group']];env=FixedScaleSessionEnv(restore(c,world['roots'][slot['root']]['record']),unit_type='A')
        model=models[slot['group']]if phase=='train'else Model(models[slot['group']].weights if slot['arm']=='TD'else(1,1,0,0));before=list(model.weights);events=[];rng=random.Random(slot['seed'])
        def cancel():
            if role_stop_requested():raise BudgetEnd('USER_STOP')
            if time.perf_counter()-began>=1800:raise BudgetEnd('WHOLE_CAP_UNKNOWN')
            if time.perf_counter()-phase_start>=allowance:raise BudgetEnd('PHASE_CAP_UNKNOWN')
        def uniform(e):
            actions=sorted(e.actions(),key=lambda a:json.dumps(L.record_value(a),sort_keys=True));choice=actions[rng.randrange(len(actions))]
            events.append(dict(kind='Uniform',actor=e.player(),state_sha256=L.state_sha(e.session.state),choice=L.record_value(choice)));return choice
        def observed(ply,actor,r):events.append(dict(kind='candidate',actor=actor,state_sha256=L.state_sha(env.session.state),receipt=L.record_value(r)))
        remaining=min(30,1800-(time.perf_counter()-began),allowance-(time.perf_counter()-phase_start))
        if remaining<=0:continue
        result=play_episode(env,model,opponent=Model((1,1,0,0)),opponent_policy=uniform,learner=TDLeafEpisode()if phase=='train'else None,
            learner_color=slot['role'],depth=4,query_nodes=8192,max_nodes=250000,horizon=64,seconds=remaining,cancel=cancel,on_query=observed,search_backend='mainline')
        env.replay();row=dict(slot=slot,before=before,after=list(model.weights),events=events,final_record=env.record(),terminal=L.record_value(env.session.result),result=asdict(result),utility=None if result.outcome is None else result.outcome*(1 if slot['role']==0 else-1))
        write(output/f"game-{slot['id']:03d}.json",row);rows.append(dict(slot=slot,before=before,after=list(model.weights),result=asdict(result),utility=row['utility']))
        write(output/'partial.json',dict(rows=rows,models={g:m.weights for g,m in models.items()},seconds=time.perf_counter()-began))
        print(slot,'outcome',result.outcome,'ending',result.ending,'seconds',round(result.seconds,3),'weights',model.weights,flush=True)
    if not(output/'frozen-models.json').exists():write(output/'frozen-models.json',{g:m.weights for g,m in models.items()})
    attempted={r['slot']['id']for r in rows}
    write(output/'result.json',dict(rows=rows,unstarted=[s for s in cfg['slots']if s['id']not in attempted],models={g:m.weights for g,m in models.items()},seconds=time.perf_counter()-began))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('plan','run'));ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();globals()[a.mode](a.output)
