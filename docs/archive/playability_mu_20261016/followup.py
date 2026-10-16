from pathlib import Path
import sys,json,time,os,hashlib
R=Path.cwd();P=R/".local_agent/playability-mu-20261016";sys.path[:0]=[str(R),str(P)]
import assessment as a
p=a.p
from scripts.research_record import record_value,write_record
from generic_chess.core.movegen import iter_legal_actions
from generic_chess.session.serialization import serialize_game_record
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
def canonical(x):return json.dumps(x,sort_keys=True,separators=(",",":"))
def select(curve,plan):
 selected=[]
 for board in[4,8,12,16]:
  for q in[0,1]:
   choice=None
   for case in sorted((x for x in plan["cases"]if x["board"]==board),key=lambda x:x["seed"]):
    low=next(x for x in curve["rows"]if x["seed"]==case["seed"]and x["q"]==q and x["seconds"]==.25);high=next(x for x in curve["rows"]if x["seed"]==case["seed"]and x["q"]==q and x["seconds"]==16)
    if low.get("execution_allowed")and high.get("execution_allowed")and low["result"]["action"]!=high["result"]["action"]:
     choice=dict(**case,q=q,kind="EXPOSED_SELECTED_PARENT",low_action=low["result"]["action"],high_action=high["result"]["action"],low_result=low["result"],high_result=high["result"]);break
   selected.append(choice or dict(board=board,q=q,kind="NO_SENSITIVE_EXECUTABLE_PAIR"))
 return selected
def diagnose(curve,cores):
 plan=json.loads((P/"followup-plan.json").read_bytes());cases=json.loads((P/"curve-plan.json").read_bytes())["cases"];out=[];start=time.perf_counter()
 for case in cases:
  p.stopped();d,c,s,nr=a.load(R/case["root"]);unique={}
  for row in curve["rows"]:
   if row["seed"]==case["seed"]and row.get("result")and row["result"]["action"]is not None:unique[canonical(row["result"]["action"])]=row["result"]["action"]
  for row in cores["rows"]:
   if row["seed"]==case["seed"]:
    for key in["core","native"]:
     if row[key]["action"]is not None:unique[canonical(row[key]["action"])]=row[key]["action"]
  for action in unique.values():
   p.stopped()
   if time.perf_counter()-start>=plan["diagnostic"]["whole_seconds"]:out.append(dict(seed=case["seed"],action=action,kind="WHOLE_CAP_NOT_STARTED_UNKNOWN"));continue
   ac=next(x for x in s.legal_actions()if record_value(x)==action);child=p.apply_action(s.state,ac,c);ct=time.perf_counter();reply=[];winning=None;complete=False;actor=child.position.side_to_move
   if not child.terminal_status.is_terminal:
    def check():
     if time.perf_counter()-ct>=.5:raise TimeoutError("Frozen literalreply .5s")
    try:
     for rep in iter_legal_actions(child,c,checkpoint=check):
      check();z=p.apply_action(child,rep,c);reply.append(dict(action=record_value(rep),terminal=record_value(z.terminal_status)))
      if z.terminal_status.is_terminal and z.terminal_status.winner==actor:winning=record_value(rep);break
     else:complete=True
    except TimeoutError:pass
   kind="SELECTED_CHILD_TERMINAL"if child.terminal_status.is_terminal else"ONE_REPLY_WIN"if winning is not None else"NONE_FOUND_ONE_PLY"if complete else"UNKNOWN"
   row=dict(seed=case["seed"],board=case["board"],action=action,selected_child=record_value(child),kind=kind,complete=complete,winning_reply=winning,rows=reply,seconds=time.perf_counter()-ct);out.append(row)
   print("REPLY_DIAG",case["seed"],kind,len(reply),flush=True)
 write_record(P/"reply-diagnostics.json",dict(complete=True,rows=out,seconds=time.perf_counter()-start));return out
def games(selected):
 plan=json.loads((P/"followup-plan.json").read_bytes())["forced_games"];start=time.perf_counter();outputs=[];(P/"games").mkdir(exist_ok=False)
 for ci,case in enumerate(selected):
  if case["kind"]!="EXPOSED_SELECTED_PARENT":outputs.append(dict(case_index=ci,case=case,kind="NO_SENSITIVE_PAIR",no_game=True));continue
  for branch in["short_first","long_first"]:
   p.stopped()
   if time.perf_counter()-start>=plan["whole_seconds"]:outputs.append(dict(case_index=ci,seed=case["seed"],branch=branch,kind="WHOLE_CAP_NOT_STARTED_UNKNOWN"));continue
   gt=time.perf_counter();d,c,s,nr=a.load(R/case["root"]);actor=s.state.position.side_to_move;profile=build_ruleset_profile(c,EvaluationConfig());bv={k:int(round(v))for k,v in profile.board_value_by_type.items()};hv={k:int(round(v))for k,v in profile.hand_value_by_base_type.items()};engines=[p.SemanticSearchEngine(c,nr,board_values=bv,hand_values=hv,tt_megabytes=16,ordering_cache_enabled=False)for _ in range(2)]
   forced=case["low_action"]if branch=="short_first"else case["high_action"];before=p.digest(s);ac=next(x for x in s.legal_actions()if record_value(x)==forced);s.submit(ac)
   journal=P/"games"/f"case{ci}-{branch}-rows.jsonl";journal.open("x").close();rows=[];cause="FINITE_PLY_CAP_UNKNOWN"
   for step in range(plan["max_future_plies"]):
    p.stopped()
    if s.state.terminal_status.is_terminal:cause="ACTUAL_TERMINAL";break
    if time.perf_counter()-gt>=plan["game_cap_seconds"]:cause="GAME_CAP_UNKNOWN";break
    if time.perf_counter()-start>=plan["whole_seconds"]:cause="WHOLE_CAP_UNKNOWN";break
    before_turn=p.digest(s);side=s.state.position.side_to_move;t=time.perf_counter();res=engines[side].search(s,p.SearchLimits(max_depth=3,max_nodes=32768,max_time_seconds=.95,quiescence_max_depth=0),root_window_pruning=True,stop_on_immediate_win=True);seconds=time.perf_counter()-t;allowed=res.action is not None and seconds<1
    row=dict(step=step,side=side,before_sha256=before_turn,result=record_value(res),caller_seconds=seconds,execution_allowed=allowed,pv_edges=p.audit(s,nr,res))
    if allowed:s.submit(res.action);row.update(action=record_value(res.action),after_sha256=p.digest(s))
    rows.append(row)
    with journal.open("a",encoding="utf-8",newline="\n")as f:f.write(json.dumps(row)+"\n");f.flush();os.fsync(f.fileno())
    if not allowed:cause="CALLER_REFUSAL_UNKNOWN";break
   if s.state.terminal_status.is_terminal:cause="ACTUAL_TERMINAL"
   status=s.state.terminal_status;outcome="UNKNOWN"if not status.is_terminal else"DRAW"if status.winner is None else"WIN"if status.winner==actor else"LOSS"
   value=dict(case_index=ci,seed=case["seed"],board=case["board"],q=case["q"],branch=branch,kind="ACTUAL_GAME",actor=actor,forced_action=forced,parent_sha256=before,outcome=outcome,ending_cause=cause,terminal=record_value(status),rows=rows,final_game_record=json.loads(serialize_game_record(s.to_record())),final_state=record_value(s.state),seconds=time.perf_counter()-gt)
   write_record(P/"games"/f"case{ci}-{branch}.json",value);outputs.append(value);print("FORCED_GAME",ci,case["seed"],branch,outcome,cause,len(rows),round(value["seconds"],2),flush=True)
 write_record(P/"game-results.json",dict(complete=True,rows=outputs,seconds=time.perf_counter()-start));print("GAMES_CLOSED",len(outputs),time.perf_counter()-start,flush=True)
def main():
 curve=json.loads((P/"curve/results.json").read_bytes());cores=json.loads((P/"core-results.json").read_bytes());cp=json.loads((P/"curve-plan.json").read_bytes());assert curve["complete"]and len(curve["rows"])==cp["slots"]
 selected=select(curve,cp);write_record(P/"selected-followups.json",dict(complete=True,selection_frozen_before_games=True,cases=selected));diagnose(curve,cores);games(selected)
if __name__=="__main__":main()
