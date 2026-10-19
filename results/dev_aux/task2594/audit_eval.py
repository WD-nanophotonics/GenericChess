"""Replay all registered Chess deployment traces and terminal/cost accounting."""
from pathlib import Path
from collections import Counter
import hashlib,json,time
from results.dev_aux.task2565.train import compiled,environment,prefix,restore
from results.dev_aux.task2565.audit import advance_env,outcome
T=Path(__file__).resolve().parent; R=T.parents[2]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=json.loads((T/'eval-plan.json').read_text()); tp=json.loads((T/'train'/'plan.json').read_text()); result=json.loads((T/'eval-result.json').read_text()); bound=json.loads((T/'eval-binding.json').read_text()); train=json.loads((T/'result.json').read_text())
 assert bound['training_sha']==sha(T/'result.json') and bound['plan_sha']==sha(T/'eval-plan.json')
 for name,digest in tp['pins'].items(): assert sha(R/name)==digest,name
 arms={(a['generator_seed'],a['seed'],a['method']):a for a in train['arms']}; ccs={g:compiled(g) for g in p['rules']}; counts=Counter(); seen=set(); start=time.perf_counter(); qiter=(json.loads(x) for x in (T/'eval-queries.jsonl').open(encoding='utf-8')); q=next(qiter,None)
 for line in (T/'eval-games.jsonl').open(encoding='utf-8'):
  g=json.loads(line); slot=g['slot']; assert slot in p['slots'] and tuple(slot) not in seen; seen.add(tuple(slot))
  gs,seed,family,color,treatment,foename=slot; method='TD' if treatment=='initial' else treatment; arm=arms[gs,seed,method]; w=arm['initial'] if treatment=='initial' else arm['weights']; assert w==g['weights']
  fresh=environment(gs,ccs[gs]); prefix(fresh,gs,family,p['prefix_plies']); assert fresh.record()==g['initial_record']; e=restore(gs,ccs[gs],g['initial_record']); nq=nodes=0
  while q is not None and q['slot']==slot:
   assert q['record_before']==e.record() and q['actor']==e.player() and outcome(e,gs) is None and q['ply']==nq
   expected=w if q['actor']==color else p['foes'][foename]; assert q['weights']==expected
   assert q['ordering_seed']==gs*100000000+family*1000+nq+p['ordering_seed_offset']
   assert 0<q['nodes']<=q['effective_nodes']<=p['nodes_per_query'] and 0<q['effective_seconds']<=p['seconds_per_query']
   advance_env(e,gs,q['record_after'],q['complete']); nq+=1; nodes+=q['nodes']; counts['queries']+=1; counts['failed_queries']+=not q['complete']; q=next(qiter,None)
  z=outcome(e,gs); reward=None if z is None else z*(1 if color==0 else -1)
  assert e.record()==g['record'] and z==g['outcome'] and reward==g['reward'] and nq==g['queries'] and nodes==g['nodes']
  assert (z is not None)==(g['ending']=='ACTUAL_TERMINAL')
  counts.update(games=1,nodes=nodes,actual_terminal=z is not None,unknown=z is None)
 assert q is None and len(seen)==result['actual']==result['expected'] and result['missing']==0
 assert counts['nodes']==result['nodes'] and counts['games']==len(p['slots'])
 summary={'status':'PASS_ALL_SLOT_HISTORY_ENDPOINT_ROLE_AND_COST_REPLAY','counts':dict(counts),'seconds':time.perf_counter()-start,'scope':'Full registered deployment record replay under the shared Chess rules authority; no rerun of search and no external-engine claim.'}
 (T/'deployment-audit.json').write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary))
if __name__=='__main__': main()
