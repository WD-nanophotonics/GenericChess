"""Candidate-onlyrewardscale and finaltrain-vs-heldout diagnostics, no newgames."""
import json,statistics,hashlib
from fractions import Fraction as F
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task163';O.mkdir(exist_ok=True)
def sel(v):return max(range(3),key=lambda i:v[i]) if max(v)>v[0] else 0
def payoff(c,lam):
 if c['result'] is None:return F(0)
 r=c['result'];s=r['score'];color=c['context']['agent_color']
 if s['terminal']:
  if s['winner'] is None:return F(0)
  return (1 if s['winner']==color else -1)*(lam+F(16-s['played_plies'],16))
 return F(s['quantity_difference'],15)
sources=[]
for task in (152,160):
 p=R/f'results/dev_aux/task{task}/controller.json';C=json.loads(p.read_bytes());assert C['completed'];byname={c['context']['name']:c for c in C['calls']};records=[];gaps=[]
 for run in C['runs']:
  seed=run['seed'];method=run['alignment'] if task==152 else run['opponent']
  for index,u in enumerate(run['updates']):
   sweep=index//4;k=index%4
   prefix=f's{seed}-align{method}' if task==152 else f's{seed}-{method}'
   groups=[[byname[f'{prefix}-train-g{sweep}-k{k}-a{a}-o{oi}-c{int(color)}'] for oi in range(8) for color in (True,False)] for a in range(3)]
   totals={str(lam):[sum((payoff(c,lam) for c in group),F(0)) for group in groups] for lam in (1,10,100)}
   exact=sel(totals['100']);assert exact==u['selected']
   signature_same=all([None if c['result'] is None else (c['result']['score']['terminal'],c['result']['score']['winner'],c['result']['score']['played_plies'],c['result']['score']['quantity_difference']) for c in groups[0]]==[None if c['result'] is None else (c['result']['score']['terminal'],c['result']['score']['winner'],c['result']['score']['played_plies'],c['result']['score']['quantity_difference']) for c in group] for group in groups[1:])
   records.append(dict(seed=seed,method=method,sweep=sweep,coordinate=u['coordinate'],unique_candidate_prices=len({tuple(sorted(c['weights'].items())) for group in groups for c in group}),same_outcome_signatures_allarms=signature_same,same_exact_means_allarms=len(set(totals['100']))==1,actual_selected=exact,selected_by_lambda={str(lam):sel(totals[str(lam)]) for lam in (1,10,100)},candidate_total_fractions={key:list(map(str,val)) for key,val in totals.items()}))
   if index==23:
    chosen_group=groups[exact];assert all(c['weights']==run['final_weights'] for c in chosen_group)
    held=[c for c in C['calls'] if c['context']['phase']=='heldout' and c['context']['start_seed']==seed and (c['context']['alignment']==method if task==152 else c['context']['opponent']==method) and (f'-afinal-' in c['context']['name'])]
    assert len(held)==16
    train_mean=sum((payoff(c,100) for c in chosen_group),F(0))/16;held_mean=sum((payoff(c,100) for c in held),F(0))/16
    gaps.append(dict(seed=seed,method=method,lastselected_training_mean=float(train_mean),frozen_final_heldout_mean=float(held_mean),lasttrain_minus_heldout=float(train_mean-held_mean),scope='Selectedadaptive trainingblock vsfrozenfreshheldout, geometry/seeddistribution changes; notformalconfidenceinterval.'))
 sources.append(dict(task=task,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),updates=len(records),outcome_plateau_updates=sum(r['same_outcome_signatures_allarms'] for r in records),mean_tie_updates=sum(r['same_exact_means_allarms'] for r in records),lambda1_changed_choices=sum(r['selected_by_lambda']['1']!=r['actual_selected'] for r in records),lambda10_changed_choices=sum(r['selected_by_lambda']['10']!=r['actual_selected'] for r in records),rows=records,train_heldout_gaps=gaps))
out=dict(complete=True,lambda_grid=[1,10,100],sources=sources,scope='Exploratorysameexposedcandidates, nohumanpricefitting/newlearningtrajectory orresult-drivenrunextension. Sourceoriginalreward unchanged; lowerlambda testsonepossibleobjective mechanism only.')
(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([dict(task=s['task'],updates=s['updates'],plateaus=s['outcome_plateau_updates'],mean_ties=s['mean_tie_updates'],lambda1=s['lambda1_changed_choices'],lambda10=s['lambda10_changed_choices'],gaps=s['train_heldout_gaps']) for s in sources],indent=2))
