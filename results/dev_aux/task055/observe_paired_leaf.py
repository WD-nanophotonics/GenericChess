"""One frozen D2 paired leaf observer; preserve every numerical return."""
import hashlib,importlib.util,json,subprocess,sys,time
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from scripts.search_backend_comparison import CASES,VALUES,CoreBoard,minimal_ab
from scripts.research_record import record_value
from scripts.reserve_refresh_diagnostic import stopped
started=time.monotonic();binary_hash=hashlib.sha256((ROOT/'generic_chess/_native_core.cp312-win_amd64.pyd').read_bytes()).hexdigest();assert binary_hash=='2f97cfb8816bc963163207095bf40ac990169284cd0cfb2e7b545f0a6bf07bf1'
spec=importlib.util.spec_from_file_location('weighted',ROOT/'.local_agent/weighted-backend-20261011/bridge.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
case=next(v for v in CASES if v['id']=='chess-middle');compiled=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'));e=w.weighted(compiled,VALUES['chess']);original=e.evaluate
reference=next(v for v in json.loads((B/'frozen_attribution.json').read_bytes())['rows'] if v['root']==case['id']);rows=[]
try:
 for arm in ('hybrid','specialized'):
  stopped();assert time.monotonic()-started<30
  counters=dict(calls=0,core_seconds=0.);digest=hashlib.sha256()
  def observed(state):
   t=time.perf_counter()
   value=original(state)
   counters['core_seconds']+=time.perf_counter()-t;counters['calls']+=1
   encoded=json.dumps(dict(position=record_value(state.position),score=value),sort_keys=True,separators=(',',':')).encode()
   digest.update(len(encoded).to_bytes(8,'big'));digest.update(encoded)
   return value
  e.evaluate=observed
  if arm=='hybrid':
   provider=NativeSemanticLegalityProvider.try_create(compiled,strict=True);assert provider is not None
   board=CoreBoard(case,compiled,provider);board.material=e
  else:board=w.WeightedChess(case,e,measure=True)
  result=minimal_ab(board,2,seconds=10,node_limit=100000,trace=True)
  assert result['reason']=='completed_depth' and result['completed_depth']==2 and result['move']=='f3e5' and result['score']==-100
  assert result['work']==reference['work'] and board.restored() and counters['calls']==595
  if arm=='hybrid':
   k=result['runtime_counters'];assert k['legal_provider_calls']==36 and k['legal_provider_actions']==1354 and k['legal_provider_fallbacks']==k['legal_provider_operational_failures']==0
  adapter_seconds=getattr(board,'adapter_seconds',0.)
  rows.append(dict(arm=arm,result=result,leaf_observer=counters,ordered_position_score_sha256=digest.hexdigest(),specialized_conversion_seconds=adapter_seconds,root_restored_four_predicates=True,whole_minus_evaluator_core=result['wall_seconds']-counters['core_seconds']))
  print(arm,json.dumps(dict(whole=result['wall_seconds'],core=counters['core_seconds'],conversion=adapter_seconds,calls=counters['calls'],digest=digest.hexdigest())))
finally:e.evaluate=original
assert rows[0]['ordered_position_score_sha256']==rows[1]['ordered_position_score_sha256'] and rows[0]['result']['trace_sha256']==rows[1]['result']['trace_sha256']
h,s=rows;delta_total=h['result']['wall_seconds']-s['result']['wall_seconds'];delta_core=h['leaf_observer']['core_seconds']-s['leaf_observer']['core_seconds']
out=dict(complete=True,product_revision='b4108a68a7ee06327be39cb3a222939644085a52',binary_sha256=binary_hash,rows=rows,observed_delta=dict(whole=delta_total,evaluator_core=delta_core,whole_minus_core=delta_total-delta_core,specialized_conversion=s['specialized_conversion_seconds']),limits='One observed pair. Ordered Position/score and trace correspondence,595calls each; not identical full-history proof or controlled speed measurement. Whole timings include observers/hashing. Same-function cost equality is not guaranteed. Residual is all other observed execution, control and instrumentation, not pure rule cost. Specialist conversion charged separately. No generalization to Shogi/q4 or further repeated cohort.')
(B/'paired_leaf_observer.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print(json.dumps(out['observed_delta']))
