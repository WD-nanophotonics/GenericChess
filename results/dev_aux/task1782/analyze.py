"""Stratified descriptive meta-summary of two predeclared cohort results."""
import json,random,hashlib,sys
from pathlib import Path


def analyze(tasks,outfile):
    records=[];data=[];total=0
    for task in tasks:
        p=Path(f'results/dev_aux/task{task}');plan=json.loads((p/'plan.json').read_text());sel=json.loads((p/'selection.json').read_text());rows=[json.loads(x) for x in (p/'run/games.jsonl').read_text().splitlines()]
        look={(r['family'],r['proof'],r['price_index'],r['color'],r['opponent']):r for r in rows if r['phase']=='DEV'}
        families=[f['family'] for f in plan['families'] if f['phase']=='DEV'];base=plan['baseline_index'];values={label:[] for label in ('solver_policy','price_plain','price_solver')}
        for family in families:
            scores={}
            for q,index,label in [(False,base,'A'),(True,base,'B'),(False,sel['selected_index'],'C'),(True,sel['selected_index'],'D')]:
                ss=[look[family,q,index,color,op['id']]['payoff'] or 0 for color in (0,1) for op in plan['opponents']];scores[label]=sum(ss)/len(ss)
            for left,right,label in [('A','B','solver_policy'),('A','C','price_plain'),('B','D','price_solver')]:values[label].append(scores[right]-scores[left])
        data.append(values);total+=len(families)
        records.append(dict(task=task,selected=sel['selected'],DEV_families=len(families),plan_sha256=hashlib.sha256((p/'plan.json').read_bytes()).hexdigest(),games_sha256=hashlib.sha256((p/'run/games.jsonl').read_bytes()).hexdigest()))
    rng=random.Random(20261015559);summary={}
    for label in data[0]:
        samples=[]
        for _ in range(5000):samples.append(sum(sum(rng.choice(d[label]) for _ in d[label]) for d in data)/total)
        samples.sort();summary[label]=dict(finite_event_difference=sum(sum(d[label]) for d in data)/total,stratified_DEV_family_bootstrap95=[samples[int(.025*4999)],samples[int(.975*4999)]])
    result=dict(status='BOTH_PREDECLARED_COHORTS_COMPLETE',studies=records,summary=summary,actual_new_go_for_analysis=0,interpretation='Complete DEV families stratified within each cohort; each candidate frozen by own independent TRAIN. Conditional finite-player-policy inference, not uncertainty over all training distributions, universal prices, continuous optimum or infinite WDL. Separate studies remain primary evidence.')
    Path(outfile).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':analyze([int(x) for x in sys.argv[2:]],sys.argv[1])
