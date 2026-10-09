"""Read-only generation audit, first frozen root with all three q2 arms capped.
New diagnostic: D3/128 total nodes/no deadline, v3 leaf/fixed Unit ordering/q2hard8.
Do not extend original2048node/2sec records. Instrument visit episodes (push/pop),
not Position-only equivalence or a cross-history cache. Compare exact decisions
and work with an uninstrumented cold control; timings are descriptive overhead.
"""
from pathlib import Path
import sys,json,time,zipfile,collections
sys.path.insert(0,str(Path.cwd()))
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.core.actions import action_from_dict
from generic_chess.core.semantic_executor import SemanticEngine
import generic_chess.core.search_runtime as sr
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value
from scripts.unfamiliar_search import validate_pv

p=Path(__file__).parent;out=p/'source-prior-generation-audit.json';assert not out.exists()
with zipfile.ZipFile(p/'source-prior-diagnosis-relative.zip') as z:
 d=json.loads(z.read('.local_agent/source-prior-transfer-20261009/declaration.json'))
 old=json.loads(z.read('.local_agent/source-prior-transfer-20261009/callers.json'))
selected=None
for rule in old['rules']:
 for ply in range(rule['roots']):
  arms=[r for r in rule['calls'] if r['ply']==ply and r['q']==2]
  if len(arms)==3 and all(not r['complete'] for r in arms):
   selected=(rule['seed'],ply);break
 if selected:break
assert selected
case=next(r for r in d['rules'] if r['seed']==selected[0])
c=compile_ruleset_for_execution(ruleset_from_dict(case['rules']));s=GameSession(c)
for a in case['route'][:selected[1]]:s.submit(action_from_dict(a))
before=s.state
cfg=EvaluationConfig(dynamic_mobility_weight=0,anchor_escape_weight=0,promotion_potential_weight=0)
profile,_=build_semantic_opportunity_profile(c,cfg)
unit={t.type_id:0 if t.is_anchor else 1000 for t in c.piece_types}
class FixedOrder:
 def __init__(self):self.leaf=Evaluator(c,profile,cfg)
 def evaluate(self,state):return self.leaf.evaluate(state)
 def capture_order_value(self,moving,captured):return unit[captured.current_type_id]*10-unit[moving.current_type_id]//10
 def type_value(self,t):return unit[t]
limits=SearchLimits(max_depth=3,max_nodes=128,max_time_seconds=None,quiescence_max_depth=2,quiescence_hard_max_depth=8)
def run():
 player=AlphaBetaPlayer(c,evaluator_override=FixedOrder(),use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False))
 start=time.perf_counter();decision=player.choose_action(s,limits);seconds=time.perf_counter()-start
 validate_pv(s,decision);assert s.state==before
 return record_value(decision),seconds
control,control_seconds=run()
original=(sr.terminal_from_search_runtime,sr.SearchPathRuntime.legal_actions,sr.SearchPathRuntime.pop,SemanticEngine.iter_legal_action_bindings)
phase=None;serial=0;active={};rows={};retained=[]
def terminal(runtime,checkpoint=None):
 global phase,serial
 serial+=1;episode=serial;active[id(runtime)]=episode
 # Retain identity, auxiliary position, occurrence snapshot and history context.
 retained.append((runtime._identity,runtime.position,runtime._snapshot,runtime._history_context))
 row=rows.setdefault(episode,collections.Counter());previous=phase;phase=('existence',episode)
 start=time.perf_counter()
 try:return original[0](runtime,checkpoint)
 finally:row['terminal_calls']+=1;row['terminal_seconds']+=time.perf_counter()-start;phase=previous
def legal(runtime,checkpoint=None):
 global phase
 episode=active.get(id(runtime),0);row=rows.setdefault(episode,collections.Counter())
 row['legal_requests']+=1;row['cache_hits']+=int(runtime._legal_cache is not None)
 previous=phase;phase=('expansion',episode);start=time.perf_counter()
 try:return original[1](runtime,checkpoint)
 finally:row['legal_request_seconds']+=time.perf_counter()-start;phase=previous
def pop(runtime):
 result=original[2](runtime)
 # Restore the visit tag by exact retained identity AND path history/snapshot.
 active[id(runtime)]=next((i for i,items in enumerate(retained,1) if items[0] is runtime._identity and items[2] is runtime._snapshot and items[3] is runtime._history_context),0)
 return result
def bindings(engine,position,checkpoint=None):
 tag=phase
 if tag is None:yield from original[3](engine,position,checkpoint=checkpoint);return
 kind,episode=tag;row=rows.setdefault(episode,collections.Counter());row[kind+'_generations']+=1
 iterator=original[3](engine,position,checkpoint=checkpoint)
 while True:
  start=time.perf_counter()
  try:item=next(iterator)
  except StopIteration:row[kind+'_iterator_seconds']+=time.perf_counter()-start;return
  except BaseException:row[kind+'_iterator_seconds']+=time.perf_counter()-start;raise
  row[kind+'_iterator_seconds']+=time.perf_counter()-start;row[kind+'_yielded']+=1
  yield item
sr.terminal_from_search_runtime=terminal;sr.SearchPathRuntime.legal_actions=legal;sr.SearchPathRuntime.pop=pop;SemanticEngine.iter_legal_action_bindings=bindings
try:instrumented,instrumented_seconds=run()
finally:sr.terminal_from_search_runtime,sr.SearchPathRuntime.legal_actions,sr.SearchPathRuntime.pop,SemanticEngine.iter_legal_action_bindings=original
fields=['action','score','principal_variation','completed_depth','nodes','qnodes','termination_reason']
assert all(control[k]==instrumented[k] for k in fields)
totals=collections.Counter()
for r in rows.values():totals.update(r)
report=dict(scope=__doc__,seed=selected[0],ply=selected[1],limits=record_value(limits),control=control,instrumented=instrumented,control_seconds=control_seconds,instrumented_seconds=instrumented_seconds,signature_fields=fields,signatures_equal=True,totals=dict(totals),visit_episodes=len(rows),existence_then_expansion_episodes=sum(r['existence_generations']>0 and r['expansion_generations']>0 for r in rows.values()),existence_only_episodes=sum(r['existence_generations']>0 and not r['expansion_generations'] for r in rows.values()),max_existence_yields=max(r['existence_yielded'] for r in rows.values()),multiple_full_generation_episodes=sum(r['expansion_generations']>1 for r in rows.values()),limitations='Episode scope only; no equivalent-state merging. Iterator next timings are disjoint by phase, wrapper times contain iterator time; never add them. Extra telemetry/path-tag recovery overhead prevents performance comparisons. No eager child full-set proposal or product change.')
out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['control','instrumented']},indent=2))
