"""Independent Python/Native nonzero model value checks, with source binding."""
from pathlib import Path
from copy import copy
import sys,json,time,numpy as np
R=Path.cwd();B=Path(sys.argv[1]).resolve();sys.path.insert(0,str(R))
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove
from generic_chess.core.coordinates import Square
from generic_chess.learning.nonlinear import semantic_state_features,CompactNonlinearResidual
from generic_chess.native import SemanticSearchEngine,_module,semantic as sem
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.adapter import pack_semantic_search_position
assert Path(_module().__file__).resolve().is_relative_to(R.resolve())
assert Path(sys.modules[CompactNonlinearResidual.__module__].__file__).resolve().is_relative_to(R.resolve())
SemanticSearchEngine.search=lambda *a,**k:(_ for _ in()).throw(AssertionError('No newsearch'))
class Adapter(CompiledSemanticRuleset):
 __slots__=()
 def __getattr__(self,name):return getattr(self._legacy_compiled,name)
 @property
 def semantic(self):return self

def read(n):return json.loads((B/n).read_bytes())
def action(x):
 if x is None:return None
 if 'from_square'in x:return SemanticBoardMove(x['pattern_id'],x['geometry_id'],x['actor_type_id'],Square(**x['from_square']),Square(**x['to_square']),x['promotion_target_id'])
 return SemanticDropMove(x['pattern_id'],x['geometry_id'],x['base_type_id'],Square(**x['to_square']))
cache={};start=time.perf_counter();counts=dict(nonzero_compact_forwards=0,four_profile_values=0,documented_large_input_exclusions=0)
def root(seed):
 if seed not in cache:
  d=read(f'fresh-roots/{seed}.json');x=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(d['ruleset'])));c=Adapter(ir=x.ir,_legacy_compiled=x._legacy_compiled,support=x.support);s=GameSession.replay(c,deserialize_game_record(json.dumps(d['game_record'])));nr=compile_native_semantic_rules(c);cache[seed]=(c,s,nr)
 c,s,nr=cache[seed];return c,copy(s),nr
for row in read('fixed-node-recovered-results.json')['forward_checks']:
 if row['kind']!='ACTUAL_NONZERO_FORWARD_CHECK':counts['documented_large_input_exclusions']+=1;continue
 c,s,nr=root(row['seed']);npk=pack_semantic_search_position(c,nr,s);dyn=sem.dynamic_features(nr,npk);payload=read(row['payload']);value=float(CompactNonlinearResidual.from_dict(payload).predict(semantic_state_features(s.state.position,c,dyn)));expect=round(value*256)*(1 if s.state.position.side_to_move==0 else-1);actual=sem.evaluate(nr,npk,board_values=[0]*len(nr.type_ids),hand_values=[0]*len(nr.type_ids),compact_values=payload,evaluator_scale=256);assert actual==expect==row['expected'];counts['nonzero_compact_forwards']+=1
for row in read('reuse-results.json')['direct']:
 c,s,nr=root(row['seed']);ac=action(row['action'])
 if ac is not None:s.submit(ac)
 npk=pack_semantic_search_position(c,nr,s);dyn=sem.dynamic_features(nr,npk);payload=read(f"nonzero-payloads/{row['seed']}.json");profile=row['profile'];linear=(2,3,5)if profile in('linear_only','both')else None;compact=payload if profile in('compact_only','both')else None;res=float(CompactNonlinearResidual.from_dict(payload).predict(semantic_state_features(s.state.position,c,dyn)));sign=1 if s.state.position.side_to_move==0 else-1;expect=sign*((sum(w*f for w,f in zip((2,3,5),dyn))if linear else 0)+(round(res*256)if compact else 0));actual=sem.evaluate(nr,npk,board_values=[0]*len(nr.type_ids),hand_values=[0]*len(nr.type_ids),dynamic_values=linear,compact_values=compact,evaluator_scale=256);assert actual==expect==row['expected'];counts['four_profile_values']+=1
out=dict(complete=True,counts=counts,seconds=time.perf_counter()-start,scope='SourceboundNumPyforward andNativevalues, nofit/search/game. Notindependentoldcounter/clockverification ormodelquality.');(B/'consumer-model-result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out),flush=True)
