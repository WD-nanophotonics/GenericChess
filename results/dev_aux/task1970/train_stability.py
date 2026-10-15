"""TRAIN-only stability diagnostics; never selects a DEV winner or new game."""
from pathlib import Path
from collections import Counter
import json,random,statistics
OUT=Path('results/dev_aux/task1970');ROOT=Path('results/dev_aux/task1965')
def run():
    results=[];tables=[]
    for cohort in (0,1):
        d=ROOT/f'cohort{cohort}'
        assert json.loads((d/'FULL-lock-before-dev.json').read_text(encoding='utf-8'))['physical_games']==416
        # TRAINprefix isclosed andneverrewritten; doNOTreadliveDEVappend.
        with (d/'games.jsonl').open(encoding='utf-8') as stream:rows=[json.loads(stream.readline()) for _ in range(416)]
        train=[x for x in rows if x['phase'] in ('RACE','CONTROL')];assert len(train)==416
        grid=sorted({x['R'] for x in train});table={r:[sum(x['finite_event_score'] for x in train if x['family']==f and x['R']==r)/2 for f in range(16)] for r in grid}
        means={r:sum(table[r])/16 for r in grid};best=min(grid,key=lambda r:(-means[r],r));rng=random.Random(20261016651970+cohort)
        counts=Counter();unique=0
        for _ in range(10000):
            ids=[rng.randrange(16) for j in range(16)];scores={r:sum(table[r][j] for j in ids) for r in grid};bestset=[r for r in grid if scores[r]==max(scores.values())]
            counts[min(bestset)]+=1;unique+=len(bestset)==1
        lofo=[min(grid,key=lambda r:(-sum(v for j,v in enumerate(table[r]) if j!=f),r)) for f in range(16)]
        full=json.loads((d/'FULL-lock-before-dev.json').read_text(encoding='utf-8'));race=json.loads((d/'RACE-lock-before-control.json').read_text(encoding='utf-8'))
        assert best==full['selected_R']
        result=dict(cohort=cohort,selected_R=best,race_R=race['selected_R'],TRAINmeans=means,empirical_best_set=[r for r in grid if means[r]==max(means.values())],bootstrap10000_selected_counts=dict(counts),bootstrap_unique_maximum_count=unique,LOFO_selected_R=lofo,nonflat_families=sum(len({table[r][f] for r in grid})>1 for f in range(16)),family_mean_scores=table,scope='TRAINlabels only; resamples same16paidfamilies/physicalpolicyrealization, not independentTRAINreplications or new training/searchcalls. Numericascendingties favor lowprices explicitly. Never change eitherlock/DEV/resultweights fromthisdiagnostic.')
        results.append(result);tables.append(table)
    transfer=[]
    for source,target in ((0,1),(1,0)):
        for selector in ('selected_R','race_R'):
            r=results[source][selector];ds=[tables[target][r][f]-tables[target][720][f] for f in range(16)]
            transfer.append(dict(source_cohort=source,target_cohort=target,selector=selector,R=r,other_TRAIN_mean_delta=sum(ds)/16,family_deltas=ds,scope='Posthoc cross-table description, otherTRAINpreviouslyexposed; not substitute for actualindependentDEV.'))
    with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(dict(status='PASS',cohorts=results,cross_TABLE_description=transfer,new_games_or_search_calls=0,scientific_status='OPEN'),f,indent=2)
    print(json.dumps(dict(status='PASS',summary=[{k:x[k] for k in ('cohort','selected_R','race_R','empirical_best_set','nonflat_families','bootstrap10000_selected_counts','LOFO_selected_R')} for x in results])))
if __name__=='__main__':run()
