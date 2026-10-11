"""One changed-premise profile: residual cost after actual material summary."""
import argparse,collections,cProfile,json,pstats,random,sys,time,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import full_q_refresh_comparison as p
from scripts.research_record import write_record,record_value
from scripts.native_capsule_runtime import CapsulePathRuntime
from scripts.native_capsule_evaluator import RuntimeSemanticAttackEvaluator
from scripts.native_capsule_decode import DecodedCapsulePathRuntime
from scripts.native_capsule_inventory import InventoryCapsulePathRuntime
from scripts import native_capsule_inventory as inventory_module
from generic_chess.native import semantic as ns
from generic_chess.ai.alphabeta.search import INF,terminal_score
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.alphabeta.quiescence import enemy_board_count,material_inventory,noisy_child

def side_of(rt):return rt.side_to_move
def include_noisy(action,rt,side,enemies,inventory,poll):return rt.noisy_child(side,enemies,inventory,checkpoint=poll)

def main():
 global d,SelectedRuntime
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--reference',required=True);args=ap.parse_args();b=Path(args.output);b.mkdir(parents=True,exist_ok=True);ref=Path(args.reference)
 if (b/'declaration.json').exists():raise RuntimeError('frozen output exists')
 d=json.loads((ref/'declaration.json').read_text());d['depth']=2;SelectedRuntime=InventoryCapsulePathRuntime
 declaration={'question':'After excluding quiet-child Python projection, is remaining actual checked transition, terminal, decode, attack or recursive scheduling dominant enough to select the next narrow experiment?','reference':str(ref),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'seed':1008,'depth':2,'q':4,'hardq':8,'limits':{'nodes':100000,'seconds':180},'decision':'Same complete score/action/work/trace required; profile overhead is charged and not a paired speed measurement. Inclusive spans overlap, no additive savings. Keep full checked transition/history; do not skip legality from raw action metadata.','cost':'One instrumented completedD2 expectedunder2min,180s bound'};write_record(b/'declaration.json',declaration)
 driver=json.loads((ref/'driver.json').read_text())['source'];exec(compile(driver,'<frozen-inventory-driver>','exec'),globals())
 g=p.generate_game(p.GeneratorConfig(seed=1008,board_size=8,setup_preset='bilateral_random',allow_hybrid=True));src=p.compile_legacy_ruleset_for_semantic_execution(g.ruleset);c=p.SearchMetadataAdapter(ir=src.ir,_legacy_compiled=src._legacy_compiled,support=src.support);config=p.EvaluationConfig();profile=p.build_ruleset_profile(c,config);s=p.GameSession(c);rng=random.Random(8008)
 for _ in range(8):s.submit(rng.choice(sorted(s.legal_actions(),key=repr)))
 counters=collections.Counter();saved={}
 for name in ('terminal_status','make_checked','in_check','transient_legal_actions'):
  old=getattr(ns,name);saved[name]=old
  def wrapped(*a,_name=name,_old=old,**kw):counters[_name]+=1;return _old(*a,**kw)
  setattr(ns,name,wrapped)
 oldsummary=inventory_module.material_summary
 def summary(*a,**kw):counters['material_summary']+=1;return oldsummary(*a,**kw)
 inventory_module.material_summary=summary
 ev=RuntimeSemanticAttackEvaluator(c,profile,config);prof=cProfile.Profile();start=time.perf_counter()
 try:prof.enable();value=search(c,s.state,s._search_history_witnesses,ev,True);prof.disable()
 finally:
  for name,old in saved.items():setattr(ns,name,old)
  inventory_module.material_summary=oldsummary
 elapsed=time.perf_counter()-start;expected=next(r for r in json.loads((ref/'result.json').read_text())['rows'] if r['seed']==1008 and r['mode']=='native-summary')
 assert value['reason']=='complete' and all(value[k]==expected[k] for k in ('score','action','work','trace')) and value['root_restored']
 functions=[{'file':k[0],'line':k[1],'function':k[2],'primitive_calls':v[0],'calls':v[1],'self_seconds':v[2],'inclusive_seconds':v[3]} for k,v in pstats.Stats(prof).stats.items()]
 functions.sort(key=lambda r:r['self_seconds'],reverse=True);write_record(b/'result.json',{'complete':True,'caller_seconds':elapsed,'actual_calls':dict(counters),'actual_attack_queries':ev.attack_queries,'search':value,'functions':functions});print('complete',elapsed,'actualcalls',dict(counters));print(functions[:15])
if __name__=='__main__':main()
