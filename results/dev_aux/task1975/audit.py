"""ColdPN1Kretraining versus SAME4KTRAINsurface; no DEVpricefit."""
from pathlib import Path
from collections import Counter
import json,hashlib,random
from results.dev_aux.task1956.physical_audit import audit,lines,read
OUT=Path('results/dev_aux/task1975');ROOT=Path('results/dev_aux/task1974')
def main():
    physical=audit(ROOT);assert physical['full_study_complete']
    p=read(ROOT/'run-plan.json');assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in p['source_sha'].items())
    rows=lines(ROOT/'games.jsonl');assert len(rows)==416 and all(x['family']<16 and x['phase']=='EXPOSED_TRAIN_1K' and x['candidate_proof_nodes']==1024 for x in rows)
    with Path('results/dev_aux/task1965/cohort0/games.jsonl').open(encoding='utf-8') as stream:old=[json.loads(stream.readline()) for _ in range(416)]
    assert len(old)==416 and all(x['phase']!='DEV' for x in old)
    old_by={(x['family'],x['candidate_side'],x['R']):x for x in old};grid=p['prices'];scores={r:sum(x['finite_event_score'] for x in rows if x['R']==r) for r in grid};selected=min(grid,key=lambda r:(-scores[r],r))
    oldscores={r:sum(x['finite_event_score'] for x in old if x['R']==r) for r in grid}
    transitions=Counter();samepaths=0
    for x in rows:
        y=old_by[x['family'],x['candidate_side'],x['R']];transitions[y['outcome']+'->'+x['outcome']]+=1;samepaths+=x['record']==y['record']
    table={r:[sum(x['finite_event_score'] for x in rows if x['family']==f and x['R']==r)/2 for f in range(16)] for r in grid}
    rng=random.Random(20261016651975);counts=Counter()
    for _ in range(10000):
        ids=[rng.randrange(16) for j in range(16)];means={r:sum(table[r][j] for j in ids) for r in grid};counts[min(grid,key=lambda r:(-means[r],r))]+=1
    cost=sum(x['seconds'] for x in rows);oldcost=sum(x['seconds'] for x in old)
    result=dict(status='PASS',physical=physical,selected_R=selected,selected_ratio=selected/720,allTRAIN_net=scores,original4K_TRAIN_net=oldscores,old4K_selected_R=min(grid,key=lambda r:(-oldscores[r],r)),same_complete_paths=samepaths,outcome_transitions=dict(transitions),cost_seconds=cost,old4K_cost_seconds=oldcost,cost_ratio=cost/oldcost,bootstrap10000_sameTRAIN_selected_counts=dict(counts),no_DEV_read=True,Native_qualification_reused=p['qualification_reuse'],new_Native_perfts=0,actual_new_policy_games=416,source_unchanged=True,scope='ALL16EXPOSEDcohort0TRAINfamilies/all13arms/bothroles/newcoldPN1K actualretraining. Same4KTRAINsurface/resourcecurve, notfreshvalidation orindependentthirdTRAINseed. Changedcandidateproofbudgetdefinesdifferentcompletepolicy; no claiming1Kretains4Koptimum/payoffs or universalprice. Chronologicalsamehostcost, no exclusive/noisefreespeedup or directPRIMARYunitcomparison.')
    with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:result[k] for k in ('status','selected_ratio','old4K_selected_R','cost_seconds','old4K_cost_seconds','cost_ratio','same_complete_paths','outcome_transitions','bootstrap10000_sameTRAIN_selected_counts')}))
if __name__=='__main__':main()
