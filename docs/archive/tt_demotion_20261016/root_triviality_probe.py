"""Search-disabled consumer. Run from product source root; pass evidence directory."""
from pathlib import Path
import sys,json,time,hashlib
R=Path.cwd();sys.path.insert(0,str(R));B=Path(sys.argv[1])if len(sys.argv)>1 else R/'.local_agent/tt-demotion-20261016'
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.ir import CompiledSemanticRuleset
class Adapter(CompiledSemanticRuleset):
 __slots__=()
 def __getattr__(self,name):return getattr(self._legacy_compiled,name)
 @property
 def semantic(self):return self
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove,PassAction
from generic_chess.core.coordinates import Square
from generic_chess.core.identity import position_identity_key
from generic_chess.core.transition import apply_action
from generic_chess.core.movegen import iter_legal_actions
from generic_chess.native import compiler as nc,semantic as sem,SemanticSearchEngine,_module
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.mirror import expected_snapshot,pack_semantic_action
from scripts.research_record import record_value
assert Path(nc.__file__).resolve().is_relative_to(R.resolve())
assert Path(_module().__file__).resolve().is_relative_to(R.resolve())
assert Path(compile_legacy_ruleset_for_semantic_execution.__code__.co_filename).resolve().is_relative_to(R.resolve())
def forbidden(*a,**kw):raise AssertionError('Search forbidden in receipt consumer')
SemanticSearchEngine.search=forbidden;_module().semantic_engine_search=forbidden
def read(p):return json.loads((B/p).read_bytes())
def action(d):
 if d is None:return None
 if not d:return PassAction()
 if 'from_square'in d:return SemanticBoardMove(d['pattern_id'],d['geometry_id'],d['actor_type_id'],Square(**d['from_square']),Square(**d['to_square']),d['promotion_target_id'])
 return SemanticDropMove(d['pattern_id'],d['geometry_id'],d['base_type_id'],Square(**d['to_square']))
def digest(state):return hashlib.sha256(json.dumps(record_value(state),sort_keys=True).encode()).hexdigest()
cache={};root_states=set();counts=dict(root_loads=0,queries=0,pv_edges=0,physical_games=0,physical_edges=0,one_reply_receipts=0,selected_choice_edges=0)
def load(root):
 key=str(root)
 if key not in cache:
  d=read('roots/'+key+'.json');raw=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(d['ruleset'])));c=Adapter(ir=raw.ir,_legacy_compiled=raw._legacy_compiled,support=raw.support);nr=nc.compile_native_semantic_rules(c);cache[key]=(d,c,nr);counts['root_loads']+=1
 d,c,nr=cache[key];s=GameSession.replay(c,deserialize_game_record(json.dumps(d['game_record'])))
 assert record_value(s.state)==d['state']and digest(s.state)==d['before_sha256']
 root_states.add(digest(s.state));return s,nr
def compare(s,nr,state,np,witnesses):
 snap=sem.snapshot(nr,np);exp=expected_snapshot(state.position,nr,s.compiled)
 for k in('board','hands','aux_state','side'):assert record_value(snap[k])==record_value(exp[k])
 assert [''.join(f'{v:016x}'for v in h)for h in snap['history']]==[str(position_identity_key(w,s.compiled))for w in witnesses]
 assert snap['history_events']==tuple((255 if e.actor<0 else e.actor,bool(e.gave_check))for e in state.history)
 assert sem.terminal_status(nr,np)==dict(status=state.terminal_status.status.value,winner=state.terminal_status.winner)
def query(s,nr,r,limit=1000000):
 assert r['nodes']>=0 and r['qnodes']>=0 and r['nodes']+r['qnodes']<=limit
 st=s.state;np=pack_semantic_search_position(s.compiled,nr,s);w=list(s._search_witnesses)
 chosen=action(r['action']);assert chosen is None or chosen in s.legal_actions()
 line=[action(a)for a in r['principal_variation']];had_pv=bool(line)
 if line:assert line[0]==chosen
 if not line and chosen is not None:line=[chosen]
 for a in line:
  np=sem.make_checked(nr,np,pack_semantic_action(nr,st.position,a));st=apply_action(st,a,s.compiled);w.append(st.position);compare(s,nr,st,np,w);counts['pv_edges']+=int(had_pv);counts['selected_choice_edges']+=int(not had_pv)
 if r.get('immediate_win')and r.get('result_source')=='verified_root_child':assert len(line)==1 and st.terminal_status.winner==s.state.position.side_to_move
 counts['queries']+=1
 return st,np



import os
mode=sys.argv[2]if len(sys.argv)>2 else"probe"
plan=dict(question="Do literal one-move physical wins waste enough root quota or compute to justify a FUTURE before-input playability filter?",premise="The closed finite panels contain one-move cases, and AUX66 distinguishes trivial samplequota from negligiblecompute. This measures ALLexisting52planned roots without discarding/refitting any study.",scope="Exposed root-mu diagnosis, not initial-setup distribution or all-domainWDL. Complete state/history, promotion/drop/aux maintained; no solver/learner/newgames/defaultfilter.",whole_seconds=300,root_seconds=8,expected_seconds=90)
if mode=="probe":
 (B/"root-triviality-plan.json").write_bytes(json.dumps(plan,indent=2).encode())
 rows=[];start=time.perf_counter();journal=B/"root-triviality-rows.jsonl";journal.open("x").close()
 for folder in("finite","witness_finite","prospective"):
  inputs=read(folder+"/plan.json")["inputs"]
  for case in inputs:
   row=dict(folder=folder,**case,actions=[],complete=False);path=B/folder/"roots"/(str(case["seed"])+".json");t=time.perf_counter()
   if not path.exists():row["kind"]="ACTUAL_MISSING_TARGET_TERMINAL_TAIL"
   elif time.perf_counter()-start>=300:row["kind"]="WHOLE_CAP_NOT_STARTED_UNKNOWN"
   else:
    s,nr=load("../"+folder+"/roots/"+str(case["seed"]));np=pack_semantic_search_position(s.compiled,nr,s);mapping={pack_semantic_action(nr,s.state.position,a):a for a in s.legal_actions()};native_actions=set(sem.guarded_actions(nr,np));assert set(mapping)==native_actions
    row["legal_actions"]=len(mapping);row["side"]=s.state.position.side_to_move;row["winning_actions"]=0;row["kind"]="ACTUAL_FRONTIER"
    for packed in sorted(mapping):
     if time.perf_counter()-t>=8 or time.perf_counter()-start>=300:break
     ac=mapping[packed];child=apply_action(s.state,ac,s.compiled);cp=sem.make_checked(nr,np,packed);compare(s,nr,child,cp,list(s._search_witnesses)+[child.position])
     won=child.terminal_status.winner==s.state.position.side_to_move and child.terminal_status.status.value!="ongoing"
     row["winning_actions"]+=int(won);row["actions"].append(dict(packed=packed,action=record_value(ac),after_sha256=digest(child),terminal=record_value(child.terminal_status),own_win=won))
    row["complete"]=len(row["actions"])==len(mapping)
   row["seconds"]=time.perf_counter()-t;rows.append(row)
   with journal.open("a",encoding="utf-8",newline="\n")as f:f.write(json.dumps(row)+"\n");f.flush();os.fsync(f.fileno())
   print("ROOT_FRONTIER",folder,case,len(row["actions"]),row.get("winning_actions"),row["complete"],flush=True)
 out=dict(complete=True,planned_roots=52,rows=rows,seconds=time.perf_counter()-start,rule="Any observed ownwin is trivial even on partialfrontier; zero-win eligible only when complete. Missing/partialstayUNKNOWN; no existing rootfiltered.")
 (B/"root-triviality.json").write_bytes(json.dumps(out,indent=2).encode())
else:
 out=read("root-triviality.json");assert out["complete"]and len(out["rows"])==52;verified=0
 for row in out["rows"]:
  if row["kind"]!="ACTUAL_FRONTIER":continue
  s,nr=load("../"+row["folder"]+"/roots/"+str(row["seed"]));np=pack_semantic_search_position(s.compiled,nr,s);mapping={pack_semantic_action(nr,s.state.position,a):a for a in s.legal_actions()}
  for ar in row["actions"]:
   ac=mapping[ar["packed"]];assert record_value(ac)==ar["action"];child=apply_action(s.state,ac,s.compiled);cp=sem.make_checked(nr,np,ar["packed"]);compare(s,nr,child,cp,list(s._search_witnesses)+[child.position]);assert digest(child)==ar["after_sha256"]and record_value(child.terminal_status)==ar["terminal"];verified+=1
  if row["complete"]:assert set(mapping)=={a["packed"]for a in row["actions"]}
 receipt=dict(complete=True,roots=52,full_child_states=verified,search_forbidden=True,scope="Late direct-Git addon replay, separate from sealed3126query/60game consumer. SharedCore/compiler/host, no new search/game/proof or independentWDL.")
 (B/"root-triviality-replay.json").write_bytes(json.dumps(receipt,indent=2).encode());print("ROOT_ADDON_REPLAY",receipt,flush=True)
