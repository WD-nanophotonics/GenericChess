"""Verify exposed reward/stability diagnostics without changing frozen outputs."""
import json,statistics
from pathlib import Path
R=Path(__file__).resolve().parents[2];B=R/'results/dev_aux';D=json.loads((B/'task121/controller.json').read_bytes());by={c['context']['name']:c for c in D['calls']};reward=[];stability=[]
for r in D['runs']:
 for g in r['iterations']:
  groups=[[by[f"s{r['seed']}-g{g['generation']}-a{a}-o{o}-c{c}"]['result']['score'] for o in range(4) for c in (1,0)] for a in range(3)];means={}
  for mode in ('original','bounded_terminal','count_at_any_end'):
   means[mode]=[statistics.mean(z['reward'] if mode=='original' else ((1 if z['winner']==bool(c) else -1) if z['terminal'] and z['winner'] is not None else z['cutoff_quantity_component']) if mode=='bounded_terminal' else z['quantity_difference']/15 for c,z in zip((1,0)*4,group)) for group in groups]
  reward.append(dict(seed=r['seed'],generation=g['generation'],actual_selected=g['selected'],means=means,counterfactual_choice={k:max(range(3),key=lambda a:v[a]) for k,v in means.items()},mates_by_arm=[sum(z['termination']=='CHECKMATE' for z in group) for group in groups],limit='same evaluated candidates only; no counterfactual trajectory or learning run'))
  drops=[]
  for omitted in range(4):
   scores=[statistics.mean(z for i,z in enumerate(v) if i//2!=omitted) for v in g['rewards']];drops.append(max(range(3),key=lambda i:scores[i]))
  stability.append(dict(seed=r['seed'],generation=g['generation'],chosen=g['selected'],leave_one_opening_out_choices=drops,stable_all4=all(x==g['selected'] for x in drops),selected_minus_incumbent=g['means'][g['selected']]-g['means'][0]))
assert reward==json.loads((B/'task122/reward_attribution.json').read_bytes())['rows'];assert stability==json.loads((B/'task122/selection_stability.json').read_bytes())['rows']
rows=json.loads((B/'task126/rows.json').read_bytes());tr=[r for r in rows if r['phase']=='train'];te=[r for r in rows if r['phase']=='heldout'];shift=statistics.mean(r['target']-r['current_quantity'] for r in tr);control=json.loads((B/'task126/intercept_control.json').read_bytes())
assert shift==control['intercept_from_training_only'];assert statistics.mean((shift+r['current_quantity']-r['target'])**2 for r in te)==control['heldout_MSE']
print(json.dumps(dict(reward_choices_verified=18,leave_one_opening_out_verified=18,intercept_control_verified=True,new_games=0,old_outputs_changed=False)))