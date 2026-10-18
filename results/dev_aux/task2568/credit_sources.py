"""Algebraic credit source decomposition on saved fixed-policy trajectories."""
from pathlib import Path
from math import tanh,isclose
from collections import defaultdict,Counter
import json,sys

def run(directory):
 d=Path(directory);p=json.loads((d/'plan.json').read_text());qs=(json.loads(l)for l in(d/'queries.jsonl').open());q=next(qs,None);by={};rates={};count=Counter()
 for g in map(json.loads,(d/'games.jsonl').open()):
  key=(g['seed'],g['method']);entry=by.setdefault(str(key),dict(episodes=0,terminal_episodes=0,unknown_episodes=0,bootstrap_terms=0,terminal_terms=0,zero_terminal_gradient_credit=0,bootstrap_scaled_net=[0.]*5,terminal_scaled_net=[0.]*5,bootstrap_scaled_abs=[0.]*5,terminal_scaled_abs=[0.]*5,weights_delta=[0.]*5));preds=[];grads=[];terminal_flags=[]
  while q is not None and q['gameid']==g['gameid']:
   if q['observed']:
    v=tanh(q['value']/10.);phi=q['pv_phi'];grad=[0.]*5 if q['pv_terminal']else[x*(1-v*v)/10. for x in phi];grad[0]=0.;preds.append(v);grads.append(grad);terminal_flags.append(q['pv_terminal'])
   q=next(qs,None)
  if g['method']=='WDL':continue
  oldrates=g['stats']['rates_before']if g['method']=='TC'else[1.]*5;elig=[0.]*5;boot=[0.]*5;terminal=[0.]*5;categories={name:[0.]*5 for name in ['material_search','terminal_PV_search','actual_endpoint']};catcounts=Counter()
  errors=[b-a for a,b in zip(preds,preds[1:])]
  if preds and g['outcome']is not None:errors.append(g['outcome']-preds[-1])
  for i,(err,grad)in enumerate(zip(errors,grads)):
   elig=[p['lambda']*a+b for a,b in zip(elig,grad)];is_terminal=(g['outcome']is not None and i==len(preds)-1);dest=terminal if is_terminal else boot;category='actual_endpoint'if is_terminal else'terminal_PV_search'if terminal_flags[i+1]else'material_search';catcounts[category]+=1
   for j in range(5):dest[j]+=err*elig[j];categories[category][j]+=err*elig[j]
   if category=='terminal_PV_search':
    catcounts['terminal_PV_target_winloss'if abs(preds[i+1])==1 else'terminal_PV_target_zero']+=1
    if g['outcome']is None:catcounts['terminal_PV_eventual_UNKNOWN']+=1
    else:catcounts['terminal_PV_eventual_match'if preds[i+1]==g['outcome']else'terminal_PV_eventual_mismatch']+=1
   entry['terminal_terms'if is_terminal else'bootstrap_terms']+=1
  scaled_boot=[p['eta']*r*x for r,x in zip(oldrates,boot)];scaled_term=[p['eta']*r*x for r,x in zip(oldrates,terminal)];delta=[b-a for a,b in zip(g['initial_weights'],g['weights'])];assert all(isclose(a+b,c,rel_tol=1e-8,abs_tol=1e-10)for a,b,c in zip(scaled_boot,scaled_term,delta))
  if g['outcome']is not None:entry['zero_terminal_gradient_credit']+=all(x==0 for x in terminal)
  for field,vec in [('bootstrap_scaled_net',scaled_boot),('terminal_scaled_net',scaled_term),('bootstrap_scaled_abs',list(map(abs,scaled_boot))),('terminal_scaled_abs',list(map(abs,scaled_term))),('weights_delta',delta)]:entry[field]=[a+b for a,b in zip(entry[field],vec)]
  category_net=entry.setdefault('target_source_scaled_net',{n:[0.]*5 for n in categories});category_abs=entry.setdefault('target_source_scaled_abs',{n:[0.]*5 for n in categories});totals=entry.setdefault('target_source_counts',{})
  for name,raw in categories.items():
   scaled=[p['eta']*r*x for r,x in zip(oldrates,raw)];category_net[name]=[a+b for a,b in zip(category_net[name],scaled)];category_abs[name]=[a+abs(b)for a,b in zip(category_abs[name],scaled)]
  assert all(isclose(sum(categories[n][j]*p['eta']*oldrates[j]for n in categories),delta[j],rel_tol=1e-8,abs_tol=1e-10)for j in range(5))
  for name,value in catcounts.items():totals[name]=totals.get(name,0)+value
  entry['episodes']+=1;entry['terminal_episodes']+=g['outcome']is not None;entry['unknown_episodes']+=g['outcome']is None
 assert q is None
 result=dict(status='PASS_FROZEN_TRAJECTORY_ALGEBRA',by_arm={k:v for k,v in by.items()if "'WDL'"not in k},scope='AllTD/TCactualdelta equals scaledbootstrap+actualterminalcredit onSAVEDtrajectories. Absolutecomponents summedperEPISODE, not pertemporalimpulse; cancellations within episodesalreadyoccur. TerminalPV meansselectedsearchleaf endedunderactualrules; zero-valueterminalPV isNOTall-defenseDRAWproof. Searchterminaltargets maycarryvictorycredit BEFOREactualend, soactualendpoint0doesNOTmeanunanchoredlearning. Thisis NOT removed-terminal counterfactualpolicytraining orstrengthcausalattribution, norprobabilitycalibration.')
 (d/'credit-sources.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:dict(episodes=v['episodes'],terminal_terms=v['terminal_terms'],bootstrap_terms=v['bootstrap_terms'],bootstrap_abs=sum(v['bootstrap_scaled_abs']),terminal_abs=sum(v['terminal_scaled_abs']))for k,v in result['by_arm'].items()}))
if __name__=='__main__':run(sys.argv[1])
