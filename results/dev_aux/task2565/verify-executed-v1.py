"""Paid deployment replay and registered first+last unpruned root/PV witnesses."""
from pathlib import Path
from math import inf
from collections import Counter
import json,time,sys,hashlib
from results.dev_aux.task2565.train import compiled,restore,environment,prefix,CHANNELS
from results.dev_aux.task2565.audit import advance_env,outcome,vector
from results.dev_aux.task2529.training_audit import feat
from results.dev_aux.task2392.reader import SharedDeleteStopReader

class Limit(Exception):pass
def unpruned(directory):
 d=Path(directory);p=json.loads((d/'plan.json').read_text());ap=json.loads((d.parent/'audit-plan.json').read_text());qs=json.loads((d/'witness-queries.json').read_text());stop=SharedDeleteStopReader(Path.cwd());stop();began=time.perf_counter();nodes=0;rows=[];ccs={row['key'][0]:compiled(row['key'][0])for row in qs};status='COMPLETE'
 def poll():
  nonlocal nodes
  if nodes>=ap['unpruned_node_cap']or time.perf_counter()-began>=ap['unpruned_seconds_cap']:raise Limit()
  if nodes%128==0:stop()
  nodes+=1
 for row in qs:
  q=row['query'];gs=q['generator_seed'];e=restore(gs,ccs[gs],q['record_before']);before=e.record();w=q['weights'];startnodes=nodes
  def features():return e.features()if gs==0 else tuple(feat(e.session,CHANNELS))
  def solve(depth):
   poll();z=outcome(e,gs)
   if z is not None:return z*1000000.,{(None,True)}
   phi=features()
   if depth==0:return sum(x*y for x,y in zip(w,phi)),{(tuple(phi),False)}
   own=e.player()==0;best=None;pv=set()
   for a in e.actions():
    e.push(a)
    try:v,ws=solve(depth-1)
    finally:e.pop()
    if best is None or(v>best if own else v<best):best=v;pv=set(ws)
    elif v==best:pv.update(ws)
   assert best is not None;return best,pv
  try:
   poll();vals=[];chosen=[];own=e.player()==0
   for a in e.actions():
    e.push(a)
    try:
     ischosen=e.record()==q['record_after'];v,ws=solve(p['depth']-1);vals.append(v)
     if ischosen:chosen.append((v,ws))
    finally:e.pop()
   exact=(max if own else min)(vals);assert exact==q['value']and len(chosen)==1 and chosen[0][0]==exact;assert(None if q['pv_phi']is None else tuple(q['pv_phi']),q['pv_terminal'])in chosen[0][1];assert e.record()==before
   rows.append(dict(key=row['key'],which=row['which'],gameid=q['gameid'],ply=q['ply'],value=exact,nodes=nodes-startnodes,root_actions=len(vals),optimal_actions=sum(v==exact for v in vals),selected_optimal=True,pv_valid=True))
  except Limit:status='PARTIAL_FROZEN_AUDIT_CAP';break
 r=dict(status=status,expected=len(qs),verified=len(rows),nodes=nodes,seconds=time.perf_counter()-began,rows=rows,scope='Prospective first AND last complete OBSERVED query per arm, not independent states/allqueries/external rules. Node/wall budget includes all work.');(d/'unpruned.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items()if k!='rows'}))

def deployment(directory):
 d=Path(directory);p=json.loads((d/'eval-plan.json').read_text());t=json.loads((d/'result.json').read_text());arms={(a['generator_seed'],a['seed'],a['method']):a for a in t['arms']};b=json.loads((d/'eval-binding.json').read_text());assert b['training_sha']==hashlib.sha256((d/'result.json').read_bytes()).hexdigest()and b['plan_sha']==hashlib.sha256((d/'eval-plan.json').read_bytes()).hexdigest();stop=SharedDeleteStopReader(Path.cwd());stop();began=time.perf_counter();counts=Counter();ccs={gs:compiled(gs)for gs in p['rules']};stream=(json.loads(l)for l in(d/'eval-queries.jsonl').open());q=next(stream,None);seen=set()
 for line in(d/'eval-games.jsonl').open():
  stop();g=json.loads(line);slot=g['slot'];assert slot in p['slots']and tuple(slot)not in seen;seen.add(tuple(slot));gs,seed,family,color,treatment,foename=slot;a=arms[gs,seed,'Fixed'if treatment=='initial'else treatment];w=a['initial']if treatment=='initial'else a['weights'];assert w==g['weights'];fresh=environment(gs,ccs[gs]);prefix(fresh,gs,family,p['prefix_plies']);assert fresh.record()==g['initial_record'];e=restore(gs,ccs[gs],g['initial_record']);nq=0;nodes=0
  while q is not None and q['slot']==slot:
   assert q['record_before']==e.record()and q['actor']==e.player()and outcome(e,gs)is None and q['ply']==nq;assert q['weights']==(w if q['actor']==color else p['foes'][foename]);assert q['ordering_seed']==gs*100000000+family*1000+nq+p['ordering_seed_offset'];assert 0<q['nodes']<=p['nodes_per_query']
   advance_env(e,gs,q['record_after'],q['complete']);nq+=1;nodes+=q['nodes'];counts['failed_queries']+=not q['complete'];q=next(stream,None)
  z=outcome(e,gs);assert z==g['outcome']and e.record()==g['record']and nq==g['queries']and nodes==g['nodes'];assert g['reward']==(None if z is None else z*(1 if color==0 else-1));assert(z is not None)==(g['ending']=='ACTUAL_TERMINAL');counts.update(dict(games=1,queries=nq,nodes=nodes,actual_terminal=z is not None,unknown=z is None))
 assert q is None;r=json.loads((d/'eval-result.json').read_text());assert counts['nodes']==r['nodes']and counts['games']==r['actual'];assert r['missing_slots']==[s for s in p['slots']if tuple(s)not in seen];result=dict(status='PASS',counts=dict(counts),seconds=time.perf_counter()-began,scope='ALL actual deployment model/foe/role/recipe/typed records/fullhistory terminals/costs; no rerun of every search/external engine.');(d/'deployment-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':globals()[sys.argv[1]](sys.argv[2])
