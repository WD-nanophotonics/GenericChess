"""Bounded same-semantic evaluator comparison on the existing thin driver."""
import argparse,ast,collections,hashlib,json,random,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import full_q_refresh_comparison as p
from scripts.research_record import record_value,write_record
from scripts.native_capsule_runtime import CapsulePathRuntime
from scripts.native_capsule_evaluator import RuntimeSemanticAttackEvaluator
from scripts.native_capsule_decode import DecodedCapsulePathRuntime
from scripts.native_capsule_inventory import InventoryCapsulePathRuntime
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.alphabeta.quiescence import enemy_board_count,material_inventory,noisy_child
from generic_chess.ai.alphabeta.search import INF,terminal_score
from generic_chess.ai.alphabeta.statistics import SearchStatistics

args=argparse.ArgumentParser();args.add_argument('--output',required=True);args.add_argument('--driver-source',required=True);args.add_argument('--depth',type=int,default=2);opts=args.parse_args()
B=Path(opts.output);B.mkdir(parents=True,exist_ok=True)
if (B/'declaration.json').exists():raise RuntimeError('frozen output exists')
d=dict(question='Under one shared caller deadline, does identical full-q iterative thin search deliver a deeper complete result when actual material summary avoids quiet-child projections?',roots=['1041-ply8','1042-ply8'],depth=3,q=4,hardq=8,nodes=100000,seconds=180,orders=2,modes=['projected-inventory','native-summary'],calls=16,budgets=[10,30],depths=[1,2,3],expected_seconds='Maximum320searchseconds plus constructor/setup; expected5-8min; interruptible, overall10min bound',decision='Any complete score/action/work/trace mismatch rejects bridge. Equal work supports backend/import attribution only. Cap remainsUNKNOWN without extension. Any mismatch rejects decoder. Count/noisy-policy or complete work mismatch rejects summary. No timing benefit retains existing projected inventory. Measured cost plus actual view/summary/terminal counts selects only scoped thin interface.',scope='Two previously undeclared delivery roots; generated cohort1041 was previously exposed with a DIFFERENT seed+17000 walk. This is developmental transfer, not an unexposed holdout. Same frozen profile/formula but SEMANTIC attack authority for every mode; not legacy comparison, default/UI replacement or full AlphaBeta integration.',source_hashes={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in [__file__,'scripts/native_capsule_runtime.py','scripts/native_capsule_evaluator.py','scripts/native_capsule_decode.py','scripts/native_capsule_inventory.py','generic_chess/native/semantic.py','generic_chess/_native/native_module.c',opts.driver_source]})
write_record(B/'declaration.json',d)
fn=next(n for n in ast.parse(Path(opts.driver_source).read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='search')
code=ast.unparse(fn).replace('rt = SearchPathRuntime(initial, c, history_witnesses=witnesses, legal_binding_provider=provider)','rt = SelectedRuntime(initial, c, witnesses)\n    if hasattr(ev, "bind_runtime"):\n        ev.bind_runtime(rt)\n    saved_view = rt.state').replace('p.runtime_state(rt)','rt.full_snapshot()').replace('rt.assert_balanced()','assert rt.state == saved_view\n    rt.assert_balanced()')
code=code.replace('root_restored=True)', 'root_restored=True,views=rt.views,transitions=rt.transitions,decoded_actions=getattr(rt,\"decoded_actions\",0),cache_hits=getattr(rt,\"public_cache_hits\",0),cache_misses=getattr(rt,\"public_cache_misses\",0))')
def side_of(rt):
 return rt.side_to_move if isinstance(rt,InventoryCapsulePathRuntime) else rt.position.side_to_move
def include_noisy(action,rt,side,enemies,inventory,poll):
 if isinstance(rt,InventoryCapsulePathRuntime):return rt.noisy_child(side,enemies,inventory,checkpoint=poll)
 return noisy_child(action,rt.state,side,enemies,inventory,lambda:rt.in_check(rt.position.side_to_move,checkpoint=poll))
old="        side = rt.position.side_to_move\n        enemies = enemy_board_count(rt.position, side)\n        inventory = material_inventory(rt.position)"
new="        side = side_of(rt)\n        if isinstance(rt,InventoryCapsulePathRuntime):\n            summary=rt.material_summary()\n            enemies=summary[2][1-side]\n            inventory=summary[3]\n        else:\n            enemies=enemy_board_count(rt.position,side)\n            inventory=material_inventory(rt.position)"
assert old in code;code=code.replace(old,new)
old="noisy_child(action, rt.state, side, enemies, inventory, lambda: rt.in_check(rt.position.side_to_move, checkpoint=poll))"
assert old in code;code=code.replace(old,"include_noisy(action,rt,side,enemies,inventory,poll)")
code=code.replace('rt.position.side_to_move','side_of(rt)')
code=code.replace('root_restored=True,','root_restored=True,summary_calls=getattr(rt,"summary_calls",0),')
code=code.replace("if time.perf_counter() - start >= d['seconds']:","if time.perf_counter() >= GLOBAL_DEADLINE:")
exec(compile(code,'<capsule-interface-fixed-driver>','exec'),globals());write_record(B/'driver.json',dict(source=code,limits='NoTT/declaration interface; root view exact position/ply/terminal plus fullNativehistory snapshot'))
roots=[]
for seed in (1041,1042):
 g=p.generate_game(p.GeneratorConfig(seed=seed,board_size=8,setup_preset='bilateral_random',allow_hybrid=True));src=p.compile_legacy_ruleset_for_semantic_execution(g.ruleset);c=p.SearchMetadataAdapter(ir=src.ir,_legacy_compiled=src._legacy_compiled,support=src.support);config=p.EvaluationConfig();profile=p.build_ruleset_profile(c,config);session=p.GameSession(c);rng=random.Random(seed+7000)
 for _ in range(8):
  if session.result.status.value != 'ongoing':break
  actions=sorted(session.legal_actions(),key=repr)
  if not actions:break
  session.submit(rng.choice(actions))
 if session.result.status.value != 'ongoing' or session.state.ply_count != 8:
  write_record(B/('unavailable-'+str(seed)+'.json'),dict(seed=seed,state=record_value(session.state),result=record_value(session.result),policy='No resampling or extension'));continue
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
write_record(B/'samples.json',[dict(seed=seed,state=record_value(s.state),witnesses=record_value(s._search_history_witnesses),profile=record_value(profile)) for seed,c,config,profile,s in roots])
for seed,c,config,profile,s in roots:
 fallback=sorted(s.legal_actions(),key=repr)[0]
 for seconds in d['budgets']:
  for order in range(2):
   for mode in (d['modes'] if order==0 else list(reversed(d['modes']))):
    p.rr.stopped()
    if time.perf_counter()-batch_start>600:raise RuntimeError('overall10min bound reached; partial retained')
    SelectedRuntime=DecodedCapsulePathRuntime if mode=='projected-inventory' else InventoryCapsulePathRuntime
    t=time.perf_counter();GLOBAL_DEADLINE=t+seconds
    ev=RuntimeSemanticAttackEvaluator(c,profile,config);events=[];completed=None;visits=0
    for depth in (1,2,3):
     if time.perf_counter()>=GLOBAL_DEADLINE or visits>=100000:break
     d['depth']=depth;d['nodes']=100000-visits
     v=search(c,s.state,s._search_history_witnesses,ev,True);visits+=v['work'].get('main',0)+v['work'].get('q',0);events.append(dict(depth=depth,**v))
     if v['reason']=='complete':completed=events[-1]
     else:break
    elapsed=time.perf_counter()-t
    row=dict(seed=seed,seconds=seconds,order=order,mode=mode,caller_seconds=elapsed,completed_depth=completed['depth'] if completed else 0,action=completed['action'] if completed else record_value(fallback),score=completed['score'] if completed else None,result_source='full_iteration' if completed else 'legal_fallback',events=events,visits=visits,actual_attack_queries=ev.attack_queries,root_restored=all(x['root_restored'] for x in events))
    rows.append(row);write_record(B/'result.json',dict(complete=False,rows=rows));print(seed,seconds,order,mode,row['completed_depth'],row['score'],round(elapsed,3),flush=True)
write_record(B/'result.json',dict(complete=True,rows=rows,elapsed_seconds=time.perf_counter()-batch_start))
