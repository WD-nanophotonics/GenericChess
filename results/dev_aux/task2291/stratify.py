"""Postfreeze positive-reference construction, never discovery/reward."""
from pathlib import Path
from copy import copy
from collections import Counter
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import choices,execute
from scripts.generic_win_proof import _Budget,_Interrupted
from results.dev_aux.task2251.study import Guide
from results.dev_aux.task2246.entry_proofs import build
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2181.run import encode
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path("results/dev_aux/task2291")
def run():
 start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());guide=Guide();inputs=json.loads(Path("results/dev_aux/task2284/inputs.json").read_text())["contexts"];strata={r["context"]:r for r in json.loads(Path("results/dev_aux/task2288/result.json").read_text())["rows"]};rows=[];certs=[];paths=[]
 def cancel():stop();return time.perf_counter()-start>=120
 for root in inputs:
  stop();r=strata[root["index"]];row=dict(context=root["index"],canonical_mover_label=r["canonical_mover_label"],status="NO_POSITIVE_REFERENCE_CANDIDATE_NOT_ACTUAL_DRAW",actual_verified=False)
  if r["canonical_mover_label"]in("WIN","LOSS"):
   c=compile_ruleset_for_execution(deserialize_ruleset(Path(root["rules"]).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root["root_record"])));target=s.state.position.side_to_move if r["canonical_mover_label"]=="WIN"else 1-s.state.position.side_to_move
   try:
    cert,work=build(s,guide,target,dict(build_nodes=32768,build_seconds=5.),cancel);v=verify_graph(s,cert,max_nodes=65536,seconds=5.,cancel=cancel);row.update(target=target,builder=work,verification=v,status="VERIFIED_ACTUAL_HISTORY_TARGET_WIN"if v["verified"]else"UNKNOWN_VERIFICATION",actual_verified=v["verified"])
    if v["verified"]:
     cur=GraphStrategyCursor(s,cert,max_nodes=65536,seconds=5.,cancel=cancel);certs.append(dict(context=root["index"],rules=root["rules"],root_record=root["root_record"],certificate=encode(cert)));count=0
     while s.result.status is SessionStatus.ONGOING:
      if cancel():raise TimeoutError("qualification_cap")
      before=copy(s);choice=cur.choose(s)if s.state.position.side_to_move==target else next(choices(s,_Budget(1000,1.,cancel)));execute(s,choice);cur.observe(before,choice,s);count+=1
     assert s.result.winner==target;row.update(current_cursor=cur.receipt,actual_conversion_moves=count);paths.append(dict(context=root["index"],record=json.loads(serialize_game_record(s.to_record()))))
   except(_Interrupted,ValueError)as error:row.update(status="UNKNOWN_BUILD_OR_CURSOR",reason=str(error))
  rows.append(row)
 for name,value in[("rows.json",rows),("certificates.json",certs),("conversions.json",paths)]: (OUT/name).write_bytes(json.dumps(value,indent=2).encode())
 result=dict(status="COMPLETE_POSTFREEZE_REFERENCE_ASSISTED_ACTUAL_HISTORY_STRATIFICATION",contexts=len(rows),actual_verified=sum(r["actual_verified"]for r in rows),verified_for_nonmover=sum(r["actual_verified"]and r["canonical_mover_label"]=="LOSS"for r in rows),actual_conversion_moves=sum(r.get("actual_conversion_moves",0)for r in rows),seconds=time.perf_counter()-start,scope="Referenceassistedpositiveconstruction kept separate from2285genericdiscovery. Completeactualhistory/rule/root/ranks/prehistory/remainingply/AND+currentcursor checks. NONE/DRAWcanonicalentries never actualDRAWlabels. Allsevencontextsretained; no pricefit/newrewardgames/rootreplacement/defaultadoption.")
 (OUT/"result.json").write_bytes(json.dumps(result,indent=2).encode());print(json.dumps(result))
if __name__=="__main__":run()
