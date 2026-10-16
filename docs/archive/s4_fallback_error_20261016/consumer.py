"""Search-disabled consumer: exact state/PV/field receipts, not old clocks/WDL."""
from pathlib import Path
from dataclasses import replace,fields
from copy import copy
import sys,json,collections,time
R=Path.cwd();B=Path(sys.argv[1]).resolve();sys.path[:0]=[str(R),str(R/'tests'),str(R/'tests/product')]
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.core.position import Hands
from generic_chess.core.pieces import Piece
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove
from generic_chess.core.coordinates import Square
from generic_chess.core.transition import initial_state
from generic_chess.core.identity import position_identity_key
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.native import _module,semantic as sem,SemanticSearchEngine
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.mirror import expected_snapshot
from generic_chess.native.semantic_engine import SemanticIterativeSearchResult
from scripts.research_record import record_value
assert Path(_module().__file__).resolve().is_relative_to(R.resolve())
def forbidden(*a,**k):raise AssertionError('Reader cannot search')
SemanticSearchEngine.search=forbidden;AlphaBetaPlayer.choose_action=forbidden
for name in('semantic_engine_search','semantic_fixed_depth_search','semantic_probe_search','semantic_iterative_search','semantic_root_parallel_search'):
 if hasattr(_module(),name):setattr(_module(),name,forbidden)
for name in('fixed_depth_search','probe_search','semantic_iterative_search','root_parallel_search'):setattr(sem,name,forbidden)
class Adapter(CompiledSemanticRuleset):
 __slots__=()
 def __getattr__(self,n):return getattr(self._legacy_compiled,n)
 @property
 def semantic(self):return self
counts=collections.Counter();start=time.perf_counter()
def read(name):return json.loads((B/'research'/name).read_bytes())
def action(x):
 if 'from_square'in x:return SemanticBoardMove(x['pattern_id'],x['geometry_id'],x['actor_type_id'],Square(**x['from_square']),Square(**x['to_square']),x['promotion_target_id'])
 return SemanticDropMove(x['pattern_id'],x['geometry_id'],x['base_type_id'],Square(**x['to_square']))
def compare(s,n):
 p=pack_semantic_search_position(s.compiled,n,s);raw=sem.snapshot(n,p);wanted=expected_snapshot(s.state.position,n,s.compiled)
 for key in('board','hands','aux_state','side'):assert record_value(raw[key])==record_value(wanted[key]),key
 assert raw['ply']==s.state.ply_count and raw['history_exact']and raw['history_events_exact']
 assert [''.join(f'{v:016x}'for v in row)for row in raw['history']]==[str(position_identity_key(w,s.compiled))for w in s._search_witnesses]
 assert raw['history_events']==tuple((255 if h.actor<0 else h.actor,bool(h.gave_check))for h in s.state.history)
 assert sem.terminal_status(n,p)=={'status':s.state.terminal_status.status.value,'winner':s.state.terminal_status.winner}
 counts['full_core_native_states']+=1;return p
keys={f.name for f in fields(SemanticIterativeSearchResult)}
def query(s,n,r,edges=None):
 assert set(r)==keys
 counts['full_result_receipts']+=1
 if r['action']is not None:assert action(r['action'])in s.legal_actions()
 current=copy(s);compare(current,n)
 for index,item in enumerate(r['principal_variation']):
  a=action(item);assert a in current.legal_actions();current.submit(a);p=compare(current,n)
  if edges is not None:assert record_value(current.state)==edges[index]['state']
  counts['pv_edges']+=1
 if r['principal_variation']:
  assert list(sem.dynamic_features(n,p))==r['dynamic_features'];counts['leaf_vectors']+=1
# Imported Position S4 controls deliberately have no reachable-history claim.
rows=[[None]*9 for _ in range(9)];rows[0][4]=Piece(0,'K','K');rows[8][4]=Piece(1,'K','K')
c=compile_ruleset_for_execution(replace(build_builtin_ruleset('standard_shogi'),max_ply=2048,initial_position=tuple(map(tuple,rows))))
p=replace(initial_state(c).position,hands=(Hands((('P',1),)),Hands()));provider=NativeSemanticLegalityProvider.try_create(c,strict=True);assert provider;e=semantic_engine_for(c);expected=set(e.legal_actions(p));assert len(expected)==read('results.json')['core_actions']==76
for z in read('results.json')['rows']:
 packed=sem.pack_position(provider.native_rules,provider._state_only_payload(p,z['ply']));raw=sem.transient_legal_actions_audit(provider.native_rules,packed);assert record_value(raw)==z['audit'];assert {b[1][0]for b in provider(p,z['ply'])}==expected;assert provider.supports_position(p,z['ply'])==z['supported'];counts['s4_action_sets']+=1
for z in read('child-results.json')['rows']:
 packed=sem.pack_position(provider.native_rules,provider._state_only_payload(p,z['ply']))
 a=next(a for a in sem.transient_legal_actions(provider.native_rules,packed)if record_value(provider._decode_action(a,p))==z['action'])
 semantic=provider._decode_action(a,p);assert record_value(e.apply(p,semantic))==z['core'];assert record_value(sem.snapshot(provider.native_rules,sem.make_checked(provider.native_rules,packed,a)))==z['native'];counts['position_only_children']+=1
for z in read('cold-results.json')['rows']:
 c=compile_ruleset_for_execution(replace(build_builtin_ruleset(z['game']),max_ply=z['rule_horizon']));s=GameSession(c);n=compile_native_semantic_rules(c);query(s,n,z['result'])
d=read('cancel-results.json');assert len(d['rows'])==d['actual_queries']==36 and d['planned_slots']==36;roots={}
for z in d['roots']:
 assert z['kind']=='ACTUAL_ONGOING'
 x=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(z['ruleset'])));c=Adapter(ir=x.ir,_legacy_compiled=x._legacy_compiled,support=x.support);s=GameSession.replay(c,deserialize_game_record(json.dumps(z['record'])));assert record_value(s.state)==z['initial'];n=compile_native_semantic_rules(c);compare(s,n);roots[z['seed']]=(s,n);counts['actual_acquisition_edges']+=len(s.to_record().actions)
for z in d['rows']:
 assert z['kind']=='ACTUAL_QUERY';s,n=roots[z['seed']];query(s,n,z['result'],z['pv_edges'])
for filename,final in(('fallback-baseline.json',False),('fallback-final.json',True)):
 d=read(filename);c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'));s=GameSession.replay(c,deserialize_game_record(json.dumps(d['record'])));assert record_value(s.state)==d['initial'];n=compile_native_semantic_rules(c)
 for z in d['rows']:
  query(s,n,z['result']);assert z['counts'][1]==1
  if final:assert z['result']['termination_reason']=='internal_error'and z['result']['action']is None and not z['result']['used_fallback']
  else:assert z['result']['termination_reason']=={'cancel':'cancelled','nodes':'node_budget','time':'time_budget','depth_zero':'completed'}[z['stop']]and z['result']['action']is not None
  counts['final_fault_receipts'if final else'baseline_fault_receipts']+=1
# Later exposed-root attribution/prototype panels reuse these same12 roots.
for folder,filename in (("key-attribution","results.json"),
                        ("stream-key","pilot-results.json"),
                        ("isolated-mixed-leaf","pilot-results.json")):
 d=read(folder+"/"+filename)
 for z in d["rows"]:
  current,native=roots[z["seed"]];query(current,native,z["result"],z["pv_edges"])
  counts[folder+"_query_receipts"]+=1
# Fresh transfer has its own records and exposure tier, including real tails.
d=read("isolated-mixed-leaf/transfer-results.json");transfer_roots={}
for z in d["roots"]:
 if z["kind"]=="ACTUAL_ROOT_FAILURE":
  counts["retained_transfer_root_failures"]+=1;continue
 x=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(z["ruleset"])));c=Adapter(ir=x.ir,_legacy_compiled=x._legacy_compiled,support=x.support);s=GameSession.replay(c,deserialize_game_record(json.dumps(z["record"])));assert record_value(s.state)==z["state"];n=compile_native_semantic_rules(c);compare(s,n);transfer_roots[z["seed"]]=(s,n);counts["transfer_acquisition_edges"]+=len(s.to_record().actions)
 if z["kind"]=="ACTUAL_TERMINAL_TAIL":counts["actual_transfer_tails"]+=1
for z in d["rows"]:
 assert z["kind"]=="ACTUAL_QUERY";s,n=transfer_roots[z["seed"]];query(s,n,z["result"],z["pv_edges"]);counts["transfer_query_receipts"]+=1
assert len(d["rows"])==d["actual_queries"]
counts["transfer_missing_slots"]=d["planned_slots"]-d["actual_queries"]
# The authoritative PENDING record and deliberately insufficient import differ.
from test_native_pending_continuation import session_after
s=session_after(("e2e4","d7d5","f1b5"));n=compile_native_semantic_rules(s.compiled);baseline=read("public-status-baseline.json");final=read("public-status-final.json");assert record_value(s.state)==baseline["root"]==final["root"];full=compare(s,n);short=sem.pack_current_position(n,s.state.position,ply_count=s.state.ply_count);candidate=sem.candidate_actions(n,short);selected=next(iter(sem.guarded_actions(n,full)))
operations={"guarded":lambda:sem.guarded_actions(n,short),"guarded_audit":lambda:sem.guarded_actions_audit(n,short),"transient":lambda:sem.transient_legal_actions(n,short),"transient_audit":lambda:sem.transient_legal_actions_audit(n,short),"subset":lambda:sem.transient_legal_subset(n,short,candidate),"checked":lambda:sem.make_checked(n,short,selected)}
for z in final["rows"]:
 assert z["error_type"]=="RuntimeError"
 try:operations[z["path"]]()
 except RuntimeError as exc:assert "required checked transition"in str(exc);counts["explicit_public_history_refusals"]+=1
 else:raise AssertionError("Missinghistory becamepartiallegality")
assert len(sem.guarded_actions(n,full))==baseline["full_legal_actions"]
print(json.dumps({'counts':dict(counts),'seconds':time.perf_counter()-start,'scope':'Current-source build, all search functions disabled. Original cancellation clocks, faults and scores not independently rerun. Position-only S4 distinct from actual full-history query states.'},indent=2))
