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

# New24consumercontrols: exacttrace/pair/order replay, no search or new cost assay.
d=read('consumer-isolation/results.json');setup=read('consumer-isolation/setup.json')
assert len(d['rows'])==24 and all(x['all_non_time_equal'] and x['all_probe_values_vectors_and_sorted_order_equal']for x in d['summary']['pairs'])
from test_native_q_history_deferral import cycle
from test_native_dynamic_feature_views import reference_features
from generic_chess.learning.features import localized_control_features
sessions={'cycle':cycle(max_ply=2048,repetition=10000,prefix=8)}
z=setup['source_hybrid'];x=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(z['ruleset'])));c=Adapter(ir=x.ir,_legacy_compiled=x._legacy_compiled,support=x.support);sessions['hybrid']=GameSession.replay(c,deserialize_game_record(json.dumps(z['record'])))
for root,current in sessions.items():
 nr=compile_native_semantic_rules(current.compiled);packed=compare(current,nr)
 dynamic=reference_features(current.compiled,current.state.position);nine=localized_control_features(current.state.position,current.compiled)
 assert list(dynamic)==next(row['vector']for row in setup['rows']if row['root']==root)
 for row in d['rows']:
  if row['root']!=root:continue
  if row['kind']=='compact_ordering':query(current,nr,row['result']);counts['new_order_search_receipts']+=1;continue
  raw=sem.snapshot(nr,packed);side=raw['side'];mat=sum((1 if piece[2]==side else -1)*(piece[1]+1)for piece in raw['board']if piece is not None)
  # Snapshot piece tuple is base/current/owner/promoted; exact field layout checked below.
  mat+=sum((1 if owner==side else -1)*(typ+1)*number for owner,hand in enumerate(raw['hands'])for typ,number in enumerate(hand))
  expected=mat+(1 if side==0 else -1)*(sum(w*v for w,v in zip(row['dynamic_values'],dynamic))+sum(w*v for w,v in zip(row['control_values'],nine)))
  expected=max(-90000000,min(90000000,expected));assert expected==row['value'],(root,expected,row['value'])
  assert sem.evaluate(nr,packed,dynamic_values=row['dynamic_values'],localized_control_values=row['control_values'])==expected
  counts['new_precomputed_leaf_receipts']+=1
for i in range(0,24,2):
 a,b=d['rows'][i:i+2];ta=[list(t)for t in a['trace']];tb=[list(t)for t in b['trace']]
 for t in ta+tb:t[1]=0
 assert ta==tb;counts['new_trace_pairs']+=1
 for row in(a,b):
  batch=[]
  for t in row['trace']:
   if t[0]!=2:continue
   if t[3]==0:
    if batch:
     assert len(batch)==batch[0][4];assert[(x[5],x[6])for x in batch]==sorted([(x[5],x[6])for x in batch],key=lambda x:(-x[0],x[1]));counts['new_sorted_batches']+=1
    batch=[]
   batch.append(t)
  if batch:
   assert len(batch)==batch[0][4];assert[(x[5],x[6])for x in batch]==sorted([(x[5],x[6])for x in batch],key=lambda x:(-x[0],x[1]));counts['new_sorted_batches']+=1
print(json.dumps({'combined_counts':dict(counts),'scope':'Search disabled; state/feature/score/order records verified. Twelve new directproduct leaf calls are restorationqualification, not originalprecomputedAPI or oldclocks. No search/teacher/WDL/externalAgentexecution.'},indent=2))

# Follow-on experiments replay on adopted normalproduct; no private search executed.
from generic_chess.learning.material import LearnableMaterialCheckpoint
from test_native_dynamic_feature_views import reference_features
from generic_chess.learning.features import localized_control_features
import math
pilot=read('root-scout/pilot-results.json');pilot_roots=read('root-scout/roots.json');scout_sessions={'cycle2':cycle(max_ply=2048,repetition=4,prefix=2),'cycle8':cycle(max_ply=2048,repetition=4,prefix=8),'pending':session_after(('e2e4','d7d5','f1b5'))}
for seed,z in pilot_roots['existing_hybrid_source'].items():
 x=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(z['ruleset'])));c=Adapter(ir=x.ir,_legacy_compiled=x._legacy_compiled,support=x.support);scout_sessions[seed]=GameSession.replay(c,deserialize_game_record(json.dumps(z['record'])))
for key,current in scout_sessions.items():assert record_value(current.state)==pilot_roots['actual_roots'][key]
scout_ns={key:compile_native_semantic_rules(current.compiled)for key,current in scout_sessions.items()}
for row in pilot['rows']:query(scout_sessions[row['root']],scout_ns[row['root']],row['result']);counts['scout_pilot_receipts']+=1
fresh=read('root-scout-v2/transfer-results.json');fresh_instances={}
for z in fresh['roots']:
 assert z['kind']=='ACTUAL_ONGOING';x=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(z['ruleset'])));c=Adapter(ir=x.ir,_legacy_compiled=x._legacy_compiled,support=x.support);current=GameSession.replay(c,deserialize_game_record(json.dumps(z['record'])));assert record_value(current.state)==z['state'];n=compile_native_semantic_rules(c);compare(current,n);fresh_instances[z['seed']]=(current,n);counts['scout_fresh_acquisition_edges']+=len(current.to_record().actions)
for row in fresh['rows']:
 assert row['kind']=='ACTUAL_QUERY';current,n=fresh_instances[row['seed']];query(current,n,row['result'],row['pv_edges']);counts['scout_fresh_receipts']+=1
for row in read('check-attribution/results.json')['rows']:
 current,n=roots[row['seed']];query(current,n,row['result'],row['pv_edges']);counts['check_entry_receipts']+=1
compact=read('compact-required3/results.json');compact_instances={}
for z in compact['roots']:
 source=z['source'];x=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(source['ruleset'])));c=Adapter(ir=x.ir,_legacy_compiled=x._legacy_compiled,support=x.support);current=GameSession.replay(c,deserialize_game_record(json.dumps(source['record'])));assert record_value(current.state)==source['initial'];n=compile_native_semantic_rules(c);cp=LearnableMaterialCheckpoint.from_dict(z['checkpoint']);compact_instances[z['seed']]=(current,n,cp)
for row in compact['rows']:
 current,n,cp=compact_instances[row['seed']]
 if row['kind']=='EXPLICIT_FAILURE_OR_REFUSAL':
  try:SemanticSearchEngine(current.compiled,n,checkpoint=cp,ordering_checkpoint=cp,tt_megabytes=0,ordering_cache_enabled=False,ordering_feature_reuse_enabled=row['reuse'])
  except Exception as exc:assert type(exc).__name__==row['error_type']and str(exc)==row['error'];counts['compact_input_refusals']+=1
  else:raise AssertionError('Inputlimitrefusal disappeared')
  continue
 query(current,n,row['result']);counts['compact_query_receipts']+=1
 packed=compare(current,n);p=current.state.position;dynamic=reference_features(current.compiled,p);control=localized_control_features(p,current.compiled);model=cp.compact_nonlinear
 assert model['output_bias']==2.0 and model['output_weights'][0]==.125
 expected=(1 if p.side_to_move==0 else -1)*(round((2+.125*math.tanh(.01*dynamic[0]))*256)+sum(a*b for a,b in zip(cp.semantic_quantized_localized_control(),control)))
 actual=sem.evaluate(n,packed,board_values=cp.semantic_quantized_board(n.type_ids),hand_values=cp.semantic_quantized_hand(n.type_ids),dynamic_values=cp.semantic_quantized_dynamic(),localized_control_values=cp.semantic_quantized_localized_control(),compact_values=model,evaluator_scale=256)
 assert actual==expected,(actual,expected);counts['compact_Core_formula_leaf_checks']+=1
# Pure Corecontrols are actualrecords with adifferent publicresult schema, notNative.
current=scout_sessions['125201'];n=scout_ns['125201']
for row in read('root-scout/core-control-results.json')['rows']:
 rr=row['result'];assert rr['action']is None or action(rr['action'])in current.legal_actions();copy_session=copy(current);compare(copy_session,n)
 for item in rr['principal_variation']:
  a=action(item);assert a in copy_session.legal_actions();copy_session.submit(a);compare(copy_session,n);counts['pure_Core_control_PV_edges']+=1
 counts['pure_Core_control_receipts']+=1
print(json.dumps({'final_counts':dict(counts),'scope':'Adopted normalSOURCE; allsearch disabled. Scores/clocks/minimax/privatecandidateexecution NOTrepeated. Eightcompactleaf expressions independentlychecked usingCoremovement/featuresemantics andknownmanualformula, nottraining. Canonicalstate/PV transport isnotanoptimalvalueproof.'},indent=2))

# LateCoreinput/player receipts areverifiedwithoutsearchoroldclockexecution.
from generic_chess.learning.nonlinear import CompactNonlinearResidual,semantic_state_features
cp_root=next(z for z in compact['roots']if z['seed']==125601);current,n,cp=compact_instances[125601];model=CompactNonlinearResidual.from_dict(cp.compact_nonlinear)
for row in read('consumer-isolation/compact-Core-input-results.json')['rows']:
 if row['label']=='first_legal_child':current.submit(sorted(current.legal_actions(),key=repr)[0])
 assert record_value(current.state)==row['state'];packed=compare(current,n);dynamic=reference_features(current.compiled,current.state.position);assert dynamic==tuple(row['vector'])==sem.dynamic_features(n,packed);features=semantic_state_features(current.state.position,current.compiled,dynamic);assert len(features)==5145;assert abs(float(model.predict(features[None,:])[0])-row['prediction'])<1e-12;counts['late_Core_input_controls']+=1
current,n,cp=compact_instances[125601]
# Reconstructoriginalparent, sinceaboveactuallyplayeditsonecontrolchild.
z=cp_root['source'];x=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(z['ruleset'])));cc=Adapter(ir=x.ir,_legacy_compiled=x._legacy_compiled,support=x.support);current=GameSession.replay(cc,deserialize_game_record(json.dumps(z['record'])));n=compile_native_semantic_rules(cc)
late=[read('consumer-isolation/compact-Core-player-results.json')]+read('Core-shared-input/results.json')['rows']
for row in late:
 result=row['result'];assert result['completed_depth']==0 and result['termination_reason']in('time_limit','node_limit');assert action(result['action'])in current.legal_actions();assert not result['principal_variation'];counts['late_Core_player_receipts']+=1
assert len(current.legal_actions())==read('Core-shared-input/root-degree.json')['core_legal_actions']==320
print(json.dumps({'late_counts':dict(counts),'scope':'Latefullstate/5145input/formula/fallbackreceipts checked, NOsearch orclockrerun. FrozenD1infeasibilityretained, nocompletedD1/DRAWinference.'},indent=2))
