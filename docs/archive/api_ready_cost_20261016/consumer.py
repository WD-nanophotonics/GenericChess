"""Replay receipt state/history and independently recompute feature contracts; no search."""
from pathlib import Path
from copy import copy
from dataclasses import replace
import sys,json,time,collections
R=Path.cwd();B=Path(sys.argv[1]).resolve();sys.path[:0]=[str(R),str(R/'tests')]
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove,PassAction
from generic_chess.core.coordinates import Square
from generic_chess.core.identity import position_identity_key
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.native import semantic as sem,SemanticSearchEngine,_module
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.mirror import expected_snapshot,pack_semantic_action
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from scripts.research_record import record_value
assert Path(_module().__file__).resolve().is_relative_to(R.resolve())
def forbidden(*a,**k):raise AssertionError('Receipt replay must not search')
SemanticSearchEngine.search=forbidden;AlphaBetaPlayer.choose_action=forbidden;_module().semantic_engine_search=forbidden
for k in('fixed_depth_search','probe_search','semantic_iterative_search','root_parallel_search'):setattr(sem,k,forbidden)
class Adapter(CompiledSemanticRuleset):
 __slots__=()
 def __getattr__(self,name):return getattr(self._legacy_compiled,name)
 @property
 def semantic(self):return self

def read(name):return json.loads((B/name).read_bytes())
def action(x):
 if x is None:return None
 if not x:return PassAction()
 if 'from_square'in x:return SemanticBoardMove(x['pattern_id'],x['geometry_id'],x['actor_type_id'],Square(**x['from_square']),Square(**x['to_square']),x['promotion_target_id'])
 return SemanticDropMove(x['pattern_id'],x['geometry_id'],x['base_type_id'],Square(**x['to_square']))
cache={};counts=collections.Counter();start=time.perf_counter()
def root(seed,fresh):
 key=(seed,fresh)
 if key not in cache:
  d=read('roots/'+str(seed)+'.json');x=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(d['ruleset'])));c=Adapter(ir=x.ir,_legacy_compiled=x._legacy_compiled,support=x.support);s=GameSession.replay(c,deserialize_game_record(json.dumps(d['game_record'])));cache[key]=(s,compile_native_semantic_rules(c))
 s,nr=cache[key];return copy(s),nr

def compare(s,nr,np):
 snap=sem.snapshot(nr,np);want=expected_snapshot(s.state.position,nr,s.compiled)
 for k in('board','hands','aux_state','side'):assert record_value(snap[k])==record_value(want[k]),k
 assert snap['ply']==s.state.ply_count
 assert [''.join(f'{v:016x}'for v in row)for row in snap['history']]==[str(position_identity_key(p,s.compiled))for p in s._search_witnesses]
 assert snap['history_events']==tuple((255 if h.actor<0 else h.actor,bool(h.gave_check))for h in s.state.history)
 assert sem.terminal_status(nr,np)==dict(status=s.state.terminal_status.status.value,winner=s.state.terminal_status.winner)
 counts['full_state_history_comparisons']+=1

def query(s,nr,r):
 np=pack_semantic_search_position(s.compiled,nr,s);compare(s,nr,np);chosen=action(r.get('action'));assert chosen is None or chosen in s.legal_actions();line=r.get('decision_line')or r.get('principal_variation')or([r['action']]if chosen is not None else[])
 for item in line:
  if isinstance(item,str):s.declare(item);counts['declarations']+=1;continue
  ac=action(item);assert ac in s.legal_actions();np=sem.make_checked(nr,np,pack_semantic_action(nr,s.state.position,ac));s.submit(ac);compare(s,nr,np);counts['pv_or_fallback_edges']+=1
 if r.get('principal_variation')and 'dynamic_features'in r:assert list(sem.dynamic_features(nr,np))==r['dynamic_features']
 counts['query_receipts']+=1

for filename in ['results.json','reserve-results.json','fixedD4-results.json','core-results.json']:
 for row in read(filename)['rows']:
  if row['kind']!='ACTUAL_QUERY':counts[row['kind']]+=1;continue
  s,nr=root(row['seed'],True);query(s,nr,row['result']);counts['arm_'+row.get('arm','PURE_CORE')]+=1;counts[filename]+=1
for row in read('results.json')['roots']:
 if row['kind'] in ('EXECUTED_ROOT','ACTUAL_TERMINAL_TAIL'):
  s,nr=root(row['seed'],True);np=pack_semantic_search_position(s.compiled,nr,s);compare(s,nr,np);assert record_value(s.state)==read('roots/'+str(row['seed'])+'.json')['state']
out=dict(complete=True,counts=dict(counts),seconds=time.perf_counter()-start,scope='Source-bound search-disabled currentNative/Core full PV/terminal/history replay for BOTH baseline/final receipts, plus returned leaf dynamic vector. Shared Core/compiler/host; does not reexecute/authenticate original clocks or independent minimax/WDL.')
(B/'consumer-result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
