"""Private mechanical effect specialization: unchanged fixed work and completedD2 controls."""
import sys,time,importlib.util
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
B=Path(__file__).parent
def module(name,file):
 s=importlib.util.spec_from_file_location(name,B/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
c=module('caller','installed_control.py');d=module('delta','compiled_effect_shared.py')
def run():
 start=time.perf_counter();out=dict(complete=False,scope='Private mechanical rule effect specialization; all effects/terminal/history retained. Predeclared single-change comparison.8existing roots/4opposite fixed512node pairs each; existing quiet root4completedD2 calls. No retained frontier or state cache; only shared effect-kind-sequence code specialization with dynamic original effect operands changes. Same evaluation/q/history/Native route. All adverse rows retained; mechanical preparation separate and also reported as cold total; no defaults changed.',fixed=[],completed=[],setup=[])
 for case in c.CASES:
  compiled=c.compile_ruleset_for_execution(c.build_builtin_ruleset('western_chess' if case['game']=='chess' else 'standard_shogi'));board=c.CoreBoard(case,compiled);e=c.w.weighted(compiled,c.VALUES[case['game']]);t=time.perf_counter();d.prepare(compiled);setup=time.perf_counter()-t;out['setup'].append(dict(root=case['id'],seconds=setup,metadata=dict(d.metadata)))
  for repeat in range(4):
   pair=[]
   for active in ((False,True) if repeat%2==0 else (True,False)):
    c.stopped();assert time.perf_counter()-start<240;d.install(active);s=c.GameSession(compiled);s._state=board.initial;s._search_history_witnesses=board.witnesses;t=time.perf_counter()
    try:v=c.AlphaBetaPlayer(compiled,evaluator_override=e,use_native_semantic_legality=True,use_disk_cache=False).choose_action(s,c.SearchLimits(max_depth=4,max_nodes=512,max_time_seconds=10,quiescence_max_depth=4,quiescence_hard_max_depth=8))
    finally:d.install(False)
    assert s.state is board.initial;value=c.record_value(v);pair.append(c.clean(value));out['fixed'].append(dict(root=case['id'],repeat=repeat,candidate=active,wall=time.perf_counter()-t,decision=value))
   assert pair[0]==pair[1]
  c.write_record(B/'compiled-effect-shared-control.json',out);print(case['id'],'fixed exact',flush=True)
  if case['id']=='chess-middle':
   for repeat in range(2):
    pair=[]
    for active in ((False,True) if repeat==0 else (True,False)):
     c.stopped();assert time.perf_counter()-start<240;d.install(active);s=c.GameSession(compiled);s._state=board.initial;s._search_history_witnesses=board.witnesses;t=time.perf_counter()
     try:v=c.AlphaBetaPlayer(compiled,evaluator_override=e,use_native_semantic_legality=True,use_disk_cache=False).choose_action(s,c.SearchLimits(max_depth=2,max_nodes=32768,max_time_seconds=30,quiescence_max_depth=4,quiescence_hard_max_depth=8))
     finally:d.install(False)
     assert s.state is board.initial and v.completed_depth==2;value=c.record_value(v);pair.append(c.clean(value));out['completed'].append(dict(root=case['id'],repeat=repeat,candidate=active,wall=time.perf_counter()-t,decision=value))
    assert pair[0]==pair[1]
 out['complete']=True;out['seconds']=time.perf_counter()-start;c.write_record(B/'compiled-effect-shared-control.json',out)
 for case in c.CASES:
  rows=[v for v in out['fixed'] if v['root']==case['id']];cost={a:sum(v['wall'] for v in rows if v['candidate']==a) for a in (False,True)};print(case['id'],cost[True]/cost[False],flush=True)
if __name__=='__main__':run()
