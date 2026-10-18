"""Prospectively selected unpruned minimax witnesses independent of TrainingSearch."""
from pathlib import Path
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2525.run import RecordedSessionEnv
from results.dev_aux.task2529.training_audit import terminal,feat
from results.dev_aux.task2392.reader import SharedDeleteStopReader
D=Path('results/dev_aux/task2552');O=Path('results/dev_aux/task2553');CHANNELS=(('board','P'),('board','A'),('board','X'),('hand','A'),('hand','P'),('hand','X'))
class Limit(Exception):pass
def run(stop_root=None):
 began=time.perf_counter();plan=json.loads((O/'audit-plan.json').read_text());p=json.loads((D/'plan.json').read_text());stop=SharedDeleteStopReader(Path.cwd()if stop_root is None else Path(stop_root));stop();selected={}
 with(D/'queries.jsonl').open()as f:
  for line in f:
   q=json.loads(line);gs,seed,family,c,t,foe,d=q['slot']
   if q['complete']and q['actor']==c:selected.setdefault((gs,seed,t,d),q)
 cc={gs:compile_ruleset(ruleset_from_dict(json.loads(Path(f'results/dev_aux/task2525/rules-{gs}.json').read_text())))for gs in p['generator_seeds']};nodes=0;rows=[];status='COMPLETE'
 def poll():
  nonlocal nodes
  if nodes>=plan['unpruned_nodes_cap']or time.perf_counter()-began>=plan['unpruned_seconds_cap']:raise Limit()
  if nodes%128==0:stop()
  nodes+=1
 for key,q in sorted(selected.items()):
  env=RecordedSessionEnv(GameSession.replay(cc[key[0]],deserialize_game_record(json.dumps(q['record_before']))),CHANNELS);before=env.record();w=q['weights'];start_nodes=nodes;rootvals=[];chosen=[]
  def solve(depth):
   poll();z=terminal(env.session)
   if z is not None:return 1e6*z,{(None,True)}
   if depth==0:
    phi=tuple(feat(env.session,CHANNELS));return sum(a*b for a,b in zip(w,phi)),{(phi,False)}
   own=env.player()==0;best=None;witness=set()
   for a in env.actions():
    env.push(a)
    try:v,pv=solve(depth-1)
    finally:env.pop()
    if best is None or(v>best if own else v<best):best=v;witness=set(pv)
    elif v==best:witness.update(pv)
   assert best is not None;return best,witness
  try:
   poll();own=env.player()==0
   for a in env.actions():
    env.push(a)
    try:
     ischosen=env.record()==q['record_after'];v,witness=solve(q['effective_depth']-1)
     if ischosen:chosen.append((v,witness))
    finally:env.pop()
    rootvals.append(v)
   exact=(max if own else min)(rootvals);assert exact==q['value']and len(chosen)==1 and chosen[0][0]==exact;assert((None if q['pv_phi']is None else tuple(q['pv_phi'])),q['pv_terminal'])in chosen[0][1];assert env.record()==before
   rows.append(dict(key=list(key),source_slot=q['slot'],source_ply=q['ply'],source_query_sha=hashlib.sha256(json.dumps(q,sort_keys=True).encode()).hexdigest(),nodes=nodes-start_nodes,value=exact,root_actions=len(rootvals),optimal_root_actions=sum(v==exact for v in rootvals),chosen_action_optimal=True,PV_witness=True,root_record_restored=True))
  except Limit:status='PARTIAL_ORIGINAL_AUDIT_CAP';assert env.record()==before;break
 result=dict(status=status,expected=plan['unpruned_keys'],available=len(selected),verified=len(rows),unverified=plan['unpruned_keys']-len(rows),nodes=nodes,seconds=time.perf_counter()-began,rows=rows,scope='Independent unpruned minimax actual Session/root/action/PV witnesses, prospective first candidatequery per rule/initial/treatment/depth. Separate audit budget and all incomplete work counted. SameCore authority, not external rules engine or everyquery/allrules proof.')
 (O/'unpruned.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='rows'}))
if __name__=='__main__':run()
