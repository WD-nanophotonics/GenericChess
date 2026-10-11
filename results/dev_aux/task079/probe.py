import ast,copy,hashlib,json,sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
R=Path.cwd();sys.path.insert(0,str(R/'.local_agent/pinned_bebe'));B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'results/dev_aux/task077'))
from candidate import SnapshotEvaluator
from generic_chess.generation.generator import generate_game
from generic_chess.generation.config import GeneratorConfig
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.core.position import Position,Hands
from generic_chess.core.pieces import Piece
from generic_chess.core.coordinates import index_to_square,square_to_index
from generic_chess.core.attacks import pseudo_attacks
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native import semantic as ns
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
E=R/'.local_agent/fixed_q4_tradeoff/.local_agent';raw=(E/'q4-prospective-20261011-repaired/producer.py').read_bytes();cls=next(x for x in ast.parse(raw).body if isinstance(x,ast.ClassDef) and x.name=='SearchMetadataAdapter');exec(compile(ast.Module(body=[cls],type_ignores=[]),'<fixed metadata adapter>','exec'),globals());cache={};rows=[]
def tuples(v):return tuple(tuples(x) for x in v) if isinstance(v,list) else v
for seed in (1006,1008):
 g=generate_game(GeneratorConfig(seed=seed,board_size=8,setup_preset='bilateral_random',allow_hybrid=True));src=compile_legacy_ruleset_for_semantic_execution(g.ruleset);c=SearchMetadataAdapter(ir=src.ir,_legacy_compiled=src._legacy_compiled,support=src.support);cfg=EvaluationConfig();profile=build_ruleset_profile(c,cfg);cache[seed]=(c,compile_native_semantic_rules(c),Evaluator(c,profile,cfg))
c,n,default=cache[1008]
configs=[default._config,replace(default._config,dynamic_mobility_weight=3,anchor_escape_weight=7,promotion_potential_weight=5),replace(default._config,dynamic_mobility_weight=0,anchor_escape_weight=0,promotion_potential_weight=0)]
evs=[Evaluator(c,default._profile,cfg) for cfg in configs]
candidates=[SnapshotEvaluator(ev,n) for ev in evs]
anchor=next(t for t in n.type_ids if c.types_by_id[t].is_anchor)
rows=[]
for tid in n.type_ids:
 for owner in (0,1):
  for side in (0,1):
   for promoted in (False,True):
    for square in (0,28,63):
     board=[None]*64;board[square]=Piece(owner,tid,tid,promoted)
     for j,o in ((4,0),(59,1),(20,owner)):
      if board[j] is None:board[j]=Piece(o,anchor,anchor,False)
     hands=tuple(Hands(((tid,2 if o==owner else 1),)) for o in (0,1))
     pos=Position(tuple(board),hands,side,c.ruleset_fingerprint,());packed=ns.pack_current_position(n,pos,ply_count=0);state=SimpleNamespace(position=pos)
     py=[ev.evaluate(state) for ev in evs];raw=[ev.evaluate_capsule(packed) for ev in candidates]
     row={'type':tid,'owner':owner,'side':side,'promoted':promoted,'square':square,'python':py,'raw':raw,'equal':py==raw};rows.append(row)
out={'complete':True,'synthetic_states':len(rows),'evaluations':len(rows)*len(configs),'mismatches':[r for r in rows if not r['equal']],'configuration_weights':[[cfg.dynamic_mobility_weight,cfg.anchor_escape_weight,cfg.promotion_potential_weight] for cfg in configs],'rows':rows,'scope':'synthetic field/formula checks withnonzerohands,explicit same-typepromotion,multipleanchors,sides;not legalreachability/terminal/history/fullDSL'}
(B/'result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in out.items() if k!='rows'}))
