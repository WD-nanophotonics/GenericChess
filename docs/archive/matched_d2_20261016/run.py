from pathlib import Path
import sys,json,time,os,hashlib
R=Path.cwd();OLD=R/".local_agent/playability-mu-20261016";P=R/".local_agent/matched-d2-20261016"
sys.path[:0]=[str(R),str(OLD)]
import assessment as a
p=a.p
from scripts.research_record import record_value,write_record
from generic_chess.session.serialization import serialize_game_record
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
def canonical(x):return json.dumps(x,sort_keys=True,separators=(",",":"))
def freeze():
 source=json.loads((P/"prepared-plan.json").read_bytes()); matrix=json.loads((OLD/"common-matrix-results.json").read_bytes())
 plan=dict(source);plan.update(status="FROZEN_BEFORE_FUTURE_LABELS",frozen_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),source_sha=__import__("subprocess").check_output(["git","rev-parse","HEAD"],text=True).strip(),future=dict(depth=3,nodes=32768,caller_seconds=1,search_seconds=.95,reserve=.05,q=0,tt_mb=16,root_window=True,immediate_win=True,ordering_cache=False),game_seconds=90,whole_seconds=1800,max_future_plies=64,planned_cells=32,run_order="families listed; uniqueactions encountered ABCD for oddindex/reverseDCBA for evenindex",claim="EXPOSED conditional firstaction comparison, no strength/generalprice/all-defense or equalactualdepthfuture claim; alltimeouts/missing UNKNOWN",expected_seconds=600)
 (P/"roots").mkdir(exist_ok=False)
 for case in plan["cases"]:
  d=json.loads((OLD/case["root_file"]).read_bytes());assert d["before_sha256"]==case["state_sha256"]
  name=str(case["seed"])+".json";(P/"roots"/name).write_bytes((OLD/case["root_file"]).read_bytes());case["root"]="roots/"+name
 plan["unique_games"]=sum(len({canonical(v)for v in x["forced_actions"].values()})for x in plan["cases"])
 write_record(P/"plan.json",plan);print("FROZEN",plan["unique_games"],flush=True)
def run():
 plan=json.loads((P/"plan.json").read_bytes());out=[];start=time.perf_counter();(P/"games").mkdir(exist_ok=False)
 for ci,case in enumerate(plan["cases"]):
  labels=list("ABCD")if ci%2==0 else list("DCBA");unique={}
  for label in labels:unique.setdefault(canonical(case["forced_actions"][label]),[]).append(label)
  for gi,(key,cells)in enumerate(unique.items()):
   p.stopped();game_id=str(case["seed"])+"-"+str(gi)
   if time.perf_counter()-start>=plan["whole_seconds"]:
    row=dict(game_id=game_id,seed=case["seed"],cells=cells,kind="NOT_STARTED",outcome="UNKNOWN",ending_cause="WHOLE_CAP_NOT_STARTED_UNKNOWN");out.append(row);continue
   gt=time.perf_counter();d,c,s,nr=a.load(P/case["root"]);assert p.digest(s)==case["state_sha256"];actor=s.state.position.side_to_move
   profile=build_ruleset_profile(c,EvaluationConfig());bv={k:int(round(v))for k,v in profile.board_value_by_type.items()};hv={k:int(round(v))for k,v in profile.hand_value_by_base_type.items()}
   engines=[p.SemanticSearchEngine(c,nr,board_values=bv,hand_values=hv,tt_megabytes=16,ordering_cache_enabled=False)for _ in range(2)]
   ac=next(x for x in s.legal_actions()if record_value(x)==json.loads(key));s.submit(ac);forced=record_value(ac);rows=[];cause="FINITE_PLY_CAP_UNKNOWN";journal=P/"games"/(game_id+"-rows.jsonl")
   with journal.open("x"):pass
   for step in range(plan["max_future_plies"]):
    p.stopped()
    if s.state.terminal_status.is_terminal:cause="ACTUAL_TERMINAL";break
    if time.perf_counter()-gt>=plan["game_seconds"]:cause="GAME_CAP_UNKNOWN";break
    if time.perf_counter()-start>=plan["whole_seconds"]:cause="WHOLE_CAP_UNKNOWN";break
    before=p.digest(s);side=s.state.position.side_to_move;t=time.perf_counter()
    res=engines[side].search(s,p.SearchLimits(max_depth=3,max_nodes=32768,max_time_seconds=.95,quiescence_max_depth=0),root_window_pruning=True,stop_on_immediate_win=True);seconds=time.perf_counter()-t;allowed=res.action is not None and seconds<1
    row=dict(step=step,side=side,before_sha256=before,result=record_value(res),caller_seconds=seconds,execution_allowed=allowed,pv_edges=p.audit(s,nr,res))
    if allowed:s.submit(res.action);row.update(action=record_value(res.action),after_sha256=p.digest(s))
    rows.append(row)
    with journal.open("a",encoding="utf-8",newline="\n")as f:f.write(json.dumps(row)+"\n");f.flush();os.fsync(f.fileno())
    if not allowed:cause="CALLER_REFUSAL_UNKNOWN";break
   if s.state.terminal_status.is_terminal:cause="ACTUAL_TERMINAL"
   status=s.state.terminal_status;outcome="UNKNOWN"if not status.is_terminal else"DRAW"if status.winner is None else"WIN"if status.winner==actor else"LOSS"
   row=dict(game_id=game_id,seed=case["seed"],board=case["board"],cells=cells,kind="ACTUAL_GAME",actor=actor,forced_action=forced,parent_sha256=case["state_sha256"],outcome=outcome,ending_cause=cause,terminal=record_value(status),rows=rows,final_game_record=json.loads(serialize_game_record(s.to_record())),final_state=record_value(s.state),seconds=time.perf_counter()-gt)
   write_record(P/"games"/(game_id+".json"),row);out.append(row);print("GAME",game_id,cells,outcome,cause,len(rows),round(row["seconds"],3),flush=True)
 write_record(P/"results.json",dict(complete=True,rows=out,seconds=time.perf_counter()-start));print("CLOSED",len(out),time.perf_counter()-start,flush=True)
if __name__=="__main__":
 if sys.argv[-1]=="freeze":freeze()
 else:run()
