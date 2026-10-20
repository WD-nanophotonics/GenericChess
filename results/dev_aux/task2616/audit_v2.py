"""Independent replay audit v2 for task2616. The frozen v1 auditor expected an unlogged weights_after field; v2 replays updates and validates the next recorded weights plus final game snapshots."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib, json, random
from results.dev_aux.task2492.learning import Model, TreeStrap, Sample, Receipt
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2565.train import prefix, restore
D=Path(__file__).resolve().parent
ROOT=Path.cwd()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def decode(x): return float('-inf') if x=='-inf' else float('inf') if x=='+inf' else x
def registration():
 p=json.loads((D/'plan.json').read_text()); ep=json.loads((D/'eval-plan.json').read_text()); r=json.loads((D/'registration.json').read_text()); rr=json.loads((D/'runner-registration.json').read_text())
 assert sha(D/'plan.json')==r['plan_sha256'] and sha(D/'eval-plan.json')==r['eval_plan_sha256'] and sha(D/'runner-registration.json')==r['runner_registration_sha256']
 assert rr['plan_sha256']==r['plan_sha256'] and rr['eval_plan_sha256']==r['eval_plan_sha256']
 for n,h in rr['runtime_pins'].items(): assert sha(ROOT/n)==h,n
 assert len(ep['slots'])==1024 and len({tuple(x) for x in ep['slots']})==1024
 assert sha(D/'root-manifest.json')==r['root_manifest_sha256']
 return p,ep,json.loads((D/'root-manifest.json').read_text())
def training():
 p,ep,roots=registration(); start=json.loads((D/'tree-started.json').read_text()); result=json.loads((D/'tree-training-result.json').read_text()); spec=p['conditions']['training']
 assert start['plan_sha256']==sha(D/'plan.json') and start['eval_plan_sha256']==sha(D/'eval-plan.json')
 assert start['runner_registration_sha256']==sha(D/'runner-registration.json')
 assert start['session_id']==json.loads((ROOT/'.local_agent/session.json').read_text())['id']
 models={}; initial_weights={}
 for seed in p['conditions']['seeds']:
  rng=random.Random(seed); models[seed]=Model([1.0]+[rng.uniform(.5,1.5) for _ in range(4)]); initial_weights[seed]=list(models[seed].weights)
 foe=Model(spec['fixed_foe']); learner=TreeStrap(eta=.05); bygame=defaultdict(list); totals=Counter(); last={s:0 for s in models}
 for line in (D/'tree-queries.jsonl').read_text().splitlines():
  q=json.loads(line); seed=q['seed']; assert seed in models
  assert q['family']==spec['training_family_offset']+q['game_index']//2 and q['color']==q['game_index']%2
  assert q['observed']==(q['actor']==q['color'] and q['complete'])
  assert 0<q['nodes']<=q['effective_nodes']<=spec['nodes_per_query'] and 0<q['effective_seconds']<=spec['seconds_per_query']
  assert last[seed]<=q['total_nodes']<=spec['node_budget_per_seed_both_actors']; last[seed]=q['total_nodes']
  current=models[seed] if q['actor']==q['color'] else foe; assert q['weights_used']==current.weights
  if q['observed']:
   samples=tuple(Sample(tuple(x['phi']),decode(x['lower']),decode(x['upper']),x['depth']) for x in q['samples'])
   rec=Receipt(None,q['value'],None if q['pv_phi'] is None else tuple(q['pv_phi']),q['pv_terminal'],samples,q['nodes'],True,0,q['seconds'],q['reason'])
   assert learner.update(models[seed],rec)==q['update']
  else: assert q['update'] is None and q['samples']==[]
  bygame[(seed,q['game_index'])].append(q); totals.update(queries=1,nodes=q['nodes'],samples=len(q['samples']),candidate_receipts=q['observed'])
 games=[json.loads(x) for x in (D/'tree-games.jsonl').read_text().splitlines()]
 previous={s:list(w) for s,w in initial_weights.items()}
 for g in games:
  qs=bygame[(g['seed'],g['index'])]; assert qs and qs[0]['record_before']==g['initial_record'] and qs[0]['family']==g['family']
  assert g['initial_weights']==previous[g['seed']]
  root=ChessEnv(); prefix(root,0,g['family'],spec['opening_prefix_plies']); assert root.record()==g['initial_record']
  env=restore(0,None,g['initial_record'])
  for i,q in enumerate(qs):
   assert env.record()==q['record_before'] and env.player()==q['actor']
   if q['complete']: assert q['action'] is not None; env.board.push_uci(q['action'])
   else: assert q['action'] is None
   assert env.record()==q['record_after']
   if i+1<len(qs): assert q['record_after']==qs[i+1]['record_before']
  assert env.record()==g['record'] and env.terminal()==g['outcome'] and len(qs)==g['queries']
  assert sum(q['nodes'] for q in qs)==g['nodes'] and (g['outcome'] is not None)==(g['ending']=='ACTUAL_TERMINAL')
  previous[g['seed']]=list(g['weights'])
 for arm in result['arms']:
  subset=[g for g in games if g['seed']==arm['seed']]
  assert subset and sum(g['nodes'] for g in subset)==arm['nodes']<=spec['node_budget_per_seed_both_actors']
  assert models[arm['seed']].weights==arm['weights']==subset[-1]['weights']
 assert result['nodes']==totals['nodes'] and result['seconds']<=spec['global_hard_cap_seconds']
 return {'queries':totals['queries'],'nodes':totals['nodes'],'samples':totals['samples'],'games':len(games),'arms':len(result['arms']),'candidate_complete_receipts':totals['candidate_receipts']}
def evaluation():
 p,ep,roots=registration(); start=json.loads((D/'eval-started.json').read_text()); b=json.loads((D/'eval-binding.json').read_text()); er=json.loads((D/'eval-result.json').read_text()); assembled=json.loads((D/'result.json').read_text())
 assert start==b and b['plan_sha256']==sha(D/'eval-plan.json') and b['task_plan_sha256']==sha(D/'plan.json') and b['assembled_result_sha256']==sha(D/'result.json')
 arms={(a['generator_seed'],a['seed'],a['method']):a for a in assembled['arms']}; rootmap={r['family']:r['record'] for r in roots['roots']}; qmap=defaultdict(list)
 for line in (D/'eval-queries.jsonl').read_text().splitlines():
  q=json.loads(line); slot=tuple(q['slot']); assert 0<q['nodes']<=q['effective_nodes']<=ep['nodes_per_query']; assert 0<q['effective_seconds']<=ep['seconds_per_query']; qmap[slot].append(q)
 rows=[json.loads(x) for x in (D/'eval-games.jsonl').read_text().splitlines()]; seen=set(); counts=Counter()
 for row in rows:
  slot=tuple(row['slot']); assert slot in {tuple(x) for x in ep['slots']} and slot not in seen; seen.add(slot)
  gs,seed,family,color,endpoint,foe_name=slot; method='TD' if endpoint=='initial' else endpoint; arm=arms[(gs,seed,method)]; w=arm['initial'] if endpoint=='initial' else arm['weights']; assert w==row['weights']
  qs=qmap[slot]; assert qs and len(qs)==row['queries']
  env=restore(gs,None,row['initial_record']); assert row['initial_record']==rootmap[family]
  for i,q in enumerate(qs):
   assert env.record()==q['record_before'] and env.player()==q['actor']
   assert q['weights']==(w if q['actor']==color else ep['foes'][foe_name])
   if q['complete']: assert q['action'] is not None; env.board.push_uci(q['action'])
   else: assert q['action'] is None
   assert env.record()==q['record_after']
   if i+1<len(qs): assert q['record_after']==qs[i+1]['record_before']
  assert env.record()==row['record'] and env.terminal()==row['outcome']
  assert row['reward']==(None if row['outcome'] is None else row['outcome']*(1 if color==0 else -1))
  assert sum(q['nodes'] for q in qs)==row['nodes']<=ep['node_budget_per_slot_both_actors']
  assert (row['outcome'] is not None)==(row['ending']=='ACTUAL_TERMINAL')
  counts.update(slots=1,nodes=row['nodes'],queries=row['queries'],unknown=row['reward'] is None)
 expected={tuple(x) for x in ep['slots']}; missing=expected-seen
 assert seen.issubset(expected) and missing=={tuple(x) for x in er['missing_slots']}
 assert counts['slots']==er['actual'] and counts['nodes']==er['nodes'] and er['seconds']<=ep['cap_seconds']
 return {'slots':counts['slots'],'nodes':counts['nodes'],'queries':counts['queries'],'unknown':counts['unknown'],'missing':len(missing)}
def main():
 out={'status':'PASS','training_replay':training(),'evaluation_replay':evaluation(),'scope':'Recomputed complete candidate-only TreeStrap updates and replayed all emitted UCI/full-history transitions; checked registered roots, actual terminal rewards, slots and paid caps.'}
 (D/'audit.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps(out,indent=2))
if __name__=='__main__': main()
