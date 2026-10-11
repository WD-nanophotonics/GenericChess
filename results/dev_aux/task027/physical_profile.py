"""Whole physical copy/publication observation, original unchanged product caller."""
import sys,time,json,collections,importlib.util
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
import generic_chess.core.semantic_executor as m
from scripts.search_backend_comparison import CASES,CoreBoard,VALUES
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta import player as pm
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime as R
from scripts.research_record import record_value
from scripts.reserve_refresh_diagnostic import stopped
s=importlib.util.spec_from_file_location('weighted',Path('.local_agent/weighted-backend-20261011/bridge.py'));w=importlib.util.module_from_spec(s);s.loader.exec_module(w)
B=Path(__file__).parent
saved=dict(transition=m.SemanticEngine._transition,trial=m.SemanticEngine._trial_child_if_s3_legal,init=m._WorkingPosition.__init__,freeze=m._WorkingPosition.to_position,attach=R.attach_stats,factory=pm.SearchStatistics)

def clean(v):
 if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if 'seconds' not in k and not k.startswith('time_')}
 if isinstance(v,list):return [clean(x) for x in v]
 return v

def actual(rt):return frozenset(collections.Counter((h,e.identity,int(e.count)) for h,b in rt._occurrences.items() for e in b).items())
def state(rt):return (rt.position,rt.ply_count,rt.terminal_status,rt.current_identity,rt.runtime_hash,rt._snapshot,tuple(rt.history),rt._history_context,actual(rt),frozenset(rt._opaque_imported_keys),frozenset(rt._history_aliases.items()))
def attach(rt,stats):
 value=saved['attach'](rt,stats);runtimes.append((rt,state(rt)));return value

def consumer():
 names=[];f=sys._getframe(2)
 for _ in range(14):
  if f is None:break
  names.append(f.f_code.co_name);f=f.f_back
 if 'terminal_from_search_runtime' in names:return 'terminal_runtime'
 if 'initial_state' in names:return 'terminal_initial'
 if '_exists_s3_reply' in names:return 's4_reply'
 if '_push_impl' in names:return 'formal_push'
 return 'frontier_or_other:'+'/'.join(names[:3])

def trial(self,*args,**kw):
 key=stage+'|'+consumer();ctx={'key':key,'outcome':'pending','copy':0.,'freeze':0.,'trans':0.};stack.append(ctx)
 try:
  value=saved['trial'](self,*args,**kw);ctx['outcome']='s3_accepted' if value is not None else 's3_rejected';return value
 except BaseException:ctx['outcome']='exception';raise
 finally:
  assert stack.pop() is ctx
  k=key+'|'+ctx['outcome'];rows[k]['trials']+=1
  for name in ['copy','freeze','trans']:rows[k][name]+=ctx[name]

def transition(self,*args,**kw):
 own=not stack;ctx={'key':stage+'|'+consumer(),'copy':0.,'freeze':0.,'trans':0.}
 if own:stack.append(ctx)
 t=time.perf_counter()
 try:return saved['transition'](self,*args,**kw)
 finally:
  elapsed=time.perf_counter()-t;stack[-1]['trans']+=elapsed;counts['transitions']+=1
  if own:
   assert stack.pop() is ctx;k=ctx['key']+'|formal';rows[k]['transitions']+=1
   for n in ['copy','freeze','trans']:rows[k][n]+=ctx[n]

def init(self,*args,**kw):
 t=time.perf_counter()
 try:return saved['init'](self,*args,**kw)
 finally:
  counts['copies']+=1;elapsed=time.perf_counter()-t
  if stack:stack[-1]['copy']+=elapsed
  else:orphan['copy']+=elapsed

def freeze(self,*args,**kw):
 t=time.perf_counter()
 try:return saved['freeze'](self,*args,**kw)
 finally:
  counts['freezes']+=1;elapsed=time.perf_counter()-t
  if stack:stack[-1]['freeze']+=elapsed
  else:orphan['freeze']+=elapsed

case=next(x for x in CASES if x['id']=='chess-middle');compiled=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'));board=CoreBoard(case,compiled);e=w.weighted(compiled,VALUES['chess']);out={'complete':False,'rows':[]}
try:
 R.attach_stats=attach
 for measured in (False,True):
  stopped();runtimes=[];captured=[];rows=collections.defaultdict(lambda:collections.Counter());counts=collections.Counter();orphan=collections.Counter();stack=[];stage='session'
  def factory():
   v=SearchStatistics();captured.append(v);return v
  pm.SearchStatistics=factory
  m.SemanticEngine._transition=transition if measured else saved['transition'];m.SemanticEngine._trial_child_if_s3_legal=trial if measured else saved['trial'];m._WorkingPosition.__init__=init if measured else saved['init'];m._WorkingPosition.to_position=freeze if measured else saved['freeze']
  start=time.perf_counter();session=GameSession(compiled);session._state=board.initial;session._search_history_witnesses=board.witnesses;session_secs=time.perf_counter()-start;stage='choose';t=time.perf_counter()
  value=AlphaBetaPlayer(compiled,evaluator_override=e,use_native_semantic_legality=True,use_disk_cache=False).choose_action(session,SearchLimits(max_depth=2,max_nodes=32768,max_time_seconds=120,quiescence_max_depth=4,quiescence_hard_max_depth=8));wall=time.perf_counter()-t
  assert value.completed_depth==2 and session.state is board.initial and len(runtimes)==1 and len(captured)==1 and not stack
  rt,root=runtimes[0];rt.assert_balanced();assert state(rt)==root
  row=dict(measured=measured,decision=record_value(value),stats=record_value(captured[0]),wall=wall,session_seconds=session_secs,counts=dict(counts),orphan=dict(orphan),components={k:dict(v) for k,v in rows.items()},root_multiset_restored=True);out['rows'].append(row)
  (B/'physical-profile.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print('arm',measured,'wall',wall,'counts',dict(counts),flush=True)
 assert clean(out['rows'][0]['decision'])==clean(out['rows'][1]['decision']) and clean(out['rows'][0]['stats'])==clean(out['rows'][1]['stats'])
 out['complete']=True;out['limits']='Nested component clocks include wrapper instrumentation; copied aux not isolated in WorkingPosition init. No optimization/equal-time speed claim or opaque C primitive enumeration. Ordinary versus observed wall is observer overhead context only.'
 (B/'physical-profile.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
finally:
 m.SemanticEngine._transition=saved['transition'];m.SemanticEngine._trial_child_if_s3_legal=saved['trial'];m._WorkingPosition.__init__=saved['init'];m._WorkingPosition.to_position=saved['freeze'];R.attach_stats=saved['attach'];pm.SearchStatistics=saved['factory']
