"""Search-disabled full-state/history consumer for this frozen research segment."""
from pathlib import Path
import sys,json,time,hashlib,collections
R=Path.cwd();sys.path.insert(0,str(R));B=Path(sys.argv[1])if len(sys.argv)>1 else R/'.local_agent/matched-d2-20261016'
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
 prefix=".local_agent/matched-d2-20261016/"
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

plan=read("plan.json");data=read("results.json");assert data["complete"];cases={x["seed"]:x for x in plan["cases"]}
for game in data["rows"]:
 if game["kind"]!="ACTUAL_GAME":continue
 case=cases[game["seed"]];s,nr=root(read(case["root"]));assert digest(s.state)==game["parent_sha256"]
 assert all(case["forced_actions"][c]==game["forced_action"]for c in game["cells"])
 ac=action(game["forced_action"]);np=pack_semantic_search_position(s.compiled,nr,s);np=sem.make_checked(nr,np,pack_semantic_action(nr,s.state.position,ac));s.submit(ac);compare(s,nr,s.state,np,list(s._search_witnesses));counts["physical_edges"]+=1
 assert [json.loads(x)for x in(B/"games"/(game["game_id"]+"-rows.jsonl")).read_text().splitlines()]==game["rows"]
 for row in game["rows"]:
  assert digest(s.state)==row["before_sha256"];query(s,nr,row["result"],32768)
  assert row["execution_allowed"]==(row["result"]["action"]is not None and row["caller_seconds"]<1)
  if not row["execution_allowed"]:assert"action"not in row;continue
  ac=action(row["action"]);assert row["action"]==row["result"]["action"];np=pack_semantic_search_position(s.compiled,nr,s);np=sem.make_checked(nr,np,pack_semantic_action(nr,s.state.position,ac));s.submit(ac);compare(s,nr,s.state,np,list(s._search_witnesses));assert digest(s.state)==row["after_sha256"];counts["physical_edges"]+=1
 assert record_value(s.state)==game["final_state"];assert json.loads(serialize_game_record(s.to_record()))==game["final_game_record"];assert record_value(s.state.terminal_status)==game["terminal"]
 term=s.state.terminal_status;outcome="UNKNOWN"if not term.is_terminal else"DRAW"if term.winner is None else"WIN"if term.winner==game["actor"]else"LOSS"
 assert outcome==game["outcome"];assert(term.is_terminal)==(game["ending_cause"]=="ACTUAL_TERMINAL");counts["physical_games"]+=1

if(B/"scale-results.json").exists():
 sd=read("scale-results.json");assert sd["complete"]
 for row in sd["rows"]:
  if row["kind"]!="ACTUAL_QUERY":continue
  s,nr=root(read(row["root"]));query(s,nr,row["result"],65536);assert row["root_restored"];counts["scale_queries"]+=1
if(B/"representation-results.json").exists():
 import struct
 rd=read("representation-results.json");assert rd["complete"]and rd["queries"]==rd["games"]==0
 for row in rd["rows"]:
  c,nr=compiled(row);s=GameSession(c);assert record_value(s.state)==row["state"];assert digest(s.state)==row["fullstate_sha256"];compare(s,nr,s.state,pack_semantic_search_position(c,nr,s),list(s._search_witnesses))
  assert [record_value(x)for x in s.legal_actions()]==row["legal_actions"];assert record_value(s.state.terminal_status)==row["terminal"]
  inds=row["indices"];vals=row["values"];assert len(inds)==len(set(inds))==len(vals)
  dense=[0.0]*row["dimension"]
  for i,v in zip(inds,vals):dense[i]=v
  assert hashlib.sha256(struct.pack("<"+"d"*len(dense),*dense)).hexdigest()==row["vector_sha256"]
  counts["representation_rulevariants"]+=1

for fn,limit,metric in [("material-profile-results.json",65536,"material_profile_queries"),("q1-transition/results.json",131072,"transition_control_queries")]:
 if not(B/fn).exists():continue
 d=read(fn);assert d["complete"]
 for row in d["rows"]:
  s,nr=root(read(row["root"]));query(s,nr,row["result"],limit);assert row["root_restored"];counts[metric]+=1
out=dict(complete=True,counts=dict(counts),seconds=time.perf_counter()-start,scope="Search-disabledfullstate/historynormalNative/Core replay, no newsearch/game/proof. SameCore/compiler/host; notWDL orhistoryclockauthentication.")
(B/"consumer-result.json").write_bytes((json.dumps(out,indent=2)+"\n").encode());print(json.dumps(out),flush=True)
