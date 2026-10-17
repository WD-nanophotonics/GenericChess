"""Independent unpruned actual Generic D2 verification, no TrainingSearch calls."""
from pathlib import Path
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2525.run import RecordedSessionEnv
from results.dev_aux.task2529.training_audit import terminal,feat
from results.dev_aux.task2392.reader import SharedDeleteStopReader
D=Path('results/dev_aux/task2541');T=Path('results/dev_aux/task2539')
class Limit(Exception):pass

def run(stop_root=None):
 began=time.perf_counter();plan=json.loads((D/'search-verification-plan.json').read_text());assert(T/'result.json').exists();p=json.loads((T/'plan.json').read_text());selected={};stop=SharedDeleteStopReader(Path.cwd()if stop_root is None else Path(stop_root));stop()
 for line in(T/'queries.jsonl').open():
  q=json.loads(line)
  if q['complete']and q['actor']==q['color']:
   for threshold in plan['thresholds']:
    key=q['generator_seed'],q['method'],q['seed'],threshold
    if key not in selected and q['total_nodes']-q['nodes']>=threshold:selected[key]=q
 compiled={gs:compile_ruleset(ruleset_from_dict(json.loads((Path('results/dev_aux/task2525')/f'rules-{gs}.json').read_text())))for gs in p['generator_seeds']if(Path('results/dev_aux/task2525')/f'rules-{gs}.json').exists()};rows=[];nodes=0;status='COMPLETE'
 def poll():
  nonlocal nodes
  if nodes>=plan['node_ceiling']or time.perf_counter()-began>=plan['cap_seconds']:raise Limit()
  if nodes%128==0:stop()
  nodes+=1
 for key,q in sorted(selected.items()):
  env=RecordedSessionEnv(GameSession.replay(compiled[key[0]],deserialize_game_record(json.dumps(q['record_before']))),(('board','P'),('board','A'),('board','X'),('hand','A'),('hand','P'),('hand','X')));before=env.record();weights=q['weights'];n0=nodes
  def solve(depth):
   poll();z=terminal(env.session)
   if z is not None:return 1000000.*z,[(None,True)]
   if depth==0:
    phi=feat(env.session,(('board','P'),('board','A'),('board','X'),('hand','A'),('hand','P'),('hand','X')));return sum(x*w for x,w in zip(phi,weights)),[(phi,False)]
   best=None;witness=[];own=env.player()==0
   for action in env.actions():
    env.push(action)
    try:v,leaves=solve(depth-1)
    finally:env.pop()
    if best is None or(v>best if own else v<best):best=v;witness=leaves
    elif v==best:witness+=leaves
   assert best is not None;return best,witness
  rootvalues=[];chosen=[]
  try:
   poll();own=env.player()==0
   for action in env.actions():
    env.push(action)
    try:
     ischosen=env.record()==q['record_after'];v,witnesses=solve(p['depth']-1)
     if ischosen:chosen.append((v,witnesses))
    finally:env.pop()
    rootvalues.append(v)
   expected=(max if own else min)(rootvalues);assert expected==q['value'];assert chosen and all(v==expected for v,_ in chosen);assert any((q['pv_phi'],q['pv_terminal'])in witnesses for _,witnesses in chosen);assert env.record()==before
   rows.append(dict(generator_seed=key[0],method=key[1],seed=key[2],threshold=key[3],game=q['gameid'],ply=q['ply'],source_total_nodes=q['total_nodes'],value=expected,root_choices=len(rootvalues),matching_committed_fullrecords=len(chosen),nodes=nodes-n0,query_record_sha=hashlib.sha256(json.dumps(q,sort_keys=True).encode()).hexdigest()))
  except Limit:status='PARTIAL_ORIGINAL_CAP';assert env.record()==before;break
 result=dict(status=status,planned=plan['expected'],available=len(selected),verified=len(rows),unverified=plan['expected']-len(rows),nodes=nodes,rows=rows,seconds=time.perf_counter()-began,scope=plan['scope']+' SelectedPV leafwitness values/features/terminalflag andchosenfulltypedchild validated; no allinteriorboundcomparison because TRAINreceiptsdoNOTstore thoseintervals. SameGameSession authority, noexternalrulesengine.');(D/'search-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='rows'}))
if __name__=='__main__':run()
