import json,sys,time,hashlib
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/".local_agent/pinned_bebe"));sys.path.insert(1,str(R));B=Path(__file__).resolve().parent
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_from_dict,action_to_dict
from scripts.research_record import record_value
c=compile_semantic_ruleset(build_western_chess_ruleset());n=compile_native_semantic_rules(c);decl=json.loads((R/"results/dev_aux/task093/declaration.json").read_bytes());d={"question":"Zero dynamic weights still invoke feature construction. Can None omit work for an otherwise explicit pure material profile?","conditions":"Three declared existing legal training openings, seed103 initial board values/hand0, actual512node/maxdepth8 q0 caller, fresh4MiB engine, opposite execution order byroot. Compare action/score/PV/allcount metrics and Core restoration; no current training edits, no timed strength claim.","cost":"6 bounded searches expected below5seconds; source-shown zero features cost change only."};(B/"declaration.json").write_bytes((json.dumps(d,indent=2)+"\n").encode());rows=[]
for j,op in enumerate(decl["train_openings"][:3]):
 s=GameSession(c)
 for a in op["actions"]:s.submit(action_from_dict(a))
 before=(s.state,tuple(s.history),s.result);values=tuple(decl["starts_weights"]["103"][k] for k in n.type_ids);arms={}
 for arm in (("zero","none") if j%2==0 else ("none","zero")):
  start=time.perf_counter();e=SemanticSearchEngine(c,n,board_values=values,hand_values=(0,)*len(values),dynamic_values=(0,0,0) if arm=="zero" else None,tt_megabytes=4);r=e.search(s,SearchLimits(max_depth=8,max_nodes=512,quiescence_max_depth=0));arms[arm]={"result":record_value(r),"wall_seconds":time.perf_counter()-start};assert before==(s.state,tuple(s.history),s.result)
 a,b=[arms[k]["result"] for k in ("zero","none")];excluded={"elapsed_seconds","ordering_elapsed_seconds","ordering_elapsed_nanoseconds_by_ply","policy_elapsed_seconds","policy_elapsed_seconds_by_ply"};equal={k:a[k]==b[k] for k in a if k not in excluded};assert all(equal.values()),{k:v for k,v in equal.items() if not v};rows.append({"root":j,"arms":arms,"all_non_time_fields_equal":True,"ratio":arms["none"]["wall_seconds"]/arms["zero"]["wall_seconds"]})
out={"complete":True,"rows":rows,"scope":"Finite actual pure-material caller representation, not product patch/mature search or new training data"};(B/"result.json").write_bytes((json.dumps(out,indent=2)+"\n").encode());print([(x["root"],round(x["ratio"],3),[round(x["arms"][k]["wall_seconds"],3) for k in ("zero","none")]) for x in rows])
