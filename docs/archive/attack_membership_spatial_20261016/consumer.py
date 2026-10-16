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
  if kind=='pending':s=session_after(('e2e4','d7d5','f1b5','c7c6'))
  elif kind=='cycle':
   s=cycle(max_ply=1024,repetition=10000,prefix=0);h=next(x for x in read('control-results.json')['histories']if x['prefix']==seed);s=GameSession.replay(s.compiled,deserialize_game_record(json.dumps(h['game_record'])))
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

for fn in ('results.json','pilot-results.json','transfer-results.json','final-pilot-results.json','cold-query-results.json','cold-cpu-results.json'):
 for row in read(fn)['rows']:
  if row.get('kind','ACTUAL_QUERY')!='ACTUAL_QUERY':counts[row['kind']]+=1;continue
  query('transfer'if fn=='transfer-results.json'else'old',row['seed'],row['result']);counts[fn]+=1
for fn in('membership-control-results.json','final-control-results.json'):
 for row in read(fn)['queries']:query('pending',0,row['result']);counts[fn]+=1
for row in read('core-results.json')['rows']:
 if row['kind']!='ACTUAL_PAIR':counts['core_'+row['kind']]+=1;continue
 for arm in('core','native'):query('transfer',row['seed'],row[arm]);counts['core_'+arm+'_query_receipts']+=1
corpus=dict(semantic_corpus());rules={};controls=read('control-results.json');origins={}
for row in controls['mechanisms']:
 name=row['fixture'];c=corpus[name]
 if name not in rules:rules[name]=compile_native_semantic_rules(c)
 nr=rules[name];s=GameSession.replay(c,deserialize_game_record(json.dumps(row['game_record'])));assert record_value(s.state)==row['state'];np=pack_semantic_search_position(c,nr,s);compare(s,nr,np);assert list(sem.dynamic_features(nr,np))==row['features'];counts['mechanism_feature_positions']+=1;origins[(name,row['seed'],row['ply'])]=s
for row in read('final-control-results.json')['checked_edges']:
 s=copy(origins[(row['fixture'],row['seed'],row['ply'])]);nr=rules[row['fixture']];np=pack_semantic_search_position(s.compiled,nr,s);ac=action(row['action']);assert ac in s.legal_actions();np=sem.make_checked(nr,np,pack_semantic_action(nr,s.state.position,ac));s.submit(ac);assert record_value(s.state)==row['child'];compare(s,nr,np);counts['separately_recorded_legal_children']+=1
for row in read('final-control-results.json')['histories']:
 s=cycle(max_ply=1024,repetition=10000,prefix=row['prefix']);nr=compile_native_semantic_rules(s.compiled);np=pack_semantic_search_position(s.compiled,nr,s);compare(s,nr,np)
 if row['errors']:
  try:sem.dynamic_features(nr,np)
  except NotImplementedError as exc:assert 'history capacity'in str(exc)and'Core'in str(exc);counts['full_capacity_refusals']+=1
  else:raise AssertionError('capacity must refuse')
 else:assert list(sem.dynamic_features(nr,np))==row['features']['membership']
 counts['actual_history_prefixes']+=1
for row in read('transfer-results.json')['roots']:
 s,nr=root('transfer',row['seed']);compare(s,nr,pack_semantic_search_position(s.compiled,nr,s));counts['transfer_root_receipts']+=1

for fn in('consumer-results.json','leaf-pilot-results.json'):
 for row in read(fn)['rows']:query('old',row['seed'],row['result']);counts[fn]+=1
for row in read('spatial-transfer-results.json')['rows']:
 if row.get('kind')!='ACTUAL_QUERY':counts['spatial_'+row['kind']]+=1;continue
 query('spatial',row['seed'],row['result']);counts['spatial_transfer_query_receipts']+=1
for row in read('spatial-fixed-node-results.json')['rows']:
 query('old',row['seed'],row['result']);counts['spatial_fixednode_query_receipts']+=1
for row in read('spatial-component-results.json')['rows']:
 s,nr=root('old',row['seed']);np=pack_semantic_search_position(s.compiled,nr,s);assert record_value(sem.spatial_features(nr,np))==row['features'];counts['spatial_exposed_component_vectors']+=1
for row in read('spatial-controls.json')['states']:
 s=copy(origins[(row['fixture'],row['seed'],row['ply'])]);nr=rules[row['fixture']];np=pack_semantic_search_position(s.compiled,nr,s);assert record_value(sem.spatial_features(nr,np))==row['features'];compare(s,nr,np);counts['spatial_mechanism_vectors']+=1
for row in read('spatial-controls.json')['transport']:
 payload=next(r['payload']for r in controls['transport']if r['label']==row['label']);s,nr=root('pending',0);np=sem.pack_position(nr,payload);assert record_value(sem.spatial_features(nr,np))==row['features']['candidate'];counts['spatial_history_transport_vectors']+=1
for row in read('spatial-controls.json')['histories']:
 s=cycle(max_ply=1024,repetition=10000,prefix=row['prefix']);nr=compile_native_semantic_rules(s.compiled);np=pack_semantic_search_position(s.compiled,nr,s)
 if row.get('errors'):
  try:sem.spatial_features(nr,np)
  except NotImplementedError as exc:assert'Core'in str(exc)and'history capacity'in str(exc);counts['spatial_full_capacity_refusals']+=1
  else:raise AssertionError('spatialcapacitymustrefuse')
 else:assert record_value(sem.spatial_features(nr,np))==row['features']['candidate']
 counts['spatial_actual_history_prefixes']+=1
for row in read('spatial-transfer-results.json')['roots']:
 s,nr=root('spatial',row['seed']);compare(s,nr,pack_semantic_search_position(s.compiled,nr,s));counts['spatial_root_receipts']+=1
out=dict(complete=True,counts=dict(counts),seconds=time.perf_counter()-start,scope='SearchDISABLED normal source-bound Native/Core fullstate/history receipt reader. No raw query/clock/proof/fitness producers invoked. Originalconstructor transfer vs finalconstructor execution tiers retained. Corefinite receipts not recomputed objectives/WDL; no all-domain independenceclaim.')
(B/'consumer-result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out))
