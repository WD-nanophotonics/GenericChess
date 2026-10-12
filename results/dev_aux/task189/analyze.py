"""Allsixopponent-distribution learning outcomes and candidate-only sensitivity."""
import json,math,statistics,hashlib
from fractions import Fraction as F
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task189';O.mkdir(exist_ok=True);P=R/'results/dev_aux/task187';C=json.loads((P/'controller.json').read_bytes());D=json.loads((P/'declaration.json').read_bytes());assert C['completed']
byname={c['context']['name']:c for c in C['calls']}
def dist(w):return statistics.mean(abs(math.log(w[k]/208/D['human_reference'][k])) for k in 'NBRQ')
def select(v):return max(range(3),key=lambda i:v[i]) if max(v)>v[0] else 0
def scaled(c):
 r=c['result'];s=r['score'];color=c['context']['agent_color']
 if s['terminal']:return 0 if s['winner'] is None else (1 if s['winner']==color else -1)*(240 if c['context']['opponent'].endswith('bounded') else 24000+15*(16-s['played_plies']))
 return 16*s['quantity_difference']
def bounded(c):
 s=c['result']['score'];color=c['context']['agent_color']
 if s['terminal']:return 0 if s['winner'] is None else (1 if s['winner']==color else -1)
 return s['quantity_difference']/15
rows=[];curves=[];ties=[];loo=[]
for run in C['runs']:
 seed=run['seed'];opponent=run['opponent']
 for index,u in enumerate(run['updates']):
  sweep=index//4;k=index%4;groups=[]
  for arm in range(3):
   group=[byname[f's{seed}-{opponent}-train-g{sweep}-k{k}-a{arm}-o{oi}-c{int(color)}'] for oi in range(len(D['train_roots'])) for color in (True,False)];groups.append([scaled(c) for c in group])
   for c,v in zip(group,groups[-1]):assert abs(c['result']['reward']-v/240)<1e-10
  totals=list(map(sum,groups));exact=select(totals)
  if exact!=u['selected']:ties.append(dict(seed=seed,opponent=opponent,sweep=sweep,coordinate=u['coordinate'],actual=u['selected'],exact=exact))
  changed=[]
  for oi in range(len(D['train_roots'])):
   totals2=[total-sum(g[2*oi:2*oi+2]) for total,g in zip(totals,groups)]
   if select(totals2)!=exact:changed.append(oi)
  loo.append(dict(seed=seed,opponent=opponent,sweep=sweep,coordinate=u['coordinate'],removed_roots_changing_choice=changed))
  if k==3:curves.append(dict(seed=seed,opponent=opponent,sweep=sweep,training_games=(sweep+1)*len(D['train_roots'])*2*3*4,reference_distance=dist(u['after']),weights=u['after']))
 arms={}
 for arm in ('initial','final'):
  group=[c for c in C['calls'] if c['context']['start_seed']==seed and c['context']['opponent']==opponent and c['context']['phase']=='heldout' and c['context']['arm']==arm];assert len(group)==2*len(D['heldout_roots'])
  arms[arm]=dict(objective_mean=statistics.mean(c['result']['reward'] for c in group),original_mean=statistics.mean(c['result']['original_reward'] for c in group),quantity_mean=statistics.mean(c['result']['score']['quantity_difference']/15 for c in group),bounded_mean=statistics.mean(bounded(c) for c in group),mate_wins=sum(c['result']['score']['termination']=='CHECKMATE' and c['result']['score']['winner']==c['context']['agent_color'] for c in group),mate_losses=sum(c['result']['score']['termination']=='CHECKMATE' and c['result']['score']['winner']!=c['context']['agent_color'] for c in group),cutoffs=sum(not c['result']['score']['terminal'] for c in group),cutoff_component_mean=statistics.mean(c['result']['score']['cutoff_quantity_component'] for c in group),speed_component_mean=statistics.mean(c['result']['score']['mate_speed_component'] for c in group))
 pairs=[]
 for oi in range(len(D['heldout_roots'])):
  for color in (True,False):
   pair=[byname[f's{seed}-{opponent}-heldout-g0-k0-a{arm}-o{oi}-c{int(color)}'] for arm in ('initial','final')]
   pairs.append(dict(root=oi,color=color,objective_delta=pair[1]['result']['reward']-pair[0]['result']['reward'],original_delta=pair[1]['result']['original_reward']-pair[0]['result']['original_reward'],quantity_delta=(pair[1]['result']['score']['quantity_difference']-pair[0]['result']['score']['quantity_difference'])/15,bounded_delta=bounded(pair[1])-bounded(pair[0])))
 rows.append(dict(seed=seed,opponent=opponent,initial_weights=run['initial_weights'],final_weights=run['final_weights'],initial_Pnormalized={k:run['initial_weights'][k]/208 for k in 'NBRQ'},final_Pnormalized={k:run['final_weights'][k]/208 for k in 'NBRQ'},initial_distance=dist(run['initial_weights']),final_distance=dist(run['final_weights']),updates=sum(u['selected']!=0 for u in run['updates']),heldout=arms,paired_quantity_mean=statistics.mean(p['quantity_delta'] for p in pairs),paired_objective_mean=statistics.mean(p['objective_delta'] for p in pairs),paired_original_mean=statistics.mean(p['original_delta'] for p in pairs),paired_original_median=statistics.median(p['original_delta'] for p in pairs),paired_bounded_mean=statistics.mean(p['bounded_delta'] for p in pairs),pairs=pairs))
out=dict(complete=True,source_controller_sha256=hashlib.sha256((P/'controller.json').read_bytes()).hexdigest(),all_start_results=rows,reference_curves=curves,exactreward_choice_changes=len(ties),exactreward_changes=ties,leave_one_root_out_choice_changes=sum(bool(l['removed_roots_changing_choice']) for l in loo),leave_one_root_out=loo,scope='Allfreshstartends, allgeometryheldouts; trainingroots exposedpilot and reachablefullarmyfixeddistribution. Descriptivehumanreference neverfitting. Samecandidate exact/clusterrescoring notfuturelearning orconfidenceinterval.')
(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(results=[{k:r[k] for k in ('seed','opponent','final_Pnormalized','initial_distance','final_distance','paired_original_mean','paired_bounded_mean','heldout')} for r in rows],exact_choice_changes=len(ties),loo_changes=out['leave_one_root_out_choice_changes']),indent=2))
