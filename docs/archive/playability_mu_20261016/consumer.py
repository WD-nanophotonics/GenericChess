"""Search-disabled full-state/history consumer for this frozen research segment."""
from pathlib import Path
import sys,json,time,hashlib,collections
R=Path.cwd();sys.path.insert(0,str(R));B=Path(sys.argv[1])if len(sys.argv)>1 else R/'.local_agent/playability-mu-20261016'
phase=sys.argv[2]if len(sys.argv)>2 else'all'
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.ir import CompiledSemanticRuleset
class Adapter(CompiledSemanticRuleset):
 __slots__=()
 def __getattr__(self,name):return getattr(self._legacy_compiled,name)
 @property
 def semantic(self):return self
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove,PassAction
from generic_chess.core.coordinates import Square
from generic_chess.core.identity import position_identity_key
from generic_chess.core.transition import apply_action
from generic_chess.core.movegen import iter_legal_actions
from generic_chess.native import compiler as nc,semantic as sem,SemanticSearchEngine,_module
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.mirror import expected_snapshot,pack_semantic_action
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from scripts.research_record import record_value
assert Path(nc.__file__).resolve().is_relative_to(R.resolve())
assert Path(_module().__file__).resolve().is_relative_to(R.resolve())
def forbidden(*args,**kwargs):raise AssertionError('No new search/game/proof in receipt replay')
SemanticSearchEngine.search=forbidden;_module().semantic_engine_search=forbidden;AlphaBetaPlayer.choose_action=forbidden
sem.fixed_depth_search=forbidden;sem.probe_search=forbidden;sem.semantic_iterative_search=forbidden;sem.root_parallel_search=forbidden
def read(p):return json.loads((B/p).read_bytes())
def action(d):
 if d is None:return None
 if not d:return PassAction()
 if'from_square'in d:return SemanticBoardMove(d['pattern_id'],d['geometry_id'],d['actor_type_id'],Square(**d['from_square']),Square(**d['to_square']),d['promotion_target_id'])
 return SemanticDropMove(d['pattern_id'],d['geometry_id'],d['base_type_id'],Square(**d['to_square']))
def digest(st):return hashlib.sha256(json.dumps(record_value(st),sort_keys=True).encode()).hexdigest()
counts=collections.Counter();cache={};roots=set()
last_compilation={}
def compiled(d):
 key=json.dumps(d['ruleset'],separators=(',',':'))
 if last_compilation.get('key')==key:return last_compilation['value']
 raw=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(d['ruleset'])))
 c=Adapter(ir=raw.ir,_legacy_compiled=raw._legacy_compiled,support=raw.support);value=(c,nc.compile_native_semantic_rules(c))
 last_compilation.clear();last_compilation.update(key=key,value=value);return value
def load(folder,seed):
 k=(folder,seed)
 if k not in cache:
  d=read(folder+'/'+str(seed)+'.json');c,nr=compiled(d);cache[k]=(d,c,nr)
 d,c,nr=cache[k];s=GameSession.replay(c,deserialize_game_record(json.dumps(d['game_record'])))
 assert digest(s.state)==d['before_sha256'];roots.add(digest(s.state));return s,nr,d
def compare(s,nr,state,np,w):
 snap=sem.snapshot(nr,np);exp=expected_snapshot(state.position,nr,s.compiled)
 for k in('board','hands','aux_state','side'):assert record_value(snap[k])==record_value(exp[k])
 assert snap['ply']==state.ply_count
 assert [''.join(f'{v:016x}'for v in h)for h in snap['history']]==[str(position_identity_key(v,s.compiled))for v in w]
 assert snap['history_events']==tuple((255 if e.actor<0 else e.actor,bool(e.gave_check))for e in state.history)
 assert sem.terminal_status(nr,np)==dict(status=state.terminal_status.status.value,winner=state.terminal_status.winner)
 assert snap['history_exact']and snap['history_events_exact']
 counts['state_history_comparisons']+=1
def query(s,nr,r,limit):
 assert r['nodes']+r['qnodes']<=limit
 chosen=action(r['action']);assert chosen is None or chosen in s.legal_actions()
 state=s.state;np=pack_semantic_search_position(s.compiled,nr,s);w=list(s._search_witnesses)
 line=[action(x)for x in r['principal_variation']]
 if line:assert line[0]==chosen
 if not line and chosen is not None:line=[chosen]
 for ac in line:
  np=sem.make_checked(nr,np,pack_semantic_action(nr,state.position,ac));state=apply_action(state,ac,s.compiled);w.append(state.position);compare(s,nr,state,np,w);counts['pv_edges']+=1
 counts['query_receipts']+=1
def actual_path(s,nr,packed_path):
 path=[]
 for packed in packed_path:
  ac=sem.public_action(nr,packed);np=pack_semantic_search_position(s.compiled,nr,s);np=sem.make_checked(nr,np,packed);s.submit(ac);compare(s,nr,s.state,np,list(s._search_witnesses));path.append(record_value(ac));counts['captured_path_edges']+=1
 return path
def relroot(path):
 prefix=".local_agent/playability-mu-20261016/"
 path=str(path).replace(chr(92),"/")
 return path[len(prefix):]if path.startswith(prefix)else path
def root(d,meta=None):
 c,nr=compiled(meta or d);s=GameSession.replay(c,deserialize_game_record(json.dumps(d["game_record"])))
 assert record_value(s.state)==d["state"]
 if"before_sha256"in d:assert digest(s.state)==d["before_sha256"]
 compare(s,nr,s.state,pack_semantic_search_position(c,nr,s),list(s._search_witnesses));counts["root_records"]+=1
 return s,nr
def case_root(case):
 return root(read(relroot(case["root"])))
def edge(s,nr,state,ac):
 np=pack_semantic_search_position(s.compiled,nr,s)
 if state is not s.state:raise AssertionError("explicitstateonly")
 np=sem.make_checked(nr,np,pack_semantic_action(nr,state.position,ac));z=apply_action(state,ac,s.compiled)
 compare(s,nr,z,np,list(s._search_witnesses)+[z.position]);return z,np
def frontier(s,nr,state,np,w,rows,field):
 legal=tuple(iter_legal_actions(state,s.compiled))
 for row in rows:
  ac=action(row["action"]);assert ac in legal
  n=sem.make_checked(nr,np,pack_semantic_action(nr,state.position,ac));z=apply_action(state,ac,s.compiled)
  assert record_value(z.terminal_status)==row[field];compare(s,nr,z,n,w+[z.position]);counts["literal_reply_edges"]+=1
 return len(legal)
start=time.perf_counter()
if phase not in["interaction","matrix"]:
 for folder in["","corrected/","tail_only/"]:
  for f in sorted((B/folder).glob("pipeline-*/result.json")):
   d=json.loads(f.read_bytes());assert d["complete"]
   journal=f.parent/"rows.jsonl"
   if journal.exists():assert d["rows"]==[json.loads(x)for x in journal.read_text(encoding="utf-8").splitlines()]
   for row in d["rows"]:
    if"root_file"not in row:continue
    full=json.loads((f.parent/row["root_file"]).read_bytes());s,nr=root(full)
    if"predicate"in row:query(s,nr,row["predicate"],65536);counts["acquisition_predicate_receipts"]+=1
 assessment=read("assessment-results.json");assert assessment["complete"]
 for row in assessment["rows"]:
  s,nr=case_root(row);query(s,nr,row["native"],65536);counts["assessment_queries"]+=1
  np=pack_semantic_search_position(s.compiled,nr,s);n=frontier(s,nr,s.state,np,list(s._search_witnesses),row["core_rows"],"child_terminal")
  if row["core_complete"]:assert len(row["core_rows"])==n
  counts["literal_frontiers"]+=1
 cores=read("core-results.json");assert cores["complete"]
 for row in cores["rows"]:
  if row["kind"]!="ACTUAL_QUERY":continue
  s,nr=case_root(row)
  for key in["core","native"]:query(s,nr,row[key],8192);counts["core_control_queries"]+=1
 domain=read("domain/results.json");assert domain["complete"]
 for row in domain["rows"]:
  if"input_file"not in row:continue
  data=read(row["input_file"]);d=next(x for x in data["roots"]if x["ply"]==row["ply"]);s,nr=root(d,data)
  for key,limit in[("goal",65536),("core",8192),("native",8192)]:
   if key in row:query(s,nr,row[key],limit);counts["domain_queries"]+=1
 for row in read("counterexample-results.json")["rows"]:
  if row["kind"]!="ACTUAL_QUERY":continue
  s,nr=case_root(row);query(s,nr,row["core"],1000000);counts["counterexample_queries"]+=1
  for n in row["native_rows"]:query(s,nr,n["result"],1000000);counts["counterexample_queries"]+=1
 for row in read("counterexample-binding.json")["rows"]:
  s,nr=case_root(row);query(s,nr,row["result"],1000000);counts["counterexample_queries"]+=1
if phase in["post","all"]:
 curve=read("curve/results.json");assert curve["complete"]
 assert curve["rows"]==[json.loads(x)for x in(B/"curve/rows.jsonl").read_text(encoding="utf-8").splitlines()]
 for row in curve["rows"]:
  if row.get("result")is None:continue
  s,nr=case_root(row);query(s,nr,row["result"],1000000);counts["curve_queries"]+=1
 cases={x["seed"]:x for x in read("curve-plan.json")["cases"]}
 for row in read("reply-diagnostics.json")["rows"]:
  if"selected_child"not in row:continue
  s,nr=case_root(cases[row["seed"]]);state,np=edge(s,nr,s.state,action(row["action"]));assert record_value(state)==row["selected_child"]
  w=list(s._search_witnesses)+[state.position];n=frontier(s,nr,state,np,w,row["rows"],"terminal")
  if row["complete"]:assert n==len(row["rows"])
  counts["diagnostic_choices"]+=1
 for game in read("game-results.json")["rows"]:
  if game["kind"]!="ACTUAL_GAME":continue
  s,nr=case_root(cases[game["seed"]]);assert digest(s.state)==game["parent_sha256"]
  ac=action(game["forced_action"]);np=pack_semantic_search_position(s.compiled,nr,s);np=sem.make_checked(nr,np,pack_semantic_action(nr,s.state.position,ac));s.submit(ac);compare(s,nr,s.state,np,list(s._search_witnesses));counts["physical_edges"]+=1
  for row in game["rows"]:
   assert digest(s.state)==row["before_sha256"];query(s,nr,row["result"],32768);counts["game_queries"]+=1
   if not row["execution_allowed"]:assert"action"not in row;continue
   ac=action(row["action"]);assert row["action"]==row["result"]["action"]
   np=pack_semantic_search_position(s.compiled,nr,s);np=sem.make_checked(nr,np,pack_semantic_action(nr,s.state.position,ac));s.submit(ac)
   compare(s,nr,s.state,np,list(s._search_witnesses));assert digest(s.state)==row["after_sha256"];counts["physical_edges"]+=1
  assert record_value(s.state)==game["final_state"]
  assert json.loads(serialize_game_record(s.to_record()))==game["final_game_record"]
  term=s.state.terminal_status;outcome="UNKNOWN"if not term.is_terminal else"DRAW"if term.winner is None else"WIN"if term.winner==game["actor"]else"LOSS"
  assert outcome==game["outcome"];counts["physical_games"]+=1
if phase in["interaction","all"]:
 info=read("interaction/inputs.json");assert info["complete"]and info["search_queries"]==0
 for inp in info["rows"]:
  d=read("interaction/roots/"+str(inp["seed"])+".json")
  if"ruleset"in d:root(d)
 completion=read("interaction/completion.json");assert completion["complete"]
 for item in completion["games"]:
  if item["kind"]!="ACTUAL_GAME":continue
  game=read("interaction/game-"+str(item["seed"])+"-"+item["mode"]+".json");assert game["complete"]
  rows=[json.loads(x)for x in(B/("interaction/game-"+str(item["seed"])+"-"+item["mode"]+".jsonl")).read_text(encoding="utf-8").splitlines()]
  assert rows==game["rows"]
  s,nr=root(read("interaction/roots/"+str(item["seed"])+".json"))
  for row in game["rows"]:
   assert digest(s.state)==row["before_sha256"];query(s,nr,row["result"],262144);counts["interaction_queries"]+=1
   if not row["execution_allowed"]:assert"action"not in row;continue
   ac=action(row["action"]);assert row["action"]==row["result"]["action"]
   np=pack_semantic_search_position(s.compiled,nr,s);np=sem.make_checked(nr,np,pack_semantic_action(nr,s.state.position,ac));s.submit(ac)
   compare(s,nr,s.state,np,list(s._search_witnesses));assert digest(s.state)==row["after_sha256"];counts["physical_edges"]+=1;counts["interaction_physical_edges"]+=1
  assert record_value(s.state)==game["final_state"]
  assert json.loads(serialize_game_record(s.to_record()))==game["final_game_record"]
  assert record_value(s.state.terminal_status)==game["terminal"]==item["terminal"]
  assert item["edges"]==sum("action"in row for row in game["rows"])
  if game["ending_cause"]=="ACTUAL_TERMINAL":assert s.state.terminal_status.is_terminal
  else:assert not s.state.terminal_status.is_terminal
  counts["physical_games"]+=1;counts["interaction_games"]+=1
 if (B/"common-parent-results.json").exists():
  meta=read("common-parent-results.json");assert meta["complete"]and meta["search_queries"]==0
  for row in meta["rows"]:
   if"root_file"not in row:continue
   d=read(row["root_file"]);s,nr=root(d);assert digest(s.state)==row["before_sha256"]
   for key in["left_source","right_source"]:
    ref=d[key];g=read(ref["file"]);rr=g["rows"][ref["step"]]
    assert rr["before_sha256"]==d["before_sha256"]==ref["before_sha256"];assert rr["result"]==ref["result"]
   counts["common_parent_records"]+=1
if phase in["matrix","all"]:
 data=read("common-matrix-results.json");assert data["complete"]
 for row in data["rows"]:
  if row["kind"]!="ACTUAL_COMMON_MATRIX":continue
  s,nr=root(read(row["root_file"]))
  for item in row["native_rows"]+row["core_rows"]:
   query(s,nr,item["result"],8192);counts["common_matrix_queries"]+=1
out=dict(complete=True,phase=phase,counts=dict(counts),seconds=time.perf_counter()-start,scope="Search-disabled exact Core/normalNative fullstate/absolute-ply/history replay of all actual receipts, literal edges and physicalgames. SameCore/compiler/host, not independentWDL/newsearch or historicalclock authentication. Failures/censors remain; no privateimage or unadoptedproposal activation.")
(B/("consumer-"+phase+".json")).write_bytes((json.dumps(out,indent=2)+"\n").encode());print(json.dumps(out),flush=True)
