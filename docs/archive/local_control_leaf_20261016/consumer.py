"""Source-bound receipt replay: full state/history and derived vectors, no search."""
from pathlib import Path
from copy import copy
import sys,json,time,collections
R=Path.cwd();B=Path(sys.argv[1]).resolve();scope=sys.argv[2]if len(sys.argv)>2 else'all';sys.path[:0]=[str(R),str(R/'tests'),str(R/'tests/product')]
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove,PassAction
from generic_chess.core.coordinates import Square
from generic_chess.core.identity import position_identity_key
from generic_chess.native import semantic as sem,SemanticSearchEngine,_module
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.mirror import expected_snapshot,pack_semantic_action
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from scripts.research_record import record_value
from test_native_q_history_deferral import cycle
from test_native_pending_continuation import session_after
from phase19c1_native_semantic_fixtures import semantic_corpus
assert Path(_module().__file__).resolve().is_relative_to(R.resolve())
def forbidden(*a,**k):raise AssertionError('Receipt replay must not search')
SemanticSearchEngine.search=forbidden;AlphaBetaPlayer.choose_action=forbidden;_module().semantic_engine_search=forbidden
for name in('fixed_depth_search','probe_search','semantic_iterative_search','root_parallel_search'):setattr(sem,name,forbidden)
class Adapter(CompiledSemanticRuleset):
 __slots__=()
 def __getattr__(self,name):return getattr(self._legacy_compiled,name)
 @property
 def semantic(self):return self
def read(name):return json.loads((B/name).read_bytes())
def action(x):
 if x is None:return None
 if not x:return PassAction()
 if'from_square'in x:return SemanticBoardMove(x['pattern_id'],x['geometry_id'],x['actor_type_id'],Square(**x['from_square']),Square(**x['to_square']),x['promotion_target_id'])
 return SemanticDropMove(x['pattern_id'],x['geometry_id'],x['base_type_id'],Square(**x['to_square']))
cache={};counts=collections.Counter();start=time.perf_counter()
def root(kind,seed):
 key=(kind,seed)
 if key not in cache:
  if kind=='aliascycle':s=cycle(max_ply=512,repetition=4,prefix=seed)
  elif kind=='pending':s=session_after(('e2e4','d7d5','f1b5','c7c6'))
  elif kind=='cycle':
   s=cycle(max_ply=1024,repetition=10000,prefix=0);h=next(x for x in read('support-controls.json')['histories']if x['prefix']==seed);s=GameSession.replay(s.compiled,deserialize_game_record(json.dumps(h['game_record'])))
  else:
   d=read(kind+'-roots/'+str(seed)+'.json');x=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(d['ruleset'])));c=Adapter(ir=x.ir,_legacy_compiled=x._legacy_compiled,support=x.support);s=GameSession.replay(c,deserialize_game_record(json.dumps(d['game_record'])));assert record_value(s.state)==d['state']
  cache[key]=(s,compile_native_semantic_rules(s.compiled))
 s,nr=cache[key];return copy(s),nr
def compare(s,nr,np):
 snap=sem.snapshot(nr,np);want=expected_snapshot(s.state.position,nr,s.compiled)
 for k in('board','hands','aux_state','side'):assert record_value(snap[k])==record_value(want[k]),k
 assert snap['ply']==s.state.ply_count
 assert [''.join(f'{v:016x}'for v in row)for row in snap['history']]==[str(position_identity_key(p,s.compiled))for p in s._search_witnesses]
 assert snap['history_events']==tuple((255 if h.actor<0 else h.actor,bool(h.gave_check))for h in s.state.history)
 assert sem.terminal_status(nr,np)==dict(status=s.state.terminal_status.status.value,winner=s.state.terminal_status.winner)
 counts['full_state_history_comparisons']+=1
def query(kind,seed,r):
 s,nr=root(kind,seed);np=pack_semantic_search_position(s.compiled,nr,s);compare(s,nr,np);chosen=action(r.get('action'));assert chosen is None or chosen in s.legal_actions();line=r.get('decision_line')or r.get('principal_variation')or([r['action']]if chosen is not None else[])
 for item in line:
  if isinstance(item,str):s.declare(item);counts['declarations']+=1;continue
  ac=action(item);assert ac in s.legal_actions();np=sem.make_checked(nr,np,pack_semantic_action(nr,s.state.position,ac));s.submit(ac);compare(s,nr,np);counts['pv_or_fallback_edges']+=1
 if r.get('principal_variation')and'dynamic_features'in r:assert list(sem.dynamic_features(nr,np))==r['dynamic_features']
 counts['query_receipts']+=1


def verify_values(c,nr,np,values):
 before=record_value(sem.snapshot(nr,np));zero=(0,)*len(nr.type_ids)
 for row in values:
  assert row["isolated"]["normal"]==row["isolated"]["leaf"]
  assert row["mixed"]["normal"]==row["mixed"]["leaf"]
  actual=sem.evaluate(nr,np,board_values=zero,hand_values=zero,localized_control_values=row["weights"])
  assert actual==row["isolated"]["leaf"]
  mixed=sem.evaluate(nr,np,dynamic_values=(2,3,5),localized_control_values=row["weights"])
  assert mixed==row["mixed"]["leaf"]
 assert record_value(sem.snapshot(nr,np))==before
 counts["direct_leaf_contexts"]+=1

for fn,kind,field in (
 ("transfer-results.json","transfer","rows"),
 ("q-profile-results.json","old","rows"),
 ("fourcell-results.json","old","rows"),
 ("zero-results.json","old","rows"),
 ("coalescence-pilot-results.json","old","rows"),
 ("coalescence-controls-results.json","old","rows"),
 ("coalescence-v2-pilot-results.json","old","rows"),
 ("coalescence-v2-controls-results.json","old","rows"),
 ("outline-pilot-results.json","old","rows"),
 ("cancel-results.json","old","rows"),
 ("api-results.json","old","rows"),
 ("coalescence-transfer-results.json","coalescence","rows"),
 ("qualification-results.json","pending","queries"),
 ("coalescence-qualification-results.json","pending","queries"),
 ("coalescence-v2-qualification-results.json","pending","queries"),
):
 d=read(fn);assert d["complete"]
 for row in d[field]:
  if row.get("kind","ACTUAL_QUERY")!="ACTUAL_QUERY":
   counts[fn+":"+row["kind"]]+=1;continue
  query(kind,row.get("seed",0),row["result"]);counts[fn]+=1
for row in read("core-results.json")["rows"]:
 if row["kind"]!="ACTUAL_PAIR":counts["core_"+row["kind"]]+=1;continue
 for arm in ("core","native"):
  query("transfer",row["seed"],row[arm]);counts["core_"+arm+"_query_receipts"]+=1
for kind,fn in (("transfer","transfer-results.json"),("coalescence","coalescence-transfer-results.json")):
 for row in read(fn)["roots"]:
  s,nr=root(kind,row["seed"]);compare(s,nr,pack_semantic_search_position(s.compiled,nr,s));counts[kind+"_roots"]+=1
corpus=dict(semantic_corpus());origins={};rules={}
for row in read("support-controls.json")["mechanisms"]:
 c=corpus[row["fixture"]];s=GameSession.replay(c,deserialize_game_record(json.dumps(row["game_record"])))
 assert record_value(s.state)==row["state"]
 key=(row["fixture"],row["seed"],row["ply"]);origins[key]=s
 if row["fixture"]not in rules:rules[row["fixture"]]=compile_native_semantic_rules(c)
for fn in ("qualification-results.json","coalescence-qualification-results.json","coalescence-v2-qualification-results.json"):
 d=read(fn)
 for row in d["states"]:
  s=copy(origins[(row["fixture"],row["seed"],row["ply"])]);nr=rules[row["fixture"]];np=pack_semantic_search_position(s.compiled,nr,s)
  compare(s,nr,np);verify_values(s.compiled,nr,np,row["values"])
 import phase19b3_s4_fixtures as s4
 from dataclasses import replace
 from generic_chess.rules.compiler import compile_semantic_ruleset
 for row in d["s4"]:
  c=compile_semantic_ruleset(getattr(s4,row["fixture"])())
  from test_native_dynamic_feature_views import S4_CASES
  builder,posfn=next((a,b)for a,b in S4_CASES if a.__name__==row["fixture"])
  p=replace(posfn(c.support),side_to_move=row["owner"]);assert record_value(p)==row["position"]
  nr=compile_native_semantic_rules(c);payload=dict(expected_snapshot(p,nr,c),ply=0)
  payload["board"]=[None if p is None else list(p)for p in payload["board"]];payload["hands"]=[list(h)for h in payload["hands"]]
  verify_values(c,nr,sem.pack_position(nr,payload),row["values"]);counts["s4_specification_contexts"]+=1
 for row in d["histories"]:
  s=cycle(max_ply=1024,repetition=10000,prefix=row["prefix"]);nr=compile_native_semantic_rules(s.compiled);np=pack_semantic_search_position(s.compiled,nr,s);compare(s,nr,np)
  if row.get("errors"):
   try:sem.evaluate(nr,np,localized_control_values=(1,0,0,0,0,0,0,0,-1))
   except NotImplementedError as exc:assert str(exc)==row["errors"]["normal"];counts["capacity_refusals"]+=1
   else:raise AssertionError("capacitymustrefuse")
  else:verify_values(s.compiled,nr,np,row["values"])
  counts["actual_history_prefixes"]+=1
 for row in d["transport"]:
  s,nr=root("pending",0);np=sem.pack_position(nr,row["payload"]);verify_values(s.compiled,nr,np,row["values"]);counts["actual_or_edited_transport"]+=1
for row in read("mixed-cost-results.json")["rows"]:
 s,nr=root("old",row["seed"]);np=pack_semantic_search_position(s.compiled,nr,s)
 for profile,v in row["scores"].items():
  actual=sem.evaluate(nr,np,dynamic_values=(2,3,5)if profile in("dynamic","both")else None,localized_control_values=(1,0,0,0,0,0,0,0,-1)if profile in("control","both")else None)
  assert actual==v;counts["component_final_score_receipts"]+=1
 compare(s,nr,np)

alias=read("finite-alias-complete-results.json")
for row in alias["rows"]:
 s,nr=root("aliascycle",row["prefix"]);assert record_value(s.state)==row["state"]
 np=pack_semantic_search_position(s.compiled,nr,s)
 features=record_value(dict(dynamic=sem.dynamic_features(nr,np),spatial=sem.spatial_features(nr,np)))
 assert features==row["features"]
 for arm in ("core","native"):
  query("aliascycle",row["prefix"],row[arm]);counts["finite_alias_"+arm+"_queries"]+=1
assert alias["rows"][0]["features"]==alias["rows"][1]["features"]
for row in alias["continuations"]:
 s,nr=root("aliascycle",row["prefix"]);np=pack_semantic_search_position(s.compiled,nr,s);compare(s,nr,np)
 for edge in row["edges"]:
  aa=s.legal_actions();na=sem.guarded_actions(nr,np)
  assert len(aa)==len(na)==edge["legal_frontier_size"]==1
  ac=action(edge["action"]);assert ac==aa[0]==sem.public_action(nr,na[0])
  np=sem.make_checked(nr,np,na[0]);s.submit(ac)
  assert record_value(s.state)==edge["state"];compare(s,nr,np)
  counts["forced_unique_frontier_edges"]+=1
 assert s.state.terminal_status.winner is None and s.state.terminal_status.status.value=="repetition"
 counts["forced_diagnostic_continuations"]+=1
out=dict(complete=True,counts=dict(counts),seconds=time.perf_counter()-start,scope="SearchDISABLED freshlyrebuiltproduct/Core replay ofallretainedquery/PV/fallback fullstate-history receipts anddirectleafcontexts. Actualdata, censors/tails andprivatecandidate comparisons retained; nooldclock/finiteobjective/WDL orAUXproducer recomputation. Corecompiler/hostshared, notall-domainproof.")
(B/"consumer-result.json").write_bytes((json.dumps(out,indent=2)+"\n").encode());print(json.dumps(out))
