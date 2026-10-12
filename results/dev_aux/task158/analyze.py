"""Allstartresults, pairedheldouts and exactreward/cluster sensitivity; no fitting."""
import json,math,statistics,hashlib
from fractions import Fraction as F
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task158';O.mkdir(exist_ok=True);P=R/'results/dev_aux/task152';C=json.loads((P/'controller.json').read_bytes());D=json.loads((R/'results/dev_aux/task152/declaration.json').read_bytes());assert C['completed']
def scaled(c):
 if c['result'] is None:return 0
 r=c['result'];s=r['score']
 if s['terminal']:
  if s['winner'] is None:return 0
  return (1 if s['winner']==c['context']['agent_color'] else -1)*(24000+15*(16-s['played_plies']))
 return 16*s['quantity_difference']
def distance(w):return statistics.mean(abs(math.log(w[k]/208/D['human_reference'][k])) for k in 'NBRQ')
def select(v):return max(range(3),key=lambda i:v[i]) if max(v)>v[0] else 0
byname={c['context']['name']:c for c in C['calls']};ties=[];loo=[];rows=[];curves=[]
for run in C['runs']:
 seed=run['seed'];align=run['alignment'];frozen_w=run['final_weights']
 for u in run['updates']:
  index=run['updates'].index(u);sweep=index//4;k=index%4;groups=[]
  for arm in range(3):
   group=[byname[f's{seed}-align{align}-train-g{sweep}-k{k}-a{arm}-o{oi}-c{int(color)}'] for oi in range(8) for color in (True,False)]
   groups.append([scaled(c) for c in group])
   for c,scaled_v in zip(group,groups[-1]):assert abs((0 if c['result'] is None else c['result']['reward'])-scaled_v/240)<1e-10
  totals=list(map(sum,groups));exact=select(totals)
  if exact!=u['selected']:ties.append(dict(seed=seed,alignment=align,sweep=sweep,coordinate=u['coordinate'],actual_selected=u['selected'],exact_selected=exact,exact_totals=totals,float_means=u['means'],scope='Sameexposedcandidategroups only; no counterfactualtrajectory inferred'))
  changed=[]
  for oi in range(8):
   local=[total-sum(group[2*oi:2*oi+2]) for total,group in zip(totals,groups)]
   if select(local)!=exact:changed.append(oi)
  loo.append(dict(seed=seed,alignment=align,sweep=sweep,coordinate=u['coordinate'],exact_selected=exact,removed_openings_changing_choice=changed))
  if k==3:curves.append(dict(seed=seed,alignment=align,sweep=sweep,training_slots=(sweep+1)*192,training_actual_games=sum(c['result'] is not None for c in C['calls'] if c['context']['start_seed']==seed and c['context']['alignment']==align and c['context']['phase']=='train' and int(c['context']['name'].split('-g')[1].split('-')[0])<=sweep),reference_distance=distance(u['after']),weights=u['after']))
 pair_rows=[]
 for oi in range(8):
  for color in (True,False):
   pair=[byname[f's{seed}-align{align}-heldout-g0-k0-a{arm}-o{oi}-c{int(color)}'] for arm in ('initial','final')]
   bounded=[(0 if c['result']['score']['winner'] is None else (1 if c['result']['score']['winner']==color else -1)) if c['result']['score']['terminal'] else c['result']['score']['quantity_difference']/15 for c in pair]
   pair_rows.append(dict(opening=oi,color=color,original_delta=pair[1]['result']['reward']-pair[0]['result']['reward'],bounded_delta=bounded[1]-bounded[0]))
 arms={}
 for arm in ('initial','final'):
  group=[c for c in C['calls'] if c['context']['start_seed']==seed and c['context']['alignment']==align and c['context']['phase']=='heldout' and f'-a{arm}-' in c['context']['name']]
  assert len(group)==16
  arms[arm]=dict(mean_reward=statistics.mean(c['result']['reward'] for c in group),mate_wins=sum(c['result']['score']['termination']=='CHECKMATE' and c['result']['score']['winner']==c['context']['agent_color'] for c in group),wins=sum(c['result']['score']['winner']==c['context']['agent_color'] for c in group),cutoffs=sum(not c['result']['score']['terminal'] for c in group),mean_cutoff_component=statistics.mean(c['result']['score']['cutoff_quantity_component'] for c in group),mean_played_plies=statistics.mean(len(c['result']['actions']) for c in group))
 rows.append(dict(seed=seed,alignment=align,initial_weights=run['initial_weights'],final_weights=frozen_w,initial_Pnormalized={k:run['initial_weights'][k]/208 for k in 'NBRQ'},final_Pnormalized={k:frozen_w[k]/208 for k in 'NBRQ'},initial_distance=distance(run['initial_weights']),final_distance=distance(frozen_w),updates=sum(u['selected']!=0 for u in run['updates']),heldout=arms,paired_original_mean=statistics.mean(p['original_delta'] for p in pair_rows),paired_original_median=statistics.median(p['original_delta'] for p in pair_rows),paired_bounded_mean=statistics.mean(p['bounded_delta'] for p in pair_rows),pairs=pair_rows))
out=dict(complete=True,source_controller_sha256=hashlib.sha256((P/'controller.json').read_bytes()).hexdigest(),all_start_results=rows,reference_curves=curves,exactrewardscale=240,choice_differences_from_exactreward=len(ties),exactreward_choice_differences=ties,leave_one_opening_out_any_change=sum(bool(x['removed_openings_changing_choice']) for x in loo),total_updates=len(loo),cluster_choice_sensitivity=loo,scope='Predeclaredsamehumanreference andmetric beforefreshstarts/outcomes; descriptiveconditionalroute, noexpertfree/universal optimum. Exact/leaveoneopeningout candidate rescoring isdiagnostic, not independentfuturelearning orconfidenceinterval.')
(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(results=[{k:r[k] for k in ('seed','alignment','initial_Pnormalized','final_Pnormalized','initial_distance','final_distance','paired_original_mean','paired_bounded_mean','heldout')} for r in rows],exact_choice_changes=len(ties),loo_changes=out['leave_one_opening_out_any_change']),indent=2))
