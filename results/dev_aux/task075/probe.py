import ast,copy,hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
R=Path.cwd();sys.path.insert(0,str(R/'.local_agent/pinned_bebe'));B=Path(__file__).resolve().parent
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
old=json.loads((E/'native-leaf-compatibility-20261011/result.json').read_bytes());assert len(old['rows'])==68
for i,row in enumerate(old['rows']):
 seed=int(row['root'].split('-')[0]);c,n,ev=cache[seed];v=row['position'];pos=Position(tuple(None if p is None else Piece(**p) for p in v['board']),tuple(Hands(tuples(h['counts'])) for h in v['hands']),v['side_to_move'],v['ruleset_fingerprint'],tuples(v['aux_state']));state=SimpleNamespace(position=pos);assert ev.evaluate(state)==row['python'];packed=ns.pack_current_position(n,pos,ply_count=0)
 py=[{square_to_index(x,8) for x in pseudo_attacks(pos,o,c)} for o in (0,1)];nat=[set(ns.attacked_squares(n,packed,o)) for o in (0,1)];candidate=copy.copy(ev);candidate._attack_maps=lambda st:tuple(frozenset(index_to_square(x,8) for x in xs) for xs in nat);score=candidate.evaluate(state)
 rows.append({'index':i,'root':row['root'],'action':row['action'],'python_score':row['python'],'candidate_score':score,'score_equal':score==row['python'],'map_equal':[py[o]==nat[o] for o in (0,1)],'python_maps':[sorted(x) for x in py],'native_maps':[sorted(x) for x in nat],'extraNative':[sorted(nat[o]-py[o]) for o in (0,1)],'missingNative':[sorted(py[o]-nat[o]) for o in (0,1)]})
out={'complete':True,'records':len(rows),'owner_maps':136,'owner_map_mismatches':sum(not x for r in rows for x in r['map_equal']),'score_mismatches':sum(not r['score_equal'] for r in rows),'rows':rows,'scope':'Existing frozen68leaf subset with scalar semantic attackauthority versus Legacy geometry pseudoattacks;candidate mapsonly, frozenmaterial/promotion/anchorunchanged. No arbitrarydomain/deployment/speedclaim.'};(B/'result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in out.items() if k!='rows'}))
