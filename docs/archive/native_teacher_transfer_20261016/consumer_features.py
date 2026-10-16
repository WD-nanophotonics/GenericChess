"""Recompute saved cosmetic feature mappings from bound publication source."""
from pathlib import Path
import sys,json,collections,time,numpy as np
R=Path.cwd();sys.path.insert(0,str(R));B=Path(sys.argv[1]);start=time.perf_counter()
from scripts.position_features import SparsePositionEncoder
from scripts.research_record import record_value
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove
from generic_chess.core.coordinates import Square
from generic_chess.learning.policy_v1 import action_v1_components
from generic_chess.core.transition import apply_action
from generic_chess.native import _module,SemanticSearchEngine
assert Path(_module().__file__).resolve().is_relative_to(R.resolve())
assert Path(sys.modules[SparsePositionEncoder.__module__].__file__).resolve().is_relative_to(R.resolve())
SemanticSearchEngine.search=lambda *a,**k:(_ for _ in()).throw(AssertionError('No newsearch'))
class Adapter(CompiledSemanticRuleset):
 __slots__=()
 def __getattr__(self,n):return getattr(self._legacy_compiled,n)
 @property
 def semantic(self):return self

def compile(rs):
 x=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(rs)));return Adapter(ir=x.ir,_legacy_compiled=x._legacy_compiled,support=x.support)
def read(f):return json.loads((B/f).read_bytes())
def action(x):
 if 'from_square'in x:return SemanticBoardMove(x['pattern_id'],x['geometry_id'],x['actor_type_id'],Square(**x['from_square']),Square(**x['to_square']),x['promotion_target_id'])
 return SemanticDropMove(x['pattern_id'],x['geometry_id'],x['base_type_id'],Square(**x['to_square']))
def king_features(c,p):
 anchors={t.type_id for t in c._legacy_compiled.piece_types if t.is_anchor};loc=collections.defaultdict(list);n=p.board_size()
 for i,x in enumerate(p.board):
  if x is not None and x.current_type_id in anchors:loc[x.owner].append(i)
 assert len(loc[0])==len(loc[1])==1
 kk={('kingking',loc[0][0],loc[1][0]):1.0};rel={}
 for owner in(0,1):
  a=loc[owner][0];ax,ay=a%n,a//n
  for i,x in enumerate(p.board):
   if x is None:continue
   tok=('kingpiece',owner,x.owner,x.current_type_id,x.base_type_id,bool(x.promoted),i%n-ax,i//n-ay);rel[tok]=rel.get(tok,0)+1.0
 return kk,rel
def absf(e,p):
 i,v=e.encode(p,(0,0,0));return dict(zip(map(int,i),map(float,v)))
def delta(a,b):return sum(a.get(k,0)!=b.get(k,0)for k in a.keys()|b.keys())
counts=collections.Counter();saved=read('rename-results.json');maps={x['seed']:x for x in read('rename-contract-map-results.json')['rows']};fds={x['seed']:x for x in read('feature-delta-results.json')['rows']}
for row in saved['rows']:
 d=read(row['root']);c=compile(d['ruleset']);cr=compile(row['renamed_ruleset']);s=GameSession.replay(c,deserialize_game_record(json.dumps(d['game_record'])));sr=GameSession.replay(cr,deserialize_game_record(json.dumps(maps[row['seed']]['contract_mapped_record'])));e=SparsePositionEncoder(c);er=SparsePositionEncoder(cr);a=e.dense(s.state.position,(0,0,0));b=er.dense(sr.state.position,(0,0,0));mp=row['feature_permutation'];z=np.zeros_like(a);z[mp]=a;assert np.array_equal(z,b)
 w=np.random.default_rng(20261016).normal(size=(16,len(a)));wr=np.zeros_like(w);wr[:,mp]=w;assert np.max(np.abs(w@a-wr@b))<1e-12;counts['random_feature_map_controls']+=1
 pm=maps[row['seed']]['pattern_map'];gm=maps[row['seed']]['geometry_map'];tm=row['mapping'];src=tuple(sorted(c.support.type_metadata));dst=tuple(sorted(cr.support.type_metadata));ix={t:i for i,t in enumerate(dst)};nt=len(src)
 legal=tuple(s.legal_actions());target={json.dumps(record_value(x),sort_keys=True):x for x in sr.legal_actions()};observed=set()
 for ac in legal:
  x=record_value(ac);x['pattern_id']=pm[x['pattern_id']];x['geometry_id']=gm[x['geometry_id']]
  for k in('actor_type_id','base_type_id','promotion_target_id'):
   if x.get(k)is not None:x[k]=tm[x[k]]
  k=json.dumps(x,sort_keys=True);assert k in target;observed.add(k);ar=target[k];v,cat=action_v1_components(c,s.state.position,ac);vr,crcat=action_v1_components(cr,sr.state.position,ar);expect=tuple(ix[tm[src[i]]]if i<nt else nt for i in cat[:3])+(cat[3],);assert np.array_equal(v,vr)and expect==crcat;counts['v1_mapped_actions']+=1
 assert observed==set(target)
 f0=absf(e,s.state.position);k0,r0=king_features(c,s.state.position)
 for item in fds[row['seed']]['rows']:
  ch=apply_action(s.state,action(item['action']),c);f=absf(e,ch.position);k,r=king_features(c,ch.position);assert(delta(f0,f),delta(k0,k),delta(r0,r))==(item['absolute_delta'],item['kingking_delta'],item['relative_delta']);counts['feature_delta_transitions']+=1
out=dict(complete=True,counts=dict(counts),seconds=time.perf_counter()-start,scope='SourceboundNumPyfeature/permutation/V1/structuraldeltarecomputation; nosearch/game/fit. Samealgorithms/sharedhost, notindependentlearnedgeneralization orincrementalimplementation.')
(B/'feature-consumer-result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out),flush=True)