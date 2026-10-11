import ast,copy,hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
R=Path.cwd();sys.path.insert(0,str(R/'.local_agent/pinned_bebe'));B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'results/dev_aux/task077'))
from candidate import SnapshotEvaluator
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.session.session import GameSession
from scripts.research_record import record_value
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
src=compile_semantic_ruleset(build_western_chess_ruleset());assert src._legacy_compiled is not None
c=SearchMetadataAdapter(ir=src.ir,_legacy_compiled=src._legacy_compiled,support=src.support);n=compile_native_semantic_rules(c);cfg=EvaluationConfig();profile=build_ruleset_profile(c,cfg);ev=Evaluator(c,profile,cfg);candidate=SnapshotEvaluator(ev,n);initial=GameSession(c).state.position
rows=[]
for owner in (0,1):
 board=[None]*64;board[0]=Piece(0,'K','K',False);board[63]=Piece(1,'K','K',False);board[27]=Piece(owner,'P','P',False)
 pos=Position(tuple(board),(Hands(),Hands()),0,c.ruleset_fingerprint,initial.aux_state);packed=ns.pack_current_position(n,pos,ply_count=0);state=SimpleNamespace(position=pos)
 py=[{square_to_index(s,8) for s in pseudo_attacks(pos,o,c)} for o in (0,1)];nat=[set(ns.attacked_squares(n,packed,o)) for o in (0,1)];rows.append({'pawn_owner':owner,'python_score':ev.evaluate(state),'rawNative_score':candidate.evaluate_capsule(packed),'python_maps':[sorted(s) for s in py],'Native_maps':[sorted(s) for s in nat],'map_equal':[py[o]==nat[o] for o in (0,1)],'position':record_value(pos)})
out={'complete':True,'rows':rows,'ruleset_fingerprint':c.ruleset_fingerprint,'scope':'Western semanticpawnattacks differ fromlegacy movementatoms inspection;syntheticisolated positions;no terminal/history/gamepriceclaim'}
(B/'result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out))
