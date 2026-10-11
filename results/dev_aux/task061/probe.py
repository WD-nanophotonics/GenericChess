"""Fixed-node/cold and identical-warm-TT counterexample probe; own process only."""
import ast,collections,hashlib,importlib.util,json,sys,time
from pathlib import Path
from types import SimpleNamespace
B=Path(__file__).resolve().parent;ROOT=Path.cwd();D=json.loads((B/'DECLARATION.json').read_bytes());EXPORT=ROOT/'.local_agent/pinned_bebe'
sys.path.insert(0,str(EXPORT))
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta import player as pm
from generic_chess.ai.alphabeta.transposition import TranspositionTable,TTEntry
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime as Runtime
from scripts.search_backend_comparison import CASES,CoreBoard,VALUES
from scripts import reserve_refresh_diagnostic as rr
from scripts.research_record import record_value
assert Path(pm.__file__).resolve().is_relative_to(EXPORT.resolve())
assert hashlib.sha256((EXPORT/'generic_chess/_native_core.cp312-win_amd64.pyd').read_bytes()).hexdigest()==D['native_binary_sha256']
spec=importlib.util.spec_from_file_location('aux_frozen_weighted',EXPORT/'weighted.py');weighted=importlib.util.module_from_spec(spec);spec.loader.exec_module(weighted)
helper=ast.parse((EXPORT/'pvs_probe.py').read_text());ns={'collections':collections}
exec(compile(ast.Module(body=[n for n in helper.body if isinstance(n,ast.FunctionDef) and n.name in ('actual','state')],type_ignores=[]),'<archived restoration functions>','exec'),ns);runtime_state=ns['state']
rr.POLICY_SOURCES['clear']=rr.MODIFIED.replace('ctx.qdepth_limit = min(1, original_q)','ctx.qdepth_limit = original_q')
assert hashlib.sha256(rr.POLICY_SOURCES['clear'].encode()).hexdigest()=='2d5fc2ba8c259987443b5843769e267b86cd1303503bfb0b36f834ba0fab8021'
original=pm.run_root_search;oldattach=Runtime.attach_stats;oldfactory=pm.SearchStatistics
runtimes=[];captured=[]
def attach(rt,stats):
 oldattach(rt,stats);runtimes.append((rt,runtime_state(rt)))
def factory():
 v=oldfactory();captured.append(v);return v
def stopped():
 for name in ('rollout','advisor','slack'):
  v=json.loads((ROOT/'.local_agent'/ (name+'.json')).read_bytes())
  if v.get('stopped') or v.get('user_paused'):raise RuntimeError('user stop preserved')
 if time.perf_counter()-started>D['global_guard_seconds']:raise RuntimeError('predeclared global guard')
def tt_record(t):
 rows=sorted((repr(k),e.depth,e.score,e.bound.name,str(e.best_action),e.generation) for k,e in t._data.items())
 return dict(entries=len(rows),generation=t.generation,sha256=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest())
def clone(t):
 v=TranspositionTable(t._max_entries);v._generation=t._generation
 v._data={k:TTEntry(e.key,e.depth,e.score,e.bound,e.best_action,e.generation) for k,e in t._data.items()};assert tt_record(v)==tt_record(t);return v
out={'complete':False,'declaration':D,'fixed_modules':{'player':str(Path(pm.__file__).relative_to(EXPORT))},'seeds':[],'rows':[]};started=time.perf_counter()
def save(): (B/'result.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
def call(player,session,limits):
 runtimes.clear();captured.clear();t=time.perf_counter();value=player.choose_action(session,limits);wall=time.perf_counter()-t
 assert len(runtimes)==len(captured)==1
 rt,root=runtimes[0];rt.assert_balanced();assert runtime_state(rt)==root
 assert value.action is None or value.action in __import__('generic_chess.core.movegen',fromlist=['legal_actions']).legal_actions(session.state,session.compiled)
 return value,wall,record_value(captured[0])
try:
 Runtime.attach_stats=attach;pm.SearchStatistics=factory
 for root_name in D['roots']:
  stopped();case=next(c for c in CASES if c['id']==root_name);c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'));board=CoreBoard(case,c);ev=weighted.weighted(c,VALUES['chess']);session=SimpleNamespace(compiled=c,state=board.initial,_search_witnesses=board.witnesses)
  seed=AlphaBetaPlayer(c,evaluator_override=ev,use_native_semantic_legality=True,use_disk_cache=False)
  pm.run_root_search=original
  value,wall,stats=call(seed,session,SearchLimits(max_depth=2,max_nodes=32768,max_time_seconds=60,quiescence_max_depth=4,quiescence_hard_max_depth=8));seed_record=tt_record(seed._tt)
  out['seeds'].append(dict(root=root_name,decision=record_value(value),stats=stats,wall=wall,tt=seed_record,history_witness_count=len(board.witnesses)));save()
  for lineage in D['lineages']:
   for j,cap in enumerate(D['node_caps']):
    for arm in (D['arms'] if j%2==0 else list(reversed(D['arms']))):
     stopped();events=[];p=AlphaBetaPlayer(c,evaluator_override=ev,use_native_semantic_legality=True,use_disk_cache=False)
     if lineage!='cold':p._tt=clone(seed._tt);p._tt_q_depths=seed._tt_q_depths
     before=tt_record(p._tt);pm.run_root_search=original if arm=='baseline' else rr.make_refresh(events,expected_state=board.initial)
     v,wall,stats=call(p,session,SearchLimits(max_depth=D['max_depth'],max_nodes=cap,max_time_seconds=D['per_call_time_guard_seconds'],quiescence_max_depth=4,quiescence_hard_max_depth=8))
     assert tt_record(seed._tt)==seed_record
     row=dict(root=root_name,lineage=lineage,node_cap=cap,arm=arm,decision=record_value(v),stats=stats,events=events,wall_observation=wall,tt_before=before,tt_after=tt_record(p._tt),root_full_runtime_restored=True)
     out['rows'].append(row);save();print(root_name,lineage,cap,arm,'D',v.completed_depth,'q',v.result_ordinary_qdepth,'score',v.score,'work',v.nodes+v.qnodes,'reason',v.termination_reason,flush=True)
 out['complete']=True;out['elapsed_observation_seconds']=time.perf_counter()-started;save()
except BaseException as e:
 out['failure']={'type':type(e).__name__,'message':str(e),'elapsed_seconds':time.perf_counter()-started};save();raise
finally:Runtime.attach_stats=oldattach;pm.SearchStatistics=oldfactory;pm.run_root_search=original
