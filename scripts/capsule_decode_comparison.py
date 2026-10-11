"""Bounded same-semantic evaluator comparison on the existing thin driver."""
import argparse,ast,collections,hashlib,json,random,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import full_q_refresh_comparison as p
from scripts.research_record import record_value,write_record
from scripts.native_capsule_runtime import CapsulePathRuntime
from scripts.native_capsule_evaluator import RuntimeSemanticAttackEvaluator
from scripts.native_capsule_decode import DecodedCapsulePathRuntime
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.alphabeta.quiescence import enemy_board_count,material_inventory,noisy_child
from generic_chess.ai.alphabeta.search import INF,terminal_score
from generic_chess.ai.alphabeta.statistics import SearchStatistics

args=argparse.ArgumentParser();args.add_argument('--output',required=True);args.add_argument('--driver-source',required=True);args.add_argument('--depth',type=int,default=2);opts=args.parse_args()
B=Path(opts.output);B.mkdir(parents=True,exist_ok=True)
if (B/'declaration.json').exists():raise RuntimeError('frozen output exists')
d=dict(question='Does existing validated packed-action decoding and bounded public syntax reuse reduce the same capsule caller cost, or is its Python validation more costly than C public_action conversion?',roots=['1006-ply8','1008-ply8'],depth=opts.depth,q=4,hardq=8,nodes=100000,seconds=180,orders=2,modes=['public-action','validated-decode'],calls=8,expected_seconds='~5-15min from earlierD2work; bounded interruptible, overall45min ceiling',decision='Any complete score/action/work/trace mismatch rejects bridge. Equal work supports backend/import attribution only. Cap remainsUNKNOWN without extension. Any mismatch rejects decoder. Negative/noise-size saving keeps public_action; measurable saving selects scoped decoder integration. Cache never bypasses decode validation.',scope='Existing exposed two generated roots. Same frozen profile/formula but SEMANTIC attack authority for every mode; not legacy comparison, default/UI replacement or full AlphaBeta integration.',source_hashes={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in [__file__,'scripts/native_capsule_runtime.py','scripts/native_capsule_evaluator.py','scripts/native_capsule_decode.py',opts.driver_source]})
write_record(B/'declaration.json',d)
fn=next(n for n in ast.parse(Path(opts.driver_source).read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='search')
code=ast.unparse(fn).replace('rt = SearchPathRuntime(initial, c, history_witnesses=witnesses, legal_binding_provider=provider)','rt = SelectedRuntime(initial, c, witnesses)\n    if hasattr(ev, "bind_runtime"):\n        ev.bind_runtime(rt)\n    saved_view = rt.state').replace('p.runtime_state(rt)','rt.full_snapshot()').replace('rt.assert_balanced()','assert rt.state == saved_view\n    rt.assert_balanced()')
code=code.replace('root_restored=True)', 'root_restored=True,views=rt.views,transitions=rt.transitions,decoded_actions=getattr(rt,\"decoded_actions\",0),cache_hits=getattr(rt,\"public_cache_hits\",0),cache_misses=getattr(rt,\"public_cache_misses\",0))')
exec(compile(code,'<capsule-interface-fixed-driver>','exec'),globals());write_record(B/'driver.json',dict(source=code,limits='NoTT/declaration interface; root view exact position/ply/terminal plus fullNativehistory snapshot'))
roots=[]
for seed in (1006,1008):
 g=p.generate_game(p.GeneratorConfig(seed=seed,board_size=8,setup_preset='bilateral_random',allow_hybrid=True));src=p.compile_legacy_ruleset_for_semantic_execution(g.ruleset);c=p.SearchMetadataAdapter(ir=src.ir,_legacy_compiled=src._legacy_compiled,support=src.support);config=p.EvaluationConfig();profile=p.build_ruleset_profile(c,config);session=p.GameSession(c);rng=random.Random(seed+7000)
 for _ in range(8):session.submit(rng.choice(sorted(session.legal_actions(),key=repr)))
 roots.append((seed,c,config,profile,session))
checks=[]
for seed,c,config,profile,s in roots:
 rt=CapsulePathRuntime(s.state,c,s._search_history_witnesses);ref=SemanticAttackEvaluator(c,profile,config,backend='core');imp=SemanticAttackEvaluator(c,profile,config,backend='native');bound=RuntimeSemanticAttackEvaluator(c,profile,config);bound.bind_runtime(rt);root=rt.state
 for a in [None]+sorted(rt.legal_actions(),key=repr)[:16]:
  if a is not None:rt.push(a)
  try:
   scores=[e.evaluate(rt.state) for e in (ref,imp,bound)];maps=[e._attack_maps(rt.state) for e in (ref,imp,bound)];assert scores[0]==scores[1]==scores[2] and maps[0]==maps[1]==maps[2];checks.append(dict(seed=seed,action=record_value(a),score=scores[0],ply=rt.ply_count))
  finally:
   if a is not None:rt.pop()
 assert rt.state==root
write_record(B/'leaf_checks.json',dict(complete=True,rows=checks,mismatches=0))
rows=[];batch_start=time.perf_counter()
for seed,c,config,profile,s in roots:
 for order in range(2):
  for mode in (d['modes'] if order==0 else list(reversed(d['modes']))):
   p.rr.stopped()
   if time.perf_counter()-batch_start>2700:raise RuntimeError('overall45min bound reached; partial retained')
   SelectedRuntime=CapsulePathRuntime if mode=='public-action' else DecodedCapsulePathRuntime
   t=time.perf_counter();ev=RuntimeSemanticAttackEvaluator(c,profile,config);result=search(c,s.state,s._search_history_witnesses,ev,True);elapsed=time.perf_counter()-t
   rows.append(dict(seed=seed,order=order,mode=mode,caller_seconds=elapsed,leaf_imports=0,attack_queries=ev.attack_queries,**result));write_record(B/'result.json',dict(complete=False,rows=rows));print(seed,order,mode,result['reason'],round(elapsed,3),result['score'],flush=True)
  group=rows[-2:]
  if all(r['reason']=='complete' for r in group):assert all(group[0][k]==r[k] for r in group[1:] for k in ('score','action','work','trace'))
write_record(B/'result.json',dict(complete=True,rows=rows,elapsed_seconds=time.perf_counter()-batch_start))
