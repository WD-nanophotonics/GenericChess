"""Bounded real-record cycle histories for beyond-exact-root reuse qualification."""
from pathlib import Path
from copy import copy
from dataclasses import replace
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,choices,execute
from scripts.generic_win_proof import _Budget,_ordered,_same_state
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2181.run import encode
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path("results/dev_aux/task2292")
def run():
 assert not(OUT/"started.json").exists();p=json.loads((OUT/"plan.json").read_text());start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());(OUT/"started.json").write_bytes(json.dumps(dict(cap=p["cap_seconds"])).encode());saved=json.loads(Path("results/dev_aux/task2291/certificates.json").read_text());pairs=[];scans=[];receipts=[];conversions=[]
 def cancel():stop();return time.perf_counter()-start>=p["cap_seconds"]
 for row in saved:
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(row["rules"]).read_text()));root=GameSession.replay(c,deserialize_game_record(json.dumps(row["root_record"])));cert=decode_graph(root,row["certificate"]);assert verify_graph(root,cert,max_nodes=65536,seconds=5.,cancel=cancel)["verified"];paths=[];nodes=0;rootstart=time.perf_counter();status="EXHAUSTED_DEPTH"
  def walk(s,depth):
   nonlocal nodes,status
   if cancel()or time.perf_counter()-rootstart>=p["per_root_seconds"]:status="TIME_CAP";return
   if nodes>=p["max_nodes"]:status="NODE_CAP";return
   nodes+=1
   if depth>0 and _same_state(s.state.position,root.state.position):
    assert s.to_record()!=root.to_record()and s.result.status is SessionStatus.ONGOING;paths.append(s)
    return
   if depth>=p["max_depth"]:return
   for a in _ordered(s.legal_actions()):
    if len(paths)>=p["pairs_per_root"]or status in("NODE_CAP","TIME_CAP"):return
    child=copy(s);execute(child,SessionChoice("ACTION",action=a))
    if child.result.status is SessionStatus.ONGOING:walk(child,depth+1)
  walk(root,0);scans.append(dict(context=row["context"],nodes=nodes,status=status,pairs=len(paths),seconds=time.perf_counter()-rootstart))
  # All cycle candidates chosen before any reuse admission result is observed.
  for current in paths:
   pairs.append(dict(context=row["context"],rules=row["rules"],source_record=row["root_record"],target_record=json.loads(serialize_game_record(current.to_record())),same_complete_position=True,source_ply=root.state.ply_count,target_ply=current.state.ply_count))
 (OUT/"frozen-pairs.json").write_bytes(json.dumps(pairs,indent=2).encode())
 for pair in pairs:
  stop();source=next(x for x in saved if x["context"]==pair["context"]);c=compile_ruleset_for_execution(deserialize_ruleset(Path(pair["rules"]).read_text()));root=GameSession.replay(c,deserialize_game_record(json.dumps(pair["source_record"])));current=GameSession.replay(c,deserialize_game_record(json.dumps(pair["target_record"])));cert=decode_graph(root,source["certificate"]);assert _same_state(root.state.position,current.state.position)
  old=verify_graph(current,cert,max_nodes=65536,seconds=5.,cancel=cancel);assert not old["verified"]and old["reason"]=="root_binding_mismatch"
  # Fresh untrusted candidate, NOT a reused positive receipt. No FP overwrite.
  rebound=replace(cert,root_record=current.to_record(),root_state=current.state);v=verify_graph(current,rebound,max_nodes=65536,seconds=5.,cancel=cancel);r=dict(pair=len(receipts),context=pair["context"],original_binding_rejected=old,candidate_verification=v,current_cursor=None,converted=False)
  if v["verified"]:
   cur=GraphStrategyCursor(current,rebound,max_nodes=65536,seconds=5.,cancel=cancel);r["current_cursor"]=cur.receipt;count=0
   while current.result.status is SessionStatus.ONGOING:
    if cancel():raise TimeoutError("qualification_cap")
    before=copy(current);choice=cur.choose(current)if current.state.position.side_to_move==cert.target else next(choices(current,_Budget(1000,1.,cancel)));execute(current,choice);cur.observe(before,choice,current);count+=1
   assert current.result.winner==cert.target;r.update(converted=True,moves=count);conversions.append(dict(pair=len(receipts),record=json.loads(serialize_game_record(current.to_record()))))
  receipts.append(r)
 for n,v in[("receipts.json",receipts),("conversions.json",conversions)]: (OUT/n).write_bytes(json.dumps(v,indent=2).encode())
 result=dict(status="COMPLETE_BOUNDED_REAL_HISTORY_REUSE_QUALIFICATION",source_contexts=len(saved),scans=scans,actual_cycle_pairs=len(pairs),old_binding_rejections=len(receipts),admitted=sum(r["candidate_verification"]["verified"]for r in receipts),actual_conversions=len(conversions),actual_conversion_moves=sum(r.get("moves",0)for r in receipts),seconds=time.perf_counter()-start,scope=p["scope"])
 (OUT/"result.json").write_bytes(json.dumps(result,indent=2).encode());print(json.dumps(result))
if __name__=="__main__":run()
