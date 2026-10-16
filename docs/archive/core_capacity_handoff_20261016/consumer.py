"""Search-disabled full-record/PV consumer for the capacity handoff evidence."""
from pathlib import Path
from copy import copy
from dataclasses import replace
import json,sys,time,collections
R=Path.cwd();B=Path(sys.argv[1]).resolve();sys.path[:0]=[str(R),str(R/'tests'),str(R/'tests/product')]
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.session.record import GameRecord
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove
from generic_chess.core.coordinates import Square
from generic_chess.core.identity import position_identity_key
from generic_chess.native import _module,semantic as sem,SemanticSearchEngine
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.mirror import expected_snapshot
from generic_chess.native.semantic_engine import _core_pv_leaf_dynamic_features
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from scripts.research_record import record_value
from test_native_q_history_deferral import cycle
from conftest import make_ruleset
from generic_chess import RuleAutomaticAdjudication
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.core.pieces import PieceType
assert Path(_module().__file__).resolve().is_relative_to(R.resolve())
def forbidden(*args,**kwargs):raise AssertionError('Consumer must not search')
SemanticSearchEngine.search=forbidden;AlphaBetaPlayer.choose_action=forbidden;_module().semantic_engine_search=forbidden
for n in('semantic_fixed_depth_search','semantic_probe_search','semantic_iterative_search','semantic_root_parallel_search'):
 if hasattr(_module(),n):setattr(_module(),n,forbidden)
for n in('fixed_depth_search','probe_search','semantic_iterative_search','root_parallel_search'):setattr(sem,n,forbidden)
class Adapter(CompiledSemanticRuleset):
 __slots__=()
 def __getattr__(self,n):return getattr(self._legacy_compiled,n)
 @property
 def semantic(self):return self
def facade(x):return Adapter(ir=x.ir,_legacy_compiled=x._legacy_compiled,support=x.support)
def read(name):return json.loads((B/name).read_bytes())
def action(x):
 if'from_square'in x:return SemanticBoardMove(x['pattern_id'],x['geometry_id'],x['actor_type_id'],Square(**x['from_square']),Square(**x['to_square']),x['promotion_target_id'])
 return SemanticDropMove(x['pattern_id'],x['geometry_id'],x['base_type_id'],Square(**x['to_square']))
counts=collections.Counter();cache={};start=time.perf_counter()
def compare(s,nr):
 counts['core_full_states']+=1
 if s.state.ply_count>1024:
  try:pack_semantic_search_position(s.compiled,nr,s)
  except NotImplementedError as exc:assert'history capacity'in str(exc);counts['explicit_core_only_capacity_states']+=1;return
  raise AssertionError('Native accepted past storage')
 p=pack_semantic_search_position(s.compiled,nr,s);snap=sem.snapshot(nr,p);want=expected_snapshot(s.state.position,nr,s.compiled)
 for k in('board','hands','aux_state','side'):assert record_value(snap[k])==record_value(want[k]),k
 assert snap['ply']==s.state.ply_count
 assert snap['history_exact']and snap['history_events_exact']
 assert[''.join(f'{v:016x}'for v in row)for row in snap['history']]==[str(position_identity_key(p,s.compiled))for p in s._search_witnesses]
 assert snap['history_events']==tuple((255 if e.actor<0 else e.actor,bool(e.gave_check))for e in s.state.history)
 assert sem.terminal_status(nr,p)=={'status':s.state.terminal_status.status.value,'winner':s.state.terminal_status.winner}
 counts['native_full_states']+=1
def query(s,nr,r,edges):
 s=copy(s);compare(s,nr)
 if r.get('action')is not None:assert action(r['action'])in s.legal_actions()
 line=r.get('principal_variation',[])
 for i,item in enumerate(line):
  a=action(item);assert a in s.legal_actions();s.submit(a);compare(s,nr);assert record_value(s.state)==edges[i]['state'];counts['pv_edges']+=1
 if line and'dynamic_features'in r:
  assert list(_core_pv_leaf_dynamic_features(s,()))==r['dynamic_features'];counts['result_feature_vectors']+=1
 counts['retained_query_receipts']+=1
def root(kind,seed,h):
 key=(kind,seed,h)
 if key not in cache:
  d=read(f'{kind}-roots/{seed}.json');c=facade(compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(d['rulesets'][str(h)]))));s=GameSession.replay(c,deserialize_game_record(json.dumps(d['records'][str(h)])));assert record_value(s.state)==d['states'][str(h)];cache[key]=(s,compile_native_semantic_rules(c))
 s,nr=cache[key];return copy(s),nr
for kind in('portability','admission'):
 d=read(kind+'-results.json')
 for z in d['rows']:
  if z['kind']!='ACTUAL_QUERY':counts[kind+':'+z['kind']]+=1;continue
  h=2048 if '2048' in z['arm'] else 1024;s,nr=root(kind,z['seed'],h);query(s,nr,z['result'],z['pv_edges']);counts[kind+'_receipts']+=1
for z in read('rule-horizon-results.json')['rows']:
 s,nr=root('portability',z['seed'],2048);query(s,nr,z['result'],z['pv_edges']);counts['private_rule_receipts']+=1
for name in('boundary-results.json','postfix-boundary-results.json'):
 for d in read(name)['roots']:
  x=cycle(max_ply=1024,repetition=10000);c=facade(x.compiled);s=GameSession.replay(c,deserialize_game_record(json.dumps(d['record'])));nr=compile_native_semantic_rules(c);assert record_value(s.state)==d['state']
  for z in read(name)['rows']:
   if z['prefix']!=d['prefix']:continue
   if z['kind']=='ACTUAL_QUERY':query(s,nr,z['result'],z['pv_edges'])
   else:counts['preserved_baseline_caller_failures']+=1
for d in read('results.json')['rows']:
 x=cycle(max_ply=2048,repetition=10000);c=facade(x.compiled);s=GameSession.replay(c,deserialize_game_record(json.dumps(d['record'])));nr=compile_native_semantic_rules(c);assert record_value(s.state)==d['state'];query(s,nr,d['core'],d['pv_edges']);counts['old_compile_refusal_receipts']+=1
k=PieceType('K','Anchor',(LeapAtom((1,0)),LeapAtom((-1,0))),is_anchor=True);r=PieceType('R','Checker',(RayAtom((0,1)),LeapAtom((1,0)),LeapAtom((-1,0))))
rules=replace(make_ruleset(4,[k,r],['..k.','.R..','....','K...'],max_ply=3,repetition_limit=10000),automatic_adjudications=(RuleAutomaticAdjudication('opaque',1),));c=facade(compile_legacy_ruleset_for_semantic_execution(rules));nr=compile_native_semantic_rules(c)
for d in read('pending-results.json')['rows']:
 s=GameSession.replay(c,deserialize_game_record(json.dumps(d['record'])));assert record_value(s.state)==d['state'];query(s,nr,d['core'],d['pv_edges'])
 if'native'in d:
  ss=copy(s);edges=[]
  for item in d['native']['principal_variation']:ss.submit(action(item));edges.append({'state':record_value(ss.state)})
  query(s,nr,d['native'],edges)
 else:counts['preserved_pending_capacity_refusals']+=1
for d in read('rule-horizon-results.json')['capacity']:
 # This producer saved exact dataclass fields, not the public JSON transport.
 # Rebuild that immutable public GameRecord without changing the saved bytes.
 raw=d['record'];assert raw['declaration'] is None
 record=GameRecord(schema_version=raw['schema_version'],ruleset_fingerprint=raw['ruleset_fingerprint'],actions=tuple(action(a)for a in raw['actions']),resigned_by=raw['resigned_by'],declaration=None,initial_setup_key=raw['initial_setup_key']);assert record_value(record)==raw
 x=cycle(max_ply=2048,repetition=10000);c=facade(x.compiled);s=GameSession.replay(c,record);nr=compile_native_semantic_rules(c);assert record_value(s.state)==d['state'];compare(s,nr)
 if'result'in d:
  ss=copy(s);edges=[]
  for item in d['result']['principal_variation']:ss.submit(action(item));edges.append({'state':record_value(ss.state)})
  query(s,nr,d['result'],edges)
 else:counts['private_capacity_refusals']+=1
for d in read('hybrid-results.json')['roots']:
 x=cycle(max_ply=2048,repetition=10000);c=facade(x.compiled);s=GameSession.replay(c,deserialize_game_record(json.dumps(d['record'])));nr=compile_native_semantic_rules(c);assert record_value(s.state)==d['state']
 for z in read('hybrid-results.json')['rows']:
  if z['prefix']==d['prefix']:query(s,nr,z['result'],z['pv_edges']);counts['hybrid_receipts']+=1
out={'complete':True,'counts':dict(counts),'seconds':time.perf_counter()-start,'scope':'FreshnormalrebuiltNative/Core searchDISABLED publicrecord/state/history/PV/resultfeature replay. Priorclock/finiteobjective notrerun; privateprototype historicalreceipts verifiedwithfinalCore, notclaimedprivatekernelreproduction. Core/compiler/hostshared, noAUXexecution orall-domainproof.'}
(B/'consumer-result.json').write_bytes(json.dumps(out,indent=2).encode());print(json.dumps(out,indent=2))
