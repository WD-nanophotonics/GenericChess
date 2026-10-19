"""Independent all-history, actor-model, reverse-TD-credit and paid-work audit for task2583.

Derived from task2580/audit.py (TD branch). SelfCandidate opponents must carry the
episode-frozen candidate weights; Fixednu opponents the declared fixed foe.
"""
from pathlib import Path
import json,hashlib,random,time,sys
from math import tanh,isclose
from collections import Counter
from results.dev_aux.task2565.train import restore,prefix
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2565.audit import advance_env,vector
from results.dev_aux.task2392.reader import SharedDeleteStopReader

def run(directory,stop_root=None):
 d=Path(directory);p=json.loads((d/'plan.json').read_text());done=json.loads((d/'result.json').read_text());assert json.loads((d/'started.json').read_text())['plan_sha']==hashlib.sha256((d/'plan.json').read_bytes()).hexdigest()
 for name,h in p['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,name
 stop=SharedDeleteStopReader(Path.cwd()if stop_root is None else Path(stop_root));stop();began=time.perf_counter();counts=Counter();weights={};paid=Counter();witness={};signals=[];qs=(json.loads(l)for l in(d/'queries.jsonl').open());q=next(qs,None);armgames=Counter()
 for line in(d/'games.jsonl').open():
  stop();g=json.loads(line);key=g['seed'],g['method'];seed,method=key;assert method in('Fixednu','SelfCandidate')
  if key not in weights:
   rng=random.Random(seed);weights[key]=[1.]+[rng.uniform(.5,1.5)for _ in range(4)]
  w=weights[key];assert g['initial_weights']==w and g['index']==armgames[key];armgames[key]+=1
  family=p['training_family_offset']+g['index']//2;assert g['color']==g['index']%2;played=w
  assert family==g['family'];vector(played,g['played_weights']);reset_plies=p['mixed_prefix_cycle'][g['index']%len(p['mixed_prefix_cycle'])];assert g['prefix_plies']==reset_plies;fresh=ChessEnv();prefix(fresh,0,family,reset_plies);assert fresh.record()==g['initial_record'];e=restore(0,None,g['initial_record']);preds=[];grads=[];nq=0;nodes=0;obs=0
  assert g['foe_name']==p['foe_cycle'][g['index']%len(p['foe_cycle'])]
  while q is not None and q['gameid']==g['gameid']:
   assert q['prefix_plies']==reset_plies and q['foe_name']==g['foe_name']
   assert q['seed']==seed and q['method']==method and q['record_before']==e.record()and q['ply']==nq and q['actor']==e.player()and e.terminal()is None
   self_actor=q['actor']==g['color']or method=='SelfCandidate';assert q['self_actor']==self_actor
   expected_w=played if self_actor else p['foes'][g['foe_name']];vector(q['weights'],expected_w)
   assert q['effective_nodes']==min(p['nodes_per_query'],p['nodes_per_arm']-paid[key],p['nodes_per_game']-nodes);assert 0<q['nodes']<=q['effective_nodes']and 0<q['effective_seconds']<=p['seconds_per_query'];paid[key]+=q['nodes'];nodes+=q['nodes'];assert paid[key]==q['total_nodes'];assert q['ordering_seed']==family*1000+nq+p['ordering_seed_offset']
   st=q['search_stats'];assert st['q_limit']==2 and st['qnodes']==st['q_truncated_leaf_labels']==st['q_cap_still_tactical']==0
   counts['check_evasion_nodes']+=st['check_evasion_nodes'];counts['self_actor_queries']+=self_actor;counts['opponent_self_queries']+=self_actor and q['actor']!=g['color']
   admitted=q['actor']==g['color']and q['complete'];assert q['observed']==admitted
   if q['complete']:
    if q['pv_terminal']:assert q['pv_phi']is None and q['value']in(-1000000.,0.,1000000.)
    else:assert isclose(q['value'],sum(a*b for a,b in zip(expected_w,q['pv_phi'])),rel_tol=1e-12,abs_tol=1e-12)
    if q['actor']==g['color']:
     projected=dict(q,generator_seed=0);entry=witness.setdefault(key,dict(first=projected,last=projected));entry['last']=projected
   else:assert q['value']is None and q['pv_phi']is None;counts['failed_queries']+=1;counts['failed_nodes']+=q['nodes']
   if admitted:
    value=tanh(q['value']/10.);preds.append(value);phi=q['pv_phi'];grad=[0.]*5 if q['pv_terminal']else[x*(1-tanh(sum(a*b for a,b in zip(w,phi))/10.)**2)/10. for x in phi];grad[0]=0.;grads.append(grad);obs+=1
   advance_env(e,0,q['record_after'],q['complete']);nq+=1;q=next(qs,None)
  z=e.terminal();assert z==g['outcome']and e.record()==g['record']and nq==g['queries']and nodes==g['nodes']and obs==g['observed'];assert(z is not None)==(g['ending']=='ACTUAL_TERMINAL');assert nodes<=p['nodes_per_game'];assert len(g['record']['moves'])-len(g['initial_record']['moves'])<=p['H']
  errors=[b-a for a,b in zip(preds,preds[1:])]
  if preds and z is not None:errors.append(z-preds[-1])
  credit=[0.]*5;back=0.
  for i in range(len(errors)-1,-1,-1):
   back=errors[i]+p['lambda']*back
   for j in range(5):credit[j]+=back*grads[i][j]
  expected=[a+p['eta']*b for a,b in zip(w,credit)];assert g['stats']['samples']==len(errors)and g['stats']['observed_searches']==obs and g['stats']['censored']==(z is None);assert isclose(g['stats']['loss'],sum(x*x/2 for x in errors)/max(1,len(errors)),rel_tol=1e-10,abs_tol=1e-11)
  vector(expected,g['weights']);weights[key]=g['weights']
  counts['candidate'+str(g['color'])+'_'+method]+=1;counts.update(dict(games=1,queries=nq,nodes=nodes,actual_terminal=z is not None,unknown=z is None,observed=obs,terms=len(errors),episode_updates=w!=g['weights']));signals.append(dict(key=key,index=g['index'],nodes=paid[key],weights=weights[key],outcome=z,loss=g['stats']['loss'],terms=len(errors),credit=credit,prefix_plies=reset_plies))
 assert q is None
 for a in done['arms']:
  key=a['seed'],a['method'];vector(a['weights'],weights[key]);assert a['nodes']==paid[key]and a['games']==armgames[key]
  for sn in a['snapshots']:
   rows=[s for s in signals if s['key']==key and s['nodes']<=sn['boundary']];assert rows;last=rows[-1];assert sn['nodes']==last['nodes']and sn['index']==last['index']+1;vector(sn['weights'],last['weights'])
  assert sorted(sn['boundary']for sn in a['snapshots'])==sorted(p['snapshot_nodes'])
 assert counts['nodes']==done['nodes'];r=dict(status='PASS',counts=dict(counts),seconds=time.perf_counter()-began,scope='ALL typedChess legalhistory, episode-frozen actor weights (SelfCandidate both actors, Fixednu fixed foe), candidate-only observation, independent reverseTD sum, snapshot=last closed episode<=boundary, all paid work incl failed/opponent. Same source rules, not independent search execution.')
 (d/'audit.json').write_text(json.dumps(r,indent=2));(d/'signals.json').write_text(json.dumps(signals));(d/'witness-queries.json').write_text(json.dumps([dict(key=[0,*key],which=which,query=query)for key,entry in witness.items()for which,query in entry.items()]));print(json.dumps(r))
if __name__=='__main__':run(sys.argv[1])
