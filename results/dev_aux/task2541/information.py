"""Observed usable-feedback and policy-sensitivity counts per paid node budget."""
from pathlib import Path
from collections import Counter,defaultdict
from dataclasses import replace
from math import tanh
import json,time
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
D=Path('results/dev_aux/task2539');O=Path('results/dev_aux/task2541')
def run():
 began=time.perf_counter();p=json.loads((D/'plan.json').read_text());result=json.loads((D/'result.json').read_text());games={};groups=defaultdict(list);counts=Counter();perarm=defaultdict(Counter);cc={g:compile_ruleset(ruleset_from_dict(json.loads(Path(f'results/dev_aux/task2525/rules-{g}.json').read_text())))for g in p['generator_seeds']}
 for line in(D/'games.jsonl').open():
  r=json.loads(line);games[r['gameid']]=r;groups[r['generator_seed'],r['method'],r['seed']].append(r)
 # Use candidate-query predictions and exact replayed endpoints, not foe targets.
 def qs():
  for line in(D/'queries.jsonl').open():yield json.loads(line)
 stream=iter(qs());q=next(stream,None)
 for gid,e in games.items():
  key=e['generator_seed'],e['method'],e['seed'];c=perarm[key];preds=[];grads=[];pvterm=[]
  while q is not None and q['gameid']==gid:
   c['queries']+=1;c['nodes']+=q['nodes'];c['candidate_queries'if q['actor']==e['color']else'foe_queries']+=1
   if q['observed_by_TD']:
    v=tanh(q['value']/10);preds.append(v);pvterm.append(q['pv_terminal']);grads.append([0.]*6 if q['pv_terminal']else[x*(1-v*v)/10 for x in q['pv_phi']]);c['candidate_TD_observations']+=1
   q=next(stream,None)
  if e['method']=='TD':
   elig=[0.]*6
   for i,pred in enumerate(preds):
    target=preds[i+1]if i+1<len(preds)else e['outcome']
    if target is None:break
    error=target-pred;elig=[p['lam']*x+y for x,y in zip(elig,grads[i])];c['TD_terms']+=1;c['nonzero_TD_errors']+=error!=0;c['nonzero_eligibility_error_terms']+=error!=0 and any(elig);c['zero_gradient_PV_terms']+=not any(grads[i])
    source='actual_game_terminal'if i+1==len(preds)else'next_search_terminal_PV'if pvterm[i+1]else'next_search_material_PV';c[source+'_terms']+=1;c[source+'_nonzero_credit_terms']+=error!=0 and any(elig);c[source+'_gross_eta_credit_L1']+=p['eta']*sum(abs(error*x)for x in elig)
   c['nonzero_episode_updates']+=e['initial_weights']!=e['after_TD_weights']
 assert q is None
 for line in(D/'updates.jsonl').open():
  u=json.loads(line)
  if u['method']!='WDL':continue
  key=u['generator_seed'],u['method'],u['seed'];c=perarm[key];c['proposals']+=1;c['accepted_proposals']+=u['changed'];c['missing_proposal_games']+=u['missing'];c['zero_width_proposal_bounds']+=u['bounds'][0]==u['bounds'][1];c['zero_bound_proposals']+=u['bounds']==[0,0]
  table={(games[i]['family'],games[i]['color'],games[i]['treatment']):games[i]for i in u['gameids']}
  for f in range(p['pairs_per_proposal']):
   for color in(0,1):
    family=p['training_family_offset']+u['index']*p['pairs_per_proposal']+f;a=table.get((family,color,'current'));b=table.get((family,color,'proposal'))
    if a is None or b is None:c['missing_pairs']+=1;continue
    assert a['initial_record']==b['initial_record'];aa=deserialize_game_record(json.dumps(a['record']));bb=deserialize_game_record(json.dumps(b['record']));i=next((j for j,(x,y)in enumerate(zip(aa.actions,bb.actions))if x!=y),None)
    if i is not None:
     before=GameSession.replay(cc[key[0]],replace(aa,actions=aa.actions[:i],resigned_by=None,declaration=None));assert before.state.position.side_to_move==color;c['candidate_first_divergence']+=1
    elif aa.actions==bb.actions:c['identical_full_actions']+=1
    else:assert a['outcome']is None or b['outcome']is None;c['censor_prefix_pairs']+=1
    if a['reward']is None or b['reward']is None:c['unknown_pairs']+=1
    else:c['improved_pairs'if b['reward']>a['reward']else'worse_pairs'if b['reward']<a['reward']else'same_reward_pairs']+=1
 rows=[];by_method=defaultdict(Counter)
 for a in result['arms']:
  key=a['generator_seed'],a['method'],a['seed'];c=perarm[key];assert c['nodes']==a['nodes'];rows.append(dict(rule=key[0],method=key[1],seed=key[2],counts=dict(c)));by_method[key[1]].update(c)
 out=dict(status='PASS_ACTUAL_FEEDBACK_AND_POLICY_SENSITIVITY',rows=rows,by_method={m:dict(c)for m,c in by_method.items()},seconds=time.perf_counter()-began,scope='Counts of actual signals per paid budget, NOT comparable information bits/equal gradient strength/causal proof. WDL identicalactions andequalutility distinguished; all paid current/proposal cells includingunknown/missing retained. Trainingrewardnotheldoutstrength. TDgamma1/lam.95 candidate-decisiontime; PVterminalgradient0 canstilltransmitpreviouseligibility. Temporaltermsseparatedbyactualgameendpoint/nextsearchterminalPV/materialPV. GrossabsolutecreditssummedBEFOREcancellationarenotnetupdatefractions/causalusefulness.')
 (O/'information.json').write_text(json.dumps(out,indent=2));print(json.dumps(dict(status=out['status'],by_method=out['by_method'])))
if __name__=='__main__':run()
