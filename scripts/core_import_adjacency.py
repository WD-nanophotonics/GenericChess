"""Finite import adjacency diagnostic; no cache or timing comparison."""
import argparse,hashlib,json,random,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import full_q_refresh_comparison as p
from scripts.research_record import write_record,record_value
from scripts.native_core_availability import NativeCoreAvailability
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.ai.limits import SearchLimits
from generic_chess.native import semantic as ns
from collections import Counter
ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);b=Path(ap.parse_args().output);b.mkdir(parents=True,exist_ok=True);assert not (b/'declaration.json').exists()
write_record(b/'declaration.json',dict(question='Is a single-position import reuse likely to save actual repeated packing, and do its ply contracts align?',seeds=[1051,1052],ply=8,walk_seed_offset=7000,depth=2,q=4,hardq=8,nodes=100000,seconds=30,calls=2,decision='Measure adjacent identity and identity+ply counts only. No cache/adoption/default change. Ignore speed because instrumentation changes cost. Reject blind reuse when ply differs; use counts to choose next interface work.',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
rows=[]
for seed in [1051,1052]:
 g=p.generate_game(p.GeneratorConfig(seed=seed,board_size=8,setup_preset='bilateral_random',allow_hybrid=True));src=p.compile_legacy_ruleset_for_semantic_execution(g.ruleset);c=p.SearchMetadataAdapter(ir=src.ir,_legacy_compiled=src._legacy_compiled,support=src.support);ec=p.EvaluationConfig();profile=p.build_ruleset_profile(c,ec);session=p.GameSession(c);rng=random.Random(seed+7000)
 for _ in range(8):session.submit(rng.choice(sorted(session.legal_actions(),key=repr)))
 counts=Counter();adjacent=Counter();compatible=Counter();last=[None,None,None];old_legal=NativeSemanticLegalityProvider.__call__;old_attack=ns.pack_current_position
 def observe(role,position,ply):
  counts[role]+=1
  if last[1] is position:
   adjacent[last[0]+'->'+role]+=1
   if last[2]==ply:compatible[last[0]+'->'+role]+=1
  last[:]=[role,position,ply]
 def legal(self,position,ply_count,checkpoint=None):
  observe('legal',position,ply_count);return old_legal(self,position,ply_count,checkpoint)
 def attack(native_rules,position,*,ply_count):
  observe('attack',position,ply_count);return old_attack(native_rules,position,ply_count=ply_count)
 class Query(NativeCoreAvailability):
  def for_position(self,position,checkpoint=None):
   observe('availability',position,0);return super().for_position(position,checkpoint=checkpoint)
 query=Query(c);ev=SemanticAttackEvaluator(c,profile,ec,backend='native');player=AlphaBetaPlayer(c,evaluator_override=ev,use_disk_cache=False,availability_provider=query.for_position)
 NativeSemanticLegalityProvider.__call__=legal;ns.pack_current_position=attack;saved=session.state;t=time.perf_counter()
 try:value=player.choose_action(session,SearchLimits(max_depth=2,max_nodes=100000,max_time_seconds=30,quiescence_max_depth=4,quiescence_hard_max_depth=8))
 finally:NativeSemanticLegalityProvider.__call__=old_legal;ns.pack_current_position=old_attack
 assert session.state==saved
 row=dict(seed=seed,counts=dict(counts),adjacent_same_position=dict(adjacent),adjacent_same_position_and_ply=dict(compatible),availability_imports=query.imports,fallbacks=query.fallbacks,decision=record_value(value),instrumented_seconds=time.perf_counter()-t,parent_restored=True,extra_retained_positions=1)
 rows.append(row);write_record(b/'result.json',dict(complete=False,rows=rows));print(json.dumps(row),flush=True)
write_record(b/'result.json',dict(complete=True,rows=rows))
