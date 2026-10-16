from pathlib import Path
import json,sys,time
R=Path.cwd();P=R/".local_agent/matched-d2-20261016";O=R/".local_agent/playability-mu-20261016";sys.path[:0]=[str(R),str(O)]
import core_control as cc
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.native import SemanticSearchEngine
from generic_chess.native.compiler import compile_native_semantic_rules
from scripts.research_record import record_value,write_record
p=cc.p;source=json.loads((P/"aux-action-alias-verified.json").read_bytes());plan=json.loads((P/"next-aux-finiteq-plan-private.json").read_bytes());write_record(P/"aux-finiteq-execution-plan.json",dict(plan,status="EXECUTE_SAME_ACTIVE_SEGMENT_WITH_UNCHANGED_INPUT_CAPS",reason="Completecheapcurrentquestionbeforeending; noreset/newsegment/capextension"));c=compile_ruleset_for_execution(deserialize_ruleset(json.dumps(source["ruleset"])));nr=compile_native_semantic_rules(c);values=plan["values"];rows=[];start=time.perf_counter()
for item in source["rows"]:
 s=GameSession.replay(c,deserialize_game_record(json.dumps(source["game_record"])));ac=next(x for x in s.legal_actions()if record_value(x)==item["action"]);s.submit(ac);assert record_value(s.state)==item["child"];before=p.digest(s)
 t=time.perf_counter();r=AlphaBetaPlayer(c,evaluator_override=cc.Material(values,values),use_tt=False,use_disk_cache=False,use_ordering=False,use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False)).choose_action(s,SearchLimits(max_depth=2,max_nodes=4096,max_time_seconds=1,quiescence_max_depth=0,quiescence_hard_max_depth=0));ct=time.perf_counter()-t
 t=time.perf_counter();n=SemanticSearchEngine(c,nr,board_values=values,hand_values=values,tt_megabytes=0,ordering_cache_enabled=False).search(s,SearchLimits(max_depth=2,max_nodes=4096,max_time_seconds=1,quiescence_max_depth=0),root_window_pruning=True);nt=time.perf_counter()-t;assert p.digest(s)==before
 row=dict(action=item["action"],child_state=record_value(s.state),core=record_value(r),native=record_value(n),core_seconds=ct,native_seconds=nt,joint_complete=r.completed_depth==n.completed_depth==2,root_action_q=-r.score if r.completed_depth==2 else None,pv_edges=p.audit(s,nr,n));rows.append(row)
 assert not row["joint_complete"]or r.score==n.score
out=dict(complete=True,rows=rows,queries=4,games=0,training=0,seconds=time.perf_counter()-start,scope="Source-exposedfixture, completedfiniteD3rootactionQ viaD2children; notoptimalWDL/population/trainedmodel. EqualV1inputcan'texpressstrictfinitepreferencewithoutadditionalcontext, approximateorderingtiesstillallowed; currentAPI/searchretainsboth. No model/productchange.")
write_record(P/"aux-finiteq-results.json",out);print("AUX_FINITEQ",[(x["action"]["pattern_id"],x["core"]["completed_depth"],x["native"]["completed_depth"],x["root_action_q"])for x in rows],flush=True)
