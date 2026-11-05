"""Post-hoc description of the one frozen ABC episode study; zero search calls."""
from __future__ import annotations
import argparse, collections, hashlib, json, math, random, time
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_prior_td_pilot import restore
from generic_chess.learning.incremental import FixedScaleSessionEnv, MATE

def write(p,v):
    p.write_text(json.dumps(v,allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8')
def same(a,b):
    return len(a)==len(b) and all(math.isclose(x,y,rel_tol=1e-12,abs_tol=1e-12) for x,y in zip(a,b))
def raw(w,phi):return sum(a*b for a,b in zip(w,phi))
def select(env,record):
    found=[a for a in env.actions() if L.record_value(a)==record]
    if len(found)!=1:raise ValueError('saved choice not uniquely legal')
    return found[0]
def td_details(row,cfg):
    # Independently expand the frozen backward eligibility sum from retained
    # literal features. This is a descriptive read, never another model update.
    w=row['before'];values=[];gradients=[];receipts=[]
    for event in row['events']:
        if event['kind']!='candidate' or not event['receipt']['complete']:continue
        r=event['receipt'];receipts.append(r)
        if r['pv_terminal']:
            assert r['pv_phi'] is None and r['value'] in (-MATE,0.,MATE)
            value=r['value']/MATE;gradient=[0.]*len(w)
        else:
            value=math.tanh(raw(w,r['pv_phi'])/cfg['scale'])
            assert math.isclose(raw(w,r['pv_phi']),r['value'],abs_tol=1e-12)
            gradient=[0. if j==0 else x*(1-value*value)/cfg['scale'] for j,x in enumerate(r['pv_phi'])]
        values.append(value);gradients.append(gradient)
    terms=[];elig=[0.]*len(w);interior=[0.]*len(w);final=[0.]*len(w)
    for i,(v,g) in enumerate(zip(values,gradients)):
        target=values[i+1] if i+1<len(values) else row['result']['outcome']
        if target is None:break
        elig=[cfg['lam']*x+y for x,y in zip(elig,g)]
        error=target-v;delta=[cfg['eta']*error*x for x in elig]
        component=interior if i+1<len(values) else final
        for j,d in enumerate(delta):component[j]+=d
        terms.append(dict(index=i,ply=[e['ply'] for e in row['events'] if e['kind']=='candidate'][i],
            phi=receipts[i]['pv_phi'],pv_terminal=receipts[i]['pv_terminal'],prediction=v,
            gradient=g,eligibility=elig,error=error,delta=delta,
            target_kind='NEXT_SEARCH_TERMINAL' if i+1<len(values) and receipts[i+1]['pv_terminal'] else 'NEXT_SEARCH_MATERIAL' if i+1<len(values) else 'ACTUAL_OUTCOME'))
    predicted=[a+b+c for a,b,c in zip(w,interior,final)]
    assert same(predicted,row['after'])
    stats=row['result']['update']
    assert len(terms)==stats['samples'] and len(values)==stats['observed_searches']
    if terms:
        assert math.isclose(sum(t['error']**2/2 for t in terms)/len(terms),stats['loss'],abs_tol=1e-12)
        assert math.isclose(sum(abs(terms[-1]['error']*x) for x in terms[-1]['eligibility']),stats['terminal_credit_l1'],abs_tol=1e-12)
    nonzero=[r['pv_phi'][1:3] for r in receipts if not r['pv_terminal'] and any(r['pv_phi'][1:3])]
    rank=0 if not nonzero else 2 if any(a*d!=b*c for a,b in nonzero for c,d in nonzero) else 1
    return dict(slot=row['slot'],before=w,after=row['after'],terms=terms,interior_delta=interior,
        actual_outcome_delta=final,free_feature_rank=rank,free_feature_rows=len(nonzero),
        nonzero_gradient_rows=sum(any(g) for g in gradients),search_terminal_rows=sum(r['pv_terminal'] for r in receipts),
        free_channel_exposure=[sum(not r['pv_terminal'] and r['pv_phi'][j]!=0 for r in receipts) for j in (1,2)])

def analyze(out):
    began=time.perf_counter();cpu=time.process_time()
    cfg=json.loads((out/'plan.json').read_bytes())
    rows=[json.loads(x) for x in (out/'games.jsonl').read_text().splitlines()]
    assert len(rows)==len(cfg['slots'])==36
    compiled={(f,p):L.compile_rule(L.ruleset_from_dict(world['RuleSet'])) for f,worlds in cfg['worlds'].items() for p,world in worlds.items()}
    games=[];training=[];contexts={};qcount=nodes=0
    for row,slot in zip(rows,cfg['slots']):
        assert slot==row['slot'] and row['status']=='RETURNED'
        f=str(slot['family']);phase=slot['phase'];world=cfg['worlds'][f][phase]
        assert row['initial_record']==world['record']
        env=FixedScaleSessionEnv(restore(compiled[f,phase],row['initial_record']),unit_type='A')
        rng=random.Random(slot['seed']);query_details=[];candidate_index=0
        for event_index,event in enumerate(row['events']):
            assert env.terminal() is None and env.player()==event['actor']
            if event['kind']=='Uniform':
                choices=sorted(env.actions(),key=lambda x:json.dumps(L.record_value(x),sort_keys=True))
                choice=choices[rng.randrange(len(choices))]
                assert L.record_value(choice)==event['choice'] and env.player()!=slot['role']
            else:
                r=event['receipt'];assert env.player()==slot['role']
                assert event['ply']==event_index and r['complete'] and r['completed_depth']==2
                choice=select(env,r['action']);leaf=FixedScaleSessionEnv(env.session,unit_type='A')
                assert r['pv_choices'] and r['pv_choices'][0]==r['action']
                for step in r['pv_choices']:leaf.push(select(leaf,step))
                leaf_outcome=leaf.terminal()
                if r['pv_terminal']:
                    assert leaf_outcome is not None and r['value']==MATE*leaf_outcome and r['pv_phi'] is None
                else:
                    assert leaf_outcome is None and list(leaf.features())==r['pv_phi']
                    assert math.isclose(raw(row['before'],r['pv_phi']),r['value'],abs_tol=1e-12)
                detail=dict(ply=event_index,root_phi=env.features(),leaf_phi=r['pv_phi'],leaf_outcome=leaf_outcome,
                    choice=r['action'],value=r['value'],candidate_index=candidate_index)
                query_details.append(detail);candidate_index+=1;qcount+=1;nodes+=r['nodes']
            env.push(choice)
        assert L.record_value(env.session.to_record())==row['final_record']
        assert L.record_value(env.session.result)==row['terminal']
        assert env.terminal()==row['result']['outcome']
        assert len(row['events'])==row['result']['plies']
        assert env.terminal()*(1 if slot['role']==0 else -1)==row['utility']
        env.replay()
        if phase=='eval':
            assert row['result']['update'] is None and row['before']==row['after']
            contexts[slot['id']]=query_details
        else:training.append(td_details(row,cfg))
        games.append(dict(slot=slot,utility=row['utility'],terminal=row['terminal'],plies=row['result']['plies'],
            queries=row['result']['queries'],nodes=row['result']['nodes'],wall_seconds=row['wall_seconds']))
    pairs=[]
    for family in (0,1,2):
        for role in (0,1):
            for rep in (0,1):
                pair={r['slot']['arm']:r for r in rows if r['slot']['phase']=='eval' and r['slot']['family']==family and r['slot']['role']==role and r['slot']['rep']==rep}
                a,b=pair['Unit'],pair['TD'];aa=a['final_record']['actions'];bb=b['final_record']['actions']
                common=next((i for i,(x,y) in enumerate(zip(aa,bb)) if x!=y),min(len(aa),len(bb)))
                assert a['initial_record']==b['initial_record'] and a['slot']['seed']==b['slot']['seed']
                first=None
                if common<min(len(aa),len(bb)):
                    # Same literal rules and complete action prefix; subsequent
                    # random actions need not match when legal sets differ.
                    ea=a['events'][common];eb=b['events'][common]
                    assert ea['kind']==eb['kind']=='candidate'
                    qa=next(q for q in contexts[a['slot']['id']] if q['ply']==common)
                    qb=next(q for q in contexts[b['slot']['id']] if q['ply']==common)
                    assert qa['root_phi']==qb['root_phi']
                    first=dict(Unit=qa,TD=qb)
                    if qa['leaf_phi'] is not None and qb['leaf_phi'] is not None:
                        first['saved_leaf_cross_values']={arm:[raw(w,q['leaf_phi']) for q in (qa,qb)] for arm,w in (('Unit',a['before']),('TD',b['before']))}
                pairs.append(dict(family=family,role=role,rep=rep,seed=a['slot']['seed'],
                    Unit_id=a['slot']['id'],TD_id=b['slot']['id'],common_prefix_plies=common,
                    trajectories_identical=aa==bb,Unit_utility=a['utility'],TD_utility=b['utility'],
                    difference=b['utility']-a['utility'],first_divergence=first))
    result=dict(question=cfg['question'],source=cfg['source'],zero_new_search=True,
        games=games,pairs=pairs,training=training,counts=dict(replayed_games=len(games),queries=qcount,nodes=nodes),
        summary=dict(training_utility=dict(collections.Counter(str(r['utility']) for r in rows if r['slot']['phase']=='train')),
            evaluation_utility={arm:dict(collections.Counter(str(r['utility']) for r in rows if r['slot']['phase']=='eval' and r['slot']['arm']==arm)) for arm in ('Unit','TD')},
            pair_differences=dict(collections.Counter(str(p['difference']) for p in pairs)),
            changed_trajectories=sum(not p['trajectories_identical'] for p in pairs),
            terminal_kinds=dict(collections.Counter(r['terminal']['status'] for r in rows))),
        analysis_wall_seconds=time.perf_counter()-began,analysis_cpu_seconds=time.process_time()-cpu,
        caveats='Posthoc fixed-data description. Two saved PV leaves are not all-action Q or common-opponent continuations. Divergence and realized utility do not label a locally bad action or establish expected policy strength. No tuning/refill.')
    write(out/'analysis.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('training','games','pairs')},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);analyze(p.parse_args().output)
