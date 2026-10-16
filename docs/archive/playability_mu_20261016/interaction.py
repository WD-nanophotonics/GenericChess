from pathlib import Path
import sys,json,time,random,os
from types import SimpleNamespace
R=Path.cwd();P=R/".local_agent/playability-mu-20261016";sys.path[:0]=[str(R),str(P)]
import assessment as a
p=a.p
from scripts.research_record import record_value,write_record
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.serialization import serialize_ruleset
from generic_chess.session.serialization import serialize_game_record
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
def prepare(plan,base):
 manifest=[];start=time.perf_counter();(base/"roots").mkdir()
 for case in plan["cases"]:
  p.stopped();t=time.perf_counter();out=dict(**case,eligible=False,kind="INPUT_FAILURE")
  try:
   cfg=GeneratorConfig(seed=case["seed"],board_size=case["board"],setup_preset=case["preset"],movement_symmetry=case["symmetry"],allow_hybrid=True,max_generation_attempts=32);g=generate_game(cfg);raw=p.compile_legacy_ruleset_for_semantic_execution(g.ruleset);c=p.SearchMetadataAdapter(ir=raw.ir,_legacy_compiled=raw._legacy_compiled,support=raw.support);s=p.GameSession(c);rng=random.Random(case["seed"]+340000);walk=[]
   for _ in range(8):
    p.stopped()
    if s.state.terminal_status.is_terminal:break
    acts=s.legal_actions()
    if not acts:break
    ac=rng.choice(sorted(acts,key=repr));s.submit(ac);walk.append(record_value(ac))
   profile=build_ruleset_profile(c,EvaluationConfig());out.update(config=record_value(cfg),ruleset=json.loads(serialize_ruleset(g.ruleset)),game_record=json.loads(serialize_game_record(s.to_record())),state=record_value(s.state),before_sha256=p.digest(s),walk=walk,generation_report=record_value(g.generation_report),board_values={k:int(round(v))for k,v in profile.board_value_by_type.items()},hand_values={k:int(round(v))for k,v in profile.hand_value_by_base_type.items()},kind="INPUT_FROZEN_NO_SEARCH"if len(walk)==8 and not s.state.terminal_status.is_terminal else"TERMINAL_TAIL",eligible=len(walk)==8 and not s.state.terminal_status.is_terminal)
  except Exception as exc:out["error"]=type(exc).__name__+": "+str(exc)
  out["seconds"]=time.perf_counter()-t;write_record(base/"roots"/f"{case['seed']}.json",out);manifest.append(dict(**case,eligible=out["eligible"],kind=out["kind"],seconds=out["seconds"]));print("INTERACTION_INPUT",case["seed"],out["kind"],flush=True)
 write_record(base/"inputs.json",dict(complete=True,rows=manifest,search_queries=0,seconds=time.perf_counter()-start))
 return manifest
def run(case,mode,plan,base,start):
 root=base/"roots"/f"{case['seed']}.json";gt=time.perf_counter();d,c,s,nr=a.load(root);role=None if mode=="C_control"else int(mode[-1]);treatment="C"if role is None else mode[0];unit={k:0 if k=="K"else 100 for k in nr.type_ids};cells={i:treatment if i==role else"C"for i in[0,1]}
 engines={i:p.SemanticSearchEngine(c,nr,board_values=unit if plan["cells"][cells[i]]["price"].startswith("UNIT")else d["board_values"],hand_values=unit if plan["cells"][cells[i]]["price"].startswith("UNIT")else d["hand_values"],tt_megabytes=16,ordering_cache_enabled=False)for i in[0,1]}
 rows=[];cause="FINITE_PLY_CAP_UNKNOWN";journal=base/f"game-{case['seed']}-{mode}.jsonl";journal.open("x").close()
 for ply in range(64):
  p.stopped()
  if s.state.terminal_status.is_terminal:cause="ACTUAL_TERMINAL";break
  if time.perf_counter()-gt>=45:cause="GAME_CAP_UNKNOWN";break
  if time.perf_counter()-start>=plan["whole_seconds"]:cause="WHOLE_CAP_UNKNOWN";break
  side=s.state.position.side_to_move;cell=cells[side];q=plan["cells"][cell]["q"];before=p.digest(s);ct=time.perf_counter();res=engines[side].search(s,p.SearchLimits(max_depth=16,max_nodes=262144,max_time_seconds=.45,quiescence_max_depth=q,quiescence_hard_max_depth=8),root_window_pruning=True,stop_on_immediate_win=True);seconds=time.perf_counter()-ct;allowed=res.action is not None and seconds<.5
  row=dict(ply=ply,side=side,cell=cell,q=q,before_sha256=before,result=record_value(res),caller_seconds=seconds,execution_allowed=allowed,pv_edges=p.audit(s,nr,res))
  if allowed:
   row["physical_audit_edges"]=p.audit(s,nr,SimpleNamespace(action=res.action,principal_variation=(res.action,)));s.submit(res.action);row.update(action=record_value(res.action),after_sha256=p.digest(s))
  rows.append(row)
  with journal.open("a",encoding="utf-8",newline="\n")as f:f.write(json.dumps(row)+"\n");f.flush();os.fsync(f.fileno())
  if not allowed:cause="CALLER_REFUSAL_UNKNOWN";break
 if s.state.terminal_status.is_terminal:cause="ACTUAL_TERMINAL"
 out=dict(complete=True,case=case,mode=mode,role=role,cell=treatment,kind="ACTUAL_GAME",ending_cause=cause,terminal=record_value(s.state.terminal_status),rows=rows,final_state=record_value(s.state),final_game_record=json.loads(serialize_game_record(s.to_record())),seconds=time.perf_counter()-gt)
 write_record(base/f"game-{case['seed']}-{mode}.json",out);print("INTERACTION_GAME",case["seed"],mode,cause,len(rows),out["terminal"],round(out["seconds"],2),flush=True)
 return dict(**case,mode=mode,kind="ACTUAL_GAME",ending_cause=cause,terminal=out["terminal"],seconds=out["seconds"],edges=sum("action"in r for r in rows),query_receipts=len(rows))
def main():
 plan=json.loads((P/"interaction-plan.json").read_bytes());base=P/"interaction";base.mkdir(exist_ok=False);start=time.perf_counter();inputs=prepare(plan,base);games=[]
 for case in plan["cases"]:
  inp=next(x for x in inputs if x["seed"]==case["seed"]);modes=plan["actual_modes"]if case["seed"]%2 else list(reversed(plan["actual_modes"]))
  for mode in modes:
   p.stopped()
   if not inp["eligible"]:games.append(dict(**case,mode=mode,kind="MISSING_INPUT_UNKNOWN"));continue
   if time.perf_counter()-start>=plan["whole_seconds"]:games.append(dict(**case,mode=mode,kind="WHOLE_CAP_NOT_STARTED_UNKNOWN"));continue
   games.append(run(case,mode,plan,base,start));write_record(base/"completion-partial.json",dict(complete=False,games=games,seconds=time.perf_counter()-start))
 write_record(base/"completion.json",dict(complete=True,games=games,seconds=time.perf_counter()-start));print("INTERACTION_CLOSED",len(games),time.perf_counter()-start,flush=True)
if __name__=="__main__":main()
