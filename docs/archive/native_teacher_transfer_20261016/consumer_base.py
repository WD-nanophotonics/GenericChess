"""Search-disabled full-state/history consumer for this frozen research segment."""
from pathlib import Path
import sys,json,time,hashlib,collections
R=Path.cwd();sys.path.insert(0,str(R));B=Path(sys.argv[1])if len(sys.argv)>1 else R/'.local_agent/alias-teacher-20261016'
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

from generic_chess.rules.compiler import compile_ruleset_for_execution
start=time.perf_counter()
parents={}
def parent(seed,rd=None,record=None):
 d=read('roots/'+str(seed)+'.json')
 if rd is None and seed in parents:c,nr=parents[seed]
 else:
  c,nr=compiled(dict(ruleset=d['ruleset']if rd is None else rd))
  if rd is None:parents[seed]=(c,nr)
 s=GameSession.replay(c,deserialize_game_record(json.dumps(d['game_record']if record is None else record)))
 if rd is None and record is None:assert record_value(s.state)==d['state']
 compare(s,nr,s.state,pack_semantic_search_position(c,nr,s),list(s._search_witnesses))
 return s,nr
pure=read('input.json');pc=compile_ruleset_for_execution(deserialize_ruleset(json.dumps(pure['ruleset'])));pn=nc.compile_native_semantic_rules(pc)
for filename,limit in [('results.json',None),('attribution-results.json',128)]:
 for row in read(filename)['rows']:
  s=GameSession.replay(pc,deserialize_game_record(json.dumps(pure['game_record'])));assert record_value(s.state)==pure['state'];compare(s,pn,s.state,pack_semantic_search_position(pc,pn,s),list(s._search_witnesses));r=row['result'];query(s,pn,r,row['nodes_cap']if limit is None else limit);counts['fixture_queries']+=1
  if limit is None:
   assert r['root_hint_requested']==row['hint']and r['root_hint_legal'];assert all(x==row['hint']for x in r['root_iteration_first_actions'])
for filename,limit in [('finite-teacher-results.json',None),('core-teacher-results.json',262144),('horizon-results.json',65536),('action-coverage-results.json',65536)]:
 data=read(filename);assert data['complete']
 for row in data['rows']:
  s,nr=parent(row['seed'])
  if filename!='finite-teacher-results.json'or row['phase']=='teacher':
   ac=action(row['action']);np=sem.make_checked(nr,pack_semantic_search_position(s.compiled,nr,s),pack_semantic_action(nr,s.state.position,ac));s.submit(ac);compare(s,nr,s.state,np,list(s._search_witnesses));counts['teacher_child_edges']+=1
  if row['kind']=='ACTUAL_TERMINAL_CHILD':assert s.state.terminal_status.is_terminal;counts['terminal_slots']+=1;continue
  assert row['kind']=='ACTUAL_QUERY'
  if 'child_state'in row:assert record_value(s.state)==row['child_state']
  cap=limit if limit is not None else 262144 if row['phase']=='teacher'else row['nodes_cap']
  query(s,nr,row['result'],cap);assert row['root_restored'];counts[filename]+=1
for row in read('rename-tie-results.json')['rows']:
 s,nr=parent(row['seed']);ac=action(row['action']);np=sem.make_checked(nr,pack_semantic_search_position(s.compiled,nr,s),pack_semantic_action(nr,s.state.position,ac));s.submit(ac);assert record_value(s.state)==row['child_state'];compare(s,nr,s.state,np,list(s._search_witnesses));query(s,nr,row['result'],4096);assert row['finite_root_q']==1208;counts['rename_tie_queries']+=1
for row in read('rename-results.json')['rows']:
 for rd,rec,r in [(None,None,row['search'][0]),(row['renamed_ruleset'],row['renamed_record'],row['search'][1])]:
  s,nr=parent(row['seed'],rd,rec);query(s,nr,r,65536);counts['rename_queries']+=1
for row in read('child-census-results.json')['rows']:
 s,nr=parent(row['seed']);assert len(s.legal_actions())==row['legal_count'];groups=set()
 for item in row['actions']:
  ac=action(item['action']);assert ac in s.legal_actions();np=sem.make_checked(nr,pack_semantic_search_position(s.compiled,nr,s),pack_semantic_action(nr,s.state.position,ac));z=apply_action(s.state,ac,s.compiled);assert digest(z)==item['child_sha256'];compare(s,nr,z,np,list(s._search_witnesses)+[z.position]);groups.add(digest(z));assert int(pack_semantic_action(nr,s.state.position,ac))==item['native_packed'];counts['census_child_edges']+=1
 assert len(groups)==row['unique_children']
out=dict(complete=True,counts=dict(counts),seconds=time.perf_counter()-start,scope='Allactualreceipt/PV/fallback/CoreNativeboardhandsaux/ply/orderedpositiondigest/actor-checkhistory replay, searchdisabled. RawCoreactionsignatures preservedinactualrecords; noWDL/oldclockauthentication/modeltraining.')
(B/'base-consumer-result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out),flush=True)
