"""Already-paid fixed-opponent four-cell analysis. No engine, fitting or rerun."""
import collections,hashlib,json,random,statistics
from pathlib import Path
from scripts.generic_proof_roles import roles,row_role
from scripts.generic_proof_study_audit import quantile,planned_bounds


def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def score(r):return r['payoff'] or 0

def analyze(folder):
    p=Path(folder);plan=load(p/'plan.json');selection=load(p/'selection.json')
    assert type(plan.get('opponent_proof')) is bool,'legacy both-player intervention cannot isolate interaction'
    rows=[json.loads(x) for x in (p/'run/games.jsonl').read_text(encoding='utf-8').splitlines()]
    data=[r for r in rows if r['phase']=='DEV'];base=plan['baseline_index'];chosen=selection['selected_index']
    spec=dict(A=(False,base),B=(True,base),C=(False,chosen),D=(True,chosen))
    families=[f['family'] for f in plan['families'] if f['phase']=='DEV'];by={}
    for r in data:
        assert r.get('opponent_proof')==plan['opponent_proof']
        k=(r['family'],r['color'],r['opponent'],row_role(r),r['proof'],r['price_index'])
        assert k not in by;by[k]=r
    planned=2*len(roles(plan))*len(plan['opponents'])*len(families);cells={}
    for label,(proof,index) in spec.items():
        rr=[r for r in data if r['proof']==proof and r['price_index']==index]
        cells[label]=dict(n=len(rr),net=sum(map(score,rr)),outcomes=dict(collections.Counter(str(r['payoff']) for r in rr)),seconds=sum(r['seconds'] for r in rr),actual_go=sum(s['decision']['source']=='EXTERNAL_SEARCH' for r in rr for s in r['trajectory']),actual_nodes=sum(s['decision']['nodes'] for r in rr for s in r['trajectory']),**planned_bounds(rr,planned,plan))
    results=[];rng=random.Random(2026101557)
    for role in [None]+list(roles(plan)):
        for op in [None]+[o['id'] for o in plan['opponents']]:
            for name,weights in [('solver_at_unit',dict(A=-1,B=1)),('solver_at_learned',dict(C=-1,D=1)),('price_plain',dict(A=-1,C=1)),('price_hybrid',dict(B=-1,D=1)),('price_solver_interaction',dict(A=1,B=-1,C=-1,D=1))]:
                vectors=[];missing=[];changes=collections.Counter();costdiff=[];movesdiff=[]
                for f in families:
                    values=[];costs=[];go=[]
                    for color in (0,1):
                        for opponent in plan['opponents']:
                            if op is not None and opponent['id']!=op:continue
                            for rr in roles(plan):
                                if role is not None and rr!=role:continue
                                bundle={label:by.get((f,color,opponent['id'],rr,*spec[label])) for label in weights}
                                if any(r is None for r in bundle.values()):continue
                                values.append(sum(weights[l]*score(r) for l,r in bundle.items()))
                                costs.append(sum(weights[l]*r['seconds'] for l,r in bundle.items()))
                                go.append(sum(weights[l]*sum(s['decision']['source']=='EXTERNAL_SEARCH' for s in r['trajectory']) for l,r in bundle.items()))
                                if len(weights)==2:
                                    a=next(bundle[l] for l,w in weights.items() if w==-1);b=next(bundle[l] for l,w in weights.items() if w==1)
                                    changes[str(a['payoff'])+'->'+str(b['payoff'])]+=1
                    n=2*(len(plan['opponents']) if op is None else 1)*(len(roles(plan)) if role is None else 1)
                    if len(values)==n:vectors.append(statistics.mean(values));costdiff.append(sum(costs));movesdiff.append(sum(go))
                    else:missing.append(f)
                out=dict(contrast=name,role=role or 'BALANCED',opponent=op or 'MIXED',complete_families=len(vectors),missing_families=missing,paired_outcome_changes=dict(changes))
                if vectors:
                    draws=[statistics.mean(rng.choices(vectors,k=len(vectors))) for _ in range(5000)]
                    out.update(event_delta=statistics.mean(vectors),family95=[quantile(draws,.025),quantile(draws,.975)],family_values=vectors,paired_game_seconds_difference=sum(costdiff),paired_actual_go_difference=sum(movesdiff))
                results.append(out)
    return dict(source=p.as_posix(),source_games_sha256=hashlib.sha256((p/'run/games.jsonl').read_bytes()).hexdigest(),selection_sha256=hashlib.sha256((p/'selection.json').read_bytes()).hexdigest(),new_games=0,new_go=0,retraining=False,fixed_opponent_proof=plan['opponent_proof'],cells=cells,contrasts=results,scope='Exploratory correction using already-exposed8DEVfamilies; full-family paired bootstrap, not confirmatory significance. UNKNOWN is zero finite event but stays unresolved, all matrices retained. Interaction is identified only because opponent policy is fixed. Actual realized time/work differ, not equal-time strength.')

if __name__=='__main__':
    import sys
    out=Path(sys.argv[1]);out.mkdir(exist_ok=False)
    results=[analyze(f) for f in sys.argv[2:]]
    (out/'factorial_report.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    for r in results:print(json.dumps(dict(source=r['source'],cells=r['cells'],contrasts=[c for c in r['contrasts'] if c['role']=='BALANCED' and c['opponent']=='MIXED'])))
