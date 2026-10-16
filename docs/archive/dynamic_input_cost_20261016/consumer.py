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
from phase19c1_native_semantic_fixtures import semantic_corpus
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
  d=read(('fresh-roots/'if fresh else'roots/')+str(seed)+'.json');x=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(d['ruleset'])));c=Adapter(ir=x.ir,_legacy_compiled=x._legacy_compiled,support=x.support);s=GameSession.replay(c,deserialize_game_record(json.dumps(d['game_record'])));cache[key]=(s,compile_native_semantic_rules(c))
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
 counts['query_receipts']+=1
for filename,fresh in[('search-results.json',False),('fresh-recovered-results.json',True),('fixed-node-recovered-results.json',True),('product-binding-results.json',True),('reuse-results.json',True),('reuse-product-results.json',True),('strict-product-results.json',True)]:
 doc=read(filename);rows=doc.get('queries')if isinstance(doc.get('queries'),list)else doc['rows']
 for row in rows:
  if row.get('kind','ACTUAL_QUERY')!='ACTUAL_QUERY':continue
  s,nr=root(row['seed'],fresh);query(s,nr,row['result']);counts[filename]+=1
for row in read('component-results.json')['rows']:
 s,nr=root(row['seed'],False);a=action(row['action'])
 if a is not None:s.submit(a)
 np=pack_semantic_search_position(s.compiled,nr,s);compare(s,nr,np);assert list(sem.dynamic_features(nr,np))==row['observations'][0]['features'];counts['exposed_component_states']+=1

def oracle(c,p):
 e=SemanticEngine(c);v=[]
 for owner in(0,1):
  view=replace(p,side_to_move=owner);aa=e.legal_actions(view);v.append((len(aa),sum(a.promotion_target_id is not None for a in aa),sum(a.source is not None and c.support.type_metadata[view.board[a.source].current_type_id].is_anchor for a in aa)-10*int(e.in_check(view,owner))))
 return tuple(a-b for a,b in zip(*v))
corpus=dict(semantic_corpus());pure_native={k:compile_native_semantic_rules(c)for k,c in corpus.items()}
for row in read('semantic-results.json')['rows']:
 c=corpus[row['fixture']];nr=pure_native[row['fixture']];s=GameSession.replay(c,deserialize_game_record(json.dumps(row['game_record'])));assert record_value(s.state)==row['state'];np=pack_semantic_search_position(c,nr,s);compare(s,nr,np);assert list(oracle(c,s.state.position))==list(sem.dynamic_features(nr,np))==row['features'];counts['pure_core_feature_states']+=1
for row in read('fresh-recovered-results.json')['rows']:
 if row['kind']!='EXECUTED_ROOT':continue
 s,nr=root(row['seed'],True);np=pack_semantic_search_position(s.compiled,nr,s);compare(s,nr,np);assert list(oracle(s.compiled,s.state.position))==list(sem.dynamic_features(nr,np))==row['features']==row['core_features'];counts['fresh_core_feature_states']+=1
# Original explicit S4 position fixtures and real pending sessions are retained.
import phase19b3_s4_fixtures as s4
from generic_chess.rules.compiler import compile_semantic_ruleset
builders={'opponent_checked':s4.opponent_checked_perspective_ruleset,'nested_s4':s4.nested_s4_option_b_ruleset,'full_child_state':s4.full_child_state_ruleset,'multiple_replies':s4.multiple_replies_ruleset,'restricted_finish':s4.restricted_finish_ruleset,'forbidden_drop':s4.forbidden_no_reply_drop_ruleset}
positions={'opponent_checked':s4.opponent_checked_reply_checked_position,'nested_s4':s4.nested_s4_option_b_position,'full_child_state':s4.full_child_state_position,'multiple_replies':s4.multiple_replies_position,'restricted_finish':s4.restricted_finish_position,'forbidden_drop':s4.forbidden_no_reply_drop_position}
for row in read('edge-results.json')['rows']:
 if row['kind']!='POSITION_FIXTURE':continue
 c=compile_semantic_ruleset(builders[row['fixture']]());nr=compile_native_semantic_rules(c);position=replace(positions[row['fixture']](c.support),side_to_move=row['side']);np=sem.pack_position(nr,row['payload']);before=sem.snapshot(nr,np);assert list(sem.dynamic_features(nr,np))==row['features']['normal']==list(oracle(c,position));assert sem.snapshot(nr,np)==before;counts['s4_position_features']+=1
# Capacity oldzeros are deliberately superseded by explicit unsupported, not rewritten.
from generic_chess import build_builtin_ruleset,RuleAutomaticAdjudication,compile_ruleset_for_execution

def pending_session(moves, trigger=3):
 definition=replace(build_builtin_ruleset('western_chess'),max_ply=3,automatic_adjudications=()if trigger is None else(RuleAutomaticAdjudication('audit',trigger),));c=compile_ruleset_for_execution(definition);ss=GameSession(c)
 for uci in moves:
  ac=next(a for a in ss.legal_actions()if getattr(a,'from_square',None)is not None and chr(97+a.from_square.file)+str(1+a.from_square.rank)+chr(97+a.to_square.file)+str(1+a.to_square.rank)==uci);ss.submit(ac)
 return ss
for name,moves,trigger in [('pending',('e2e4','d7d5','f1b5'),3),('pending_after',('e2e4','d7d5','f1b5','c7c6'),3),('rule_max',('e2e4','d7d5','f1b5'),None)]:
 ss=pending_session(moves,trigger);nn=compile_native_semantic_rules(ss.compiled);np=pack_semantic_search_position(ss.compiled,nn,ss);compare(ss,nn,np);row=next(r for r in read('edge-results.json')['rows']if r['fixture']==name);assert list(sem.dynamic_features(nn,np))==row['features']['normal'];counts['pending_max_feature_states']+=1
s=pending_session(('e2e4','d7d5','f1b5','c7c6'));nr=compile_native_semantic_rules(s.compiled);np=pack_semantic_search_position(s.compiled,nr,s);snap=sem.snapshot(nr,np)
from generic_chess.native.compiler import GC_SEM_MAX_PLY
hist=[(i+1,0,0,0,255 if i==0 else(i-1)%2,int(i>0 and i%2==1))for i in range(GC_SEM_MAX_PLY+1)];hist[-1]=(*snap['history'][-1],1,0);full=sem.pack_position(nr,dict(side=snap['side'],ply=GC_SEM_MAX_PLY,board=[None if p is None else list(p)for p in snap['board']],hands=[list(h)for h in snap['hands']],history=hist,aux_state=snap['aux_state']));assert sem.terminal_status(nr,full)['status']=='ongoing'
for fn in[lambda:sem.dynamic_features(nr,full),lambda:sem.spatial_features(nr,full),lambda:sem.evaluate(nr,full,dynamic_values=(1,0,0)),lambda:sem.evaluate(nr,full,localized_control_values=(1,-1,0,0,0,0,0,0,0))]:
 try:fn()
 except NotImplementedError as exc:assert 'history capacity'in str(exc)and'Core'in str(exc);counts['explicit_capacity_refusals']+=1
 else:raise AssertionError('Capacity became fakezero feature')
out=dict(complete=True,counts=dict(counts),seconds=time.perf_counter()-start,scope='ActualsourceboundnormalNative searchdisabledfullstate/history/PV andCorefeature replay; independentalgorithm/sharedCorecompiler/host. Noqueryrerun/game/fit/oldclockauthentication. Capacityoldzero deliberatelysuperseded; privatecountertimings/provenance notindependentlyauthenticated.')
(B/'consumer-result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out),flush=True)
