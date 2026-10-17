"""Independent arithmetic/fullhistory audit for TRAIN-only candidate-clock pilot."""
from pathlib import Path
from collections import Counter
from math import tanh,isclose
import json,random,hashlib
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2529.training_audit import terminal
from results.dev_aux.task2529.incremental_replay import advance
D=Path('results/dev_aux/task2538')
def near(x,y):return isclose(x,y,rel_tol=1e-10,abs_tol=1e-12)
def run():
 p=json.loads((D/'plan.json').read_text());done=json.loads((D/'result.json').read_text());assert json.loads((D/'started.json').read_text())['plan_sha']==hashlib.sha256((D/'plan.json').read_bytes()).hexdigest()
 for n,h in json.loads((D/'pins.json').read_text())['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 cc={gs:compile_ruleset(ruleset_from_dict(json.loads(Path(f'results/dev_aux/task2525/rules-{gs}.json').read_text())))for gs in p['generator_seeds']};qs={};counts=Counter();rows=[json.loads(x)for x in(D/'games.jsonl').read_text().splitlines()];index={}
 for line in(D/'queries.jsonl').open():
  q=json.loads(line);qs.setdefault((q['rule'],q['color'],q['treatment']),[]).append(q)
 for e in rows:
  key=e['rule'],e['color'],e['treatment'];assert key not in index;index[key]=e;rr=qs.get(key,[]);assert len(rr)==e['queries'];w=e['initial_weights'];rng=random.Random(p['initial_seed']);base=[1.]+[rng.uniform(.5,1.5)for _ in range(5)];expected=list(base)
  if e['treatment']=='proposal':expected[p['proposal_coordinate']]+=p['proposal_delta']
  assert w==expected;s=GameSession.replay(cc[e['rule']],deserialize_game_record(json.dumps(e['initial_record'])));counts['prefix_plies']+=len(s.to_record().actions);previous=e['initial_record'];preds=[];grads=[];used=0
  for i,q in enumerate(rr):
   assert q['ply']==i and q['record_before']==previous and terminal(s)is None and q['actor']==s.state.position.side_to_move;current=w if q['actor']==e['color']else p['foe'];assert q['weights']==current and q['nodes']<=q['effective_nodes']<=p['nodes_per_query']and q['effective_seconds']<=p['seconds_per_query'];used+=q['nodes'];counts['queries']+=1
   expected_observe=e['treatment']=='baseline'and q['actor']==e['color']and q['complete'];assert q['observed_by_TD']==expected_observe
   if expected_observe:
    value=tanh(q['value']/10);g=[0.]*6 if q['pv_terminal']else[x*(1-value*value)/10 for x in q['pv_phi']];preds.append(value);grads.append(g);counts['candidate_TD_observations']+=1
    if q['pv_terminal']:assert q['value']in(-1e6,0,1e6)
    else:assert q['value']==sum(x*y for x,y in zip(w,q['pv_phi']))
   elif e['treatment']=='baseline':counts['foe_queries_NOT_observed']+=1
   s=advance(s,q['record_after'],q['complete']);counts['training_plies']+=q['complete'];previous=q['record_after']
  actual=terminal(s);public=GameSession.replay(cc[e['rule']],deserialize_game_record(json.dumps(e['record'])));assert public.state==s.state and public.result==s.result and public.to_record()==s.to_record();assert e['record']==previous and actual==e['outcome']and e['nodes']==used and e['reward']==(None if actual is None else actual*(1 if e['color']==0 else-1));assert(actual is not None)==(e['ending']=='ACTUAL_TERMINAL')
  if e['treatment']=='baseline':
   errors=[preds[i+1]-preds[i]for i in range(len(preds)-1)]
   if preds and actual is not None:errors.append(actual-preds[-1])
   future=0.;delta=[0.]*6
   for i in reversed(range(len(preds))):
    future=(errors[i]if i<len(errors)else 0)+p['lam']*future;delta=[x+future*y for x,y in zip(delta,grads[i])]
   assert all(near(x,y+p['eta']*z)for x,y,z in zip(e['after_TD_weights'],w,delta));assert e['stats']['samples']==len(errors)and e['stats']['observed_searches']==len(preds)and e['stats']['censored']==(actual is None);assert near(e['stats']['loss'],sum(x*x/2 for x in errors)/max(1,len(errors)))
  else:assert e['after_TD_weights']==w and e['stats']is None
  if e['color']==1 and e['treatment']=='baseline'and actual is not None and rr and rr[-1]['actor']==0 and preds:
   counts['black_candidate_white_foe_terminal_with_prior_observation']+=1;assert e['reward']==-actual and rr[-1]['observed_by_TD']is False
  counts['games']+=1;counts['actual_terminal']+=actual is not None;counts['unknown']+=actual is None;counts['nodes']+=used
 for result in done['paired']:
  lo=hi=0
  for color in(0,1):
   aa=index.get((result['rule'],color,'baseline'));bb=index.get((result['rule'],color,'proposal'))
   if aa and bb:assert aa['initial_record']==bb['initial_record']
   a=(-1,1)if aa is None or aa['reward']is None else(aa['reward'],aa['reward']);b=(-1,1)if bb is None or bb['reward']is None else(bb['reward'],bb['reward']);lo+=b[0]-a[1];hi+=b[1]-a[0]
  assert result['bounds']==[lo/2,hi/2]and result['strict_accept_would_be']==(lo>0)and result['applied']is False
 assert counts['games']==done['actual']and counts['nodes']==done['nodes']and counts['queries']==done['queries']and counts['candidate_TD_observations']==done['candidate_TD_observations']
 out=dict(status='PASS_CANDIDATE_DECISION_TD_AND_PAID_WDL_INTERFACE',counts=dict(counts),planned=16,missing=16-len(rows),scope='Actualfulltypedrecords/whiteorientedterminal/candidateONLYTDreversecredits/foeexcluded/pairedUboundarithmetic. BlackcandidatewhitefoefinishercoverageCOUNTEDnotassumed; TDwhitez/WDL-z checked. Pilotsharedbaseline diagnosticnotfreecomputecomparison/newfitness/fulllearningadvantage. No selectedweightsdeployed.')
 (D/'audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
