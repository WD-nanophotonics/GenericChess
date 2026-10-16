"""ALL closed first-difference contexts: ordinary material ties, not game causality."""
from pathlib import Path
from copy import copy
import json,time,hashlib,math
from collections import Counter
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,execute
from results.dev_aux.task2238.normal import SeededMaterialSearch
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path("results/dev_aux/task2294")
def run():
 start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());folder=Path("results/dev_aux/task2287");p=json.loads((folder/"plan.json").read_text());roots={r["family"]:r for r in json.loads((folder/"inputs.json").read_text())["roots"]};games=[json.loads(x)for x in(folder/"games.jsonl").read_text().splitlines()];idx={(g["context"],g["family"],g["opponent_ratio"],g["candidate_color"],g["ratio"]):g for g in games};pairs=[];contexts={}
 def cancel():stop();return time.perf_counter()-start>=300
 for seed in p["seeds"]:
  for family,root in roots.items():
   for foe in p["opponent_prices"]:
    for role in p["candidate_colors"]:
     for a,b in[(1.5,2.),(2.,3.),(1.5,3.)]:
      if cancel():raise TimeoutError("closedcontextfreeze_cap")
      left=idx.get((seed,family,foe,role,a));right=idx.get((seed,family,foe,role,b));row=dict(seed=seed,family=family,foe=foe,role=role,prices=[a,b],status="UNKNOWN_MISSING_OR_UNFINISHED")
      if left is not None and right is not None and left["reward"]is not None and right["reward"]is not None:
       row.update(status="IDENTICAL_RECORDS",actual_reward_delta=right["reward"]-left["reward"]);la=deserialize_game_record(json.dumps(left["record"])).actions;ra=deserialize_game_record(json.dumps(right["record"])).actions;c=compile_ruleset_for_execution(deserialize_ruleset(Path(root["rules"]).read_text()));s=GameSession(c);n=0
       while n<min(len(la),len(ra))and la[n]==ra[n]:s.submit(la[n]);n+=1
       if n<len(la)or n<len(ra):
        assert n<len(la)and n<len(ra)and s.result.status is SessionStatus.ONGOING;assert s.state.position.side_to_move==role;assert sum(pc is not None for pc in s.state.position.board)>4
        record=json.loads(serialize_game_record(s.to_record()));key=hashlib.sha256(json.dumps(dict(seed=seed,record=record),sort_keys=True).encode()).hexdigest();contexts.setdefault(key,dict(key=key,rules=root["rules"],root_record=record,seed=seed,side=role));row.update(status="FIRST_MATERIAL_ACTION_DIFFERENCE",common_plies=n,context_key=key,choices=[choice_value(SessionChoice("ACTION",action=x))for x in(la[n],ra[n])])
       else:assert left["reward"]==right["reward"]
      pairs.append(row)
 (OUT/"frozen-pairs.json").write_bytes(json.dumps(pairs,indent=2).encode());(OUT/"frozen-contexts.json").write_bytes(json.dumps(list(contexts.values()),indent=2).encode());queries=[];counterfactuals=[];qualified={}
 def evaluate(pos,target,ratio):return float(sum((1 if pc.owner==target else-1)*(ratio if pc.current_type_id=="R"else 1.)for pc in pos.board if pc is not None and pc.current_type_id!="K"))
 for key,root in contexts.items():
  if cancel():break
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(root["rules"]).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root["root_record"])));target=s.state.position.side_to_move;rr={}
  for ratio in(1.5,1.75,2.,2.5,3.):
   d=SeededMaterialSearch(c,lambda pos,t:evaluate(pos,t,ratio),max_depth=3,priority_seed=root["seed"]).choose(s,max_nodes=8192,seconds=1.,cancel=cancel);q=dict(context=key,ratio=ratio,choice=choice_value(d.choice),score=str(d.score),nodes=d.nodes,completed_depth=d.completed_depth,exit_cause=d.exit_cause,seconds=d.seconds);queries.append(q);rr[ratio]=(d,q)
  for a,b in[(1.5,1.75),(2.5,3.)]:
   if all(rr[x][0].completed_depth==3 for x in(a,b)):assert all(rr[a][1][k]==rr[b][1][k]for k in("choice","nodes","completed_depth","exit_cause"))
  for pair in[p for p in pairs if p.get("context_key")==key]:
   a,b=pair["prices"]
   if all(rr[x][0].completed_depth==3 for x in(a,b)):
    assert pair["choices"]==[rr[x][1]["choice"]for x in(a,b)]
    values={}
    for price in(a,b):
     for owner in(a,b):
      child=copy(s);execute(child,rr[owner][0].choice)
      if child.result.status is not SessionStatus.ONGOING:value=0. if child.result.winner is None else math.inf if child.result.winner==target else-math.inf;depth=2
      else:
       d=SeededMaterialSearch(c,lambda pos,t:evaluate(pos,t,price),max_depth=2,priority_seed=root["seed"]).choose(child,max_nodes=8192,seconds=1.,cancel=cancel);value=None if d.score is None else-d.score;depth=d.completed_depth
      values[str((price,owner))]=dict(score=str(value),depth=depth)
    ties={str(price):None if any(values[str((price,owner))]["depth"]!=2 for owner in(a,b))else values[str((price,a))]["score"]==values[str((price,b))]["score"]for price in(a,b)}
    counterfactuals.append(dict(context=key,prices=[a,b],values=values,ties=ties,actual_reward_delta=pair["actual_reward_delta"],scope="Bothselectedactions evaluatedwithfullwindowD2childunderbothprices; tieatfirstlocaldecision NOTentiregamecausalmediation."))
 for n,v in[("queries.json",queries),("counterfactuals.json",counterfactuals)]: (OUT/n).write_bytes(json.dumps(v,indent=2).encode())
 result=dict(status="COMPLETE_CLOSED_FIRST_MATERIAL_DIFFERENCE_QUALIFICATION"if len(queries)==5*len(contexts)else"PARTIAL_QUALIFICATION_CAP",paired_slots=len(pairs),pair_statuses=dict(Counter(r["status"]for r in pairs)),unique_actual_material_contexts=len(contexts),new_ordinary_queries=len(queries),complete_D3=sum(r["completed_depth"]==3 for r in queries),local_counterfactual_pairs=len(counterfactuals),by_prices={str([a,b]):dict(pairs=sum(r["prices"]==[a,b]for r in counterfactuals),ties_at_low=sum(r["prices"]==[a,b]and r["ties"][str(a)]is True for r in counterfactuals),ties_at_high=sum(r["prices"]==[a,b]and r["ties"][str(b)]is True for r in counterfactuals))for a,b in[(1.5,2.),(2.,3.),(1.5,3.)]},seconds=time.perf_counter()-start,scope="ALL32TRAIN/twoseeds/foes/roles/3contrasts; 768plannedpairslots, missingUNKNOWN retained. FreezeALLfirstfullhistorymaterialdifferences beforequeries; sourceguidecannotexplainfirstwithinseedpriceactiondifference. Exactordinarysource/fullD3/finitecomparisononly assumptions, no canonicalWDL lookup, no newrewardgame/fit/DEV. Crossseedguidepriorityalsochanges; no entireW-Ltiecausality oruniversalpriceclaim.")
 (OUT/"result.json").write_bytes(json.dumps(result,indent=2).encode());print(json.dumps(result))
if __name__=="__main__":run()
