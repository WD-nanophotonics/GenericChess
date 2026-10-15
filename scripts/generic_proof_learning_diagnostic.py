"""No-new-go TRAIN stability, action sensitivity and physical-tail attribution."""
import collections,json,random
from pathlib import Path
from scripts.generic_proof_study_audit import quantile,incomplete


def analyze(folder):
    p=Path(folder);plan=json.loads((p/'plan.json').read_text());rows=[json.loads(x) for x in (p/'run/games.jsonl').read_text().splitlines()]
    selection=json.loads((p/'selection.json').read_text());selected=selection['selected_index'];baseline=plan['baseline_index']
    train=[r for r in rows if r['phase']=='TRAIN'];families=sorted({r['family'] for r in train});nprices=len(plan['prices']);perfamily=2*len(plan['opponents'])
    assert not any(incomplete(r,plan) for r in train)
    assert all(sum(r['family']==f and r['price_index']==i for r in train)==perfamily for f in families for i in range(nprices))
    scores={f:[sum(r['payoff'] or 0 for r in train if r['family']==f and r['price_index']==i) for i in range(nprices)] for f in families}
    rng=random.Random(20261015557);counts=collections.Counter()
    for _ in range(5000):
        sample=[rng.choice(families) for _ in families];totals=[sum(scores[f][i] for f in sample) for i in range(nprices)]
        counts[min(range(nprices),key=lambda i:(-totals[i],plan['prices'][i]))]+=1
    actions={};root_sources=collections.Counter()
    for r in train:
        if not r['trajectory']:continue
        key=(r['family'],r['color'],r['opponent']);z=r['trajectory'][0]['decision'];actions.setdefault(key,{})[r['price_index']]=z['action'];root_sources[z['source']]+=1
    varying=sum(len(set(a.values()))>1 for a in actions.values());flatfamilies=sum(len(set(s))==1 for s in scores.values())
    costs=[]
    for phase in ('TRAIN','DEV'):
        for q in (False,True):
            for i in range(nprices):
                data=[r for r in rows if r['phase']==phase and r['proof']==q and r['price_index']==i]
                if not data:continue
                decisions=[(ply,z['decision']) for r in data for ply,z in enumerate(r['trajectory'])]
                costs.append(dict(phase=phase,proof=q,price_index=i,games=len(data),decision_seconds_not_full_games=sum(z['seconds'] for _,z in decisions),recorded_game_seconds=sum(r.get('seconds',0) for r in data) if all('seconds' in r for r in data) else None,proof_nodes=sum(z['proof_nodes'] for _,z in decisions),verification_nodes=sum(z['verification_nodes'] for _,z in decisions),native_nodes=sum(z['search_nodes'] for _,z in decisions),native_go=sum(z['source']=='EXTERNAL_SEARCH' for _,z in decisions),physical_tail_moves=sum(ply>=plan['H'] for ply,z in decisions),physical_tail_decision_seconds=sum(z['seconds'] for ply,z in decisions if ply>=plan['H'])))
    dev=[r for r in rows if r['phase']=='DEV'];lookup={(r['family'],r['proof'],r['price_index'],r['color'],r['opponent']):r for r in dev}
    contrasts=[]
    for op in plan['opponents']:
        pairs=[]
        for f in sorted({r['family'] for r in dev}):
            for color in (0,1):
                B=lookup.get((f,True,baseline,color,op['id']));D=lookup.get((f,True,selected,color,op['id']))
                if B is None or D is None:continue
                prefix=lambda r:(r['payoff'] or 0) if len(r['trajectory'])<=plan['H'] else 0
                before=prefix(D)-prefix(B);after=(D['payoff'] or 0)-(B['payoff'] or 0)
                pairs.append((before,after,after-before))
        contrasts.append(dict(opponent=op['id'],paired_games=len(pairs),prefix_WL_difference=sum(x[0] for x in pairs)/len(pairs) if pairs else None,final_WL_difference=sum(x[1] for x in pairs)/len(pairs) if pairs else None,physical_tail_contribution=sum(x[2] for x in pairs)/len(pairs) if pairs else None))
    result=dict(status='COMPLETE_DESCRIPTIVE_NO_NEW_GO',actual_new_native_go=0,selected=selection['selected'],selected_equals_baseline=selected==baseline,TRAIN_family_count=len(families),TRAIN_bootstrap_selection_counts=dict(counts),bootstrap_resamples=5000,bootstrap_meaning='Resample complete TRAIN families; descriptive finite-objective selection variability on this exposed small grid, not universal parameter posterior.',TRAIN_flat_outcome_families=flatfamilies,TRAIN_root_choices= len(actions),TRAIN_price_sensitive_root_choices=varying,TRAIN_root_sources=dict(root_sources),DEV_by_opponent=contrasts,costs=costs,limitations='Prefix versus final decomposition uses SAME observed policy paths and TRAIN-selected price; no H16 retraining. Counterfactual universal WDL remains unknown. Shared grid paths are not independent online training runs.')
    (p/'learning_diagnostic.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print({k:v for k,v in result.items() if k!='costs'})


if __name__=='__main__':
    import sys
    for folder in sys.argv[1:]:analyze(folder)
