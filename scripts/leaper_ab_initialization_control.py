"""Changed-premise initialization control, not extra epochs of the unit pilot.

Same original contact mu and unchanged learner/search. Two symmetric log-scale
initial ratios (.5, 2), both retained; no winner, price, seed or model selection.
"""
from pathlib import Path
import argparse,json,time
from dataclasses import asdict
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import source_documents,SOURCE,restore,write
from scripts.leaper_microgames import role_stop_requested
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,TDLeafEpisode,play_episode,BudgetEnd


def plan(output):
    output.mkdir(parents=True,exist_ok=False);docs=source_documents();world=json.loads(docs['contact/inputs.json']);slots=[]
    for initial in (.5,2.):
        for root in range(4):slots.append(dict(id=len(slots),phase='train',initial=initial,root=root,role=root%2,arm='TD'))
    for initial in (.5,2.):
        for root in range(4):
            for role in (0,1):
                for arm in (('Initial','TD')if(root+role)%2==0 else('TD','Initial')):
                    slots.append(dict(id=len(slots),phase='eval',initial=initial,root=root,role=role,arm=arm))
    spec=dict(source=SOURCE,producer_sha256=L.sha(Path(__file__)),world=world,slots=slots,
        changed_premise='Unit pilot selected only fixed-A nonterminal PV features despite nonzero error. Test leaf-selection/initialization starvation by changing ONLY initial B to symmetric .5 and2 controls. Not unchanged-cap refill or continuation; both separate models reinitialize.',
        question='Can the free coordinate update when a different initial ratio selects B-sensitive PVs, and does this alter matched terminal utility?',
        selection='All original4contactstarts and training roles0/1/0/1, no oracle or outcome root filtering. Both initializations retained, no best-model selection. Exposed intervention, not blind replication.',
        learner=dict(eta=.05,lam=.95,scale=10.),search=dict(depth=4,nodes=8192,qdepth=0,backend='mainline',fresh_per_query=True,equal_capture_ordering=True),
        game_seconds=90,game_nodes=1000000,whole_seconds=900,expected_seconds=300,
        logical_budget='Unit pilot actual<200s plus suffix<=900s, this control<=900s and verification/analysis estimated<2400s; combined<120min. No large run split.',
        opponent='Unit fixed model, same public mainline search and budgets as candidate; preserve all complete records and incomplete UNKNOWN.')
    write(output/'plan.json',spec)


def run(output):
    spec=json.loads((output/'plan.json').read_bytes());assert spec['producer_sha256']==L.sha(Path(__file__))
    with(output/'execution.json').open('x')as f:json.dump(dict(source=SOURCE,started=time.time()),f)
    c=L.compile_rule(L.ruleset_from_dict(spec['world']['rule']));models={x:Model((1,x,0,0))for x in(.5,2.)};rows=[];began=time.perf_counter();frozen=False
    for slot in spec['slots']:
        if role_stop_requested()or time.perf_counter()-began>=spec['whole_seconds']:break
        if slot['phase']=='eval'and not frozen:write(output/'frozen-models.json',{str(k):m.weights for k,m in models.items()});frozen=True
        x=slot['initial'];env=FixedScaleSessionEnv(restore(c,spec['world']['roots'][slot['root']]['record']),unit_type='A')
        model=models[x]if slot['phase']=='train'else Model(models[x].weights if slot['arm']=='TD'else(1,x,0,0));before=list(model.weights);qs=[]
        def cancel():
            if role_stop_requested():raise BudgetEnd('USER_STOP')
            if time.perf_counter()-began>=spec['whole_seconds']:raise BudgetEnd('WHOLE_CAP_UNKNOWN')
        def observed(ply,actor,r):qs.append(dict(ply=ply,actor=actor,state_sha256=L.state_sha(env.session.state),receipt=L.record_value(r)))
        result=play_episode(env,model,opponent=Model((1,1,0,0)),learner=TDLeafEpisode()if slot['phase']=='train'else None,
            learner_color=slot['role'],depth=4,query_nodes=8192,max_nodes=spec['game_nodes'],horizon=64,
            seconds=min(spec['game_seconds'],spec['whole_seconds']-(time.perf_counter()-began)),cancel=cancel,on_query=observed,search_backend='mainline')
        env.replay();row=dict(slot=slot,before=before,after=list(model.weights),queries=qs,final_record=env.record(),terminal=L.record_value(env.session.result),result=asdict(result),utility=None if result.outcome is None else result.outcome*(1 if slot['role']==0 else-1))
        write(output/f"game-{slot['id']:03d}.json",row);rows.append(dict(slot=slot,result=asdict(result),before=before,after=list(model.weights),utility=row['utility']))
        write(output/'partial.json',dict(rows=rows,models={str(k):m.weights for k,m in models.items()}));print(slot,result.outcome,result.seconds,model.weights,result.update,flush=True)
    if not frozen:write(output/'frozen-models.json',{str(k):m.weights for k,m in models.items()})
    write(output/'result.json',dict(status='CLOSED',seconds=time.perf_counter()-began,rows=rows,unstarted=spec['slots'][len(rows):],models={str(k):m.weights for k,m in models.items()}))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('plan','run'));ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();globals()[a.mode](a.output)
