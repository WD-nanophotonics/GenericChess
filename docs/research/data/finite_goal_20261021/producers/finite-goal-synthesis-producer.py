"""Derive exact censoring bounds, matched-prefix costs and finite-policy traces."""
from pathlib import Path
from collections import Counter
from fractions import Fraction
import json
from scripts.research_record import write_record
base=Path('artifacts/price-regions-20261021');data=json.loads((base/'mixed-scale-state-48.json').read_text());census=json.loads((base/'finite-decision-census.json').read_text());opening=json.loads((base/'finite-opening-games.json').read_text())
output=base/'finite-goal-synthesis.json'
if output.exists():raise FileExistsError(output)

def utility(g):
    o=g.get('outcome',{});label=o.get('result',g.get('result'))
    invalid=any(o.get(k,False) for k in ('candidate_fallback','control_fallback','candidate_timing_invalid','control_timing_invalid'))
    if invalid:return (-1,1)
    if label=='candidate_win':return (1,1)
    if label=='candidate_loss':return (-1,-1)
    if label=='rule_draw':return (0,0)
    return (-1,1)

def contrast(rows,coeff):
    lo=Fraction(0);hi=Fraction(0)
    for g in rows:
        weight=coeff.get(g['cell'],0);a,b=utility(g)
        lo+=min(weight*a,weight*b);hi+=max(weight*a,weight*b)
    pairs=len({(g['seed'],g['owner']) for g in rows})
    return dict(lower=str(lo/pairs),upper=str(hi/pairs),matched_slots=pairs,kind='Exact identification bounds, not confidence intervals; censored values never imputed')
contrasts={'C-A':{'C':1,'A':-1},'D-A':{'D':1,'A':-1},'D-C':{'D':1,'C':-1},'B-A':{'B':1,'A':-1},'interaction(D-C)-(B-A)':{'D':1,'C':-1,'B':-1,'A':1}}
result=dict(scope='Exposed six-rule diagnostic, correlated finite game/encodings and complete saved histories; no fitting/activation/independent-strength claim.',
    whole_run=dict(seconds=data['wall_seconds'],paid_nodes=data['paid_nodes']),cells={},contrasts={k:contrast(data['games'],v) for k,v in contrasts.items()},families=[],scale_controls=[],matched_prefix_costs=[],finite_census=[],opening_traces=[])
for cell in 'ABCD':
    games=[g for g in data['games'] if g['cell']==cell];events=[e for g in games for e in g['events']];candidate=[e for e in events if e['candidate']]
    assert all(e['candidate']==(e['side']==g['owner']) for g in games for e in g['events'])
    lo=sum(utility(g)[0] for g in games);hi=sum(utility(g)[1] for g in games)
    result['cells'][cell]=dict(outcomes=dict(Counter(g['outcome']['result'] for g in games)),utility_lower=str(Fraction(lo,len(games))),utility_upper=str(Fraction(hi,len(games))),
        events=len(events),candidate_events=len(candidate),all_nodes=sum(e['nodes'] for e in events),candidate_nodes=sum(e['nodes'] for e in candidate),
        all_elapsed=sum(e['elapsed_seconds'] for e in events),candidate_elapsed=sum(e['elapsed_seconds'] for e in candidate),
        depths=dict(Counter(e['completed_depth'] for e in candidate)),terminations=dict(Counter(e['termination_reason'] for e in candidate)),
        fallback=sum(e['fallback'] for e in events),timing_invalid=sum(e['timing_invalid'] for e in events))
for seed in sorted({g['seed'] for g in data['games']}):
    games=[g for g in data['games'] if g['seed']==seed];result['families'].append(dict(seed=seed,contrasts={k:contrast(games,v) for k,v in contrasts.items()},outcomes=[(g['cell'],g['owner'],g['outcome']['result']) for g in games]))
    for owner in (0,1):
        a=next(g for g in games if g['cell']=='A' and g['owner']==owner);b=next(g for g in games if g['cell']=='B' and g['owner']==owner)
        result['scale_controls'].append(dict(seed=seed,owner=owner,identical_record=a['record']==b['record'],same_outcome=a['outcome']['result']==b['outcome']['result']))

def events_by_prefix(game):
    actions=game['record']['actions'];out={}
    for e in game['events']:
        assert not e['action'].startswith('<'),'Declaration needs an explicit separate prefix key'
        if e['candidate']:
            key=json.dumps(actions[:e['ply']-1],sort_keys=True);assert key not in out;out[key]=e
    return out
for left,right in (('A','B'),('A','C'),('B','D'),('C','D')):
    pairs=[]
    for seed in sorted({g['seed'] for g in data['games']}):
        for owner in (0,1):
            a=events_by_prefix(next(g for g in data['games'] if (g['seed'],g['cell'],g['owner'])==(seed,left,owner)))
            b=events_by_prefix(next(g for g in data['games'] if (g['seed'],g['cell'],g['owner'])==(seed,right,owner)))
            for key in a.keys()&b.keys():pairs.append((seed,owner,a[key],b[key]))
    completed=[(a,b) for _,_,a,b in pairs if a['completed_depth']==b['completed_depth']==2]
    result['matched_prefix_costs'].append(dict(left=left,right=right,matched_candidate_histories=len(pairs),both_D2=len(completed),
        identical_D2_node_counts=sum(a['nodes']==b['nodes'] for a,b in completed),
        left_nodes=sum(a['nodes'] for _,_,a,_ in pairs),right_nodes=sum(b['nodes'] for _,_,_,b in pairs),
        left_elapsed=sum(a['elapsed_seconds'] for _,_,a,_ in pairs),right_elapsed=sum(b['elapsed_seconds'] for _,_,_,b in pairs),
        note='Exact complete-history matches; differing trajectories/game lengths cannot be compared as per-node speed. Concurrent load/clock endpoints remain limits.'))
for world in census['worlds']:
    models=sorted({(x['model'],x['depth']) for row in world['rows'] for x in row['checks']});summary=[]
    for model,depth in models:
        phases=[]
        for ply in sorted({r['ply'] for r in world['rows']}):
            rows=[r for r in world['rows'] if r['ply']==ply];mass=sum((Fraction(r['mass']) for r in rows),Fraction(0));regret=Fraction(0);misses=0
            for r in rows:
                x=next(x for x in r['checks'] if (x['model'],x['depth'])==(model,depth));regret+=Fraction(r['mass'])*x['regret'];misses+=x['regret']>0
            phases.append(dict(ply=ply,histories=len(rows),ongoing_mass=str(mass),misses=misses,unconditional_regret=str(regret),conditional_regret=str(regret/mass)))
        checks=[x for r in world['rows'] for x in r['checks'] if (x['model'],x['depth'])==(model,depth)]
        summary.append(dict(model=model,depth=depth,misses=sum(x['regret']>0 for x in checks),nodes=sum(x['decision']['nodes'] for x in checks),phases=phases))
    result['finite_census'].append(dict(world=world['world'],ongoing=len(world['rows']),terminal_leaves=world['terminal_leaves'],summary=summary))
for game in opening['games']:
    world=next(w for w in census['worlds'] if w['world']==game['world']);model=game['model'].rsplit('_D',1)[0];depth=int(game['model'].rsplit('_D',1)[1]);trace=[]
    for e in game['events']:
        if not e['candidate']:continue
        prefix=game['record']['actions'][:e['ply']-1]
        row=next(r for r in world['rows'] if r['record']['actions']==prefix)
        x=next(x for x in row['checks'] if (x['model'],x['depth'])==(model,depth))
        trace.append(dict(ply=row['ply'],best_wdl=row['best_wdl'],selected_wdl=x['selected_wdl'],regret=x['regret']))
    result['opening_traces'].append(dict(world=game['world'],model=game['model'],result=game['outcome']['result'],trace=trace))
write_record(output,result)
print('cells',[(k,v['outcomes'],v['utility_lower'],v['utility_upper'],round(v['candidate_elapsed'],3)) for k,v in result['cells'].items()]);print('contrasts',result['contrasts']);print('matched',result['matched_prefix_costs']);print('opening',result['opening_traces'])
