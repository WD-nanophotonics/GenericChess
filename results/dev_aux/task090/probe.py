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
from generic_chess.core.semantic_executor import semantic_engine_for
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
from dataclasses import replace
from generic_chess.rules.schema import ruleset_from_dict,RuleStateGuard,RuleTypeRef,RuleSpatialSelector,RuleSquareRef
old=next(r for r in json.loads((R/'results/dev_aux/task057/result.json').read_bytes())['rows'] if r['case']=='any')
rules=ruleset_from_dict(old['ruleset']);guard=RuleStateGuard('count','any',RuleTypeRef('any'),'current','any','board',RuleSpatialSelector('exact',(RuleSquareRef('offset_from_source',offset=(0,1)),)))
rules=replace(rules,semantic_actions=tuple(replace(a,state_guards=a.state_guards+(guard,)) if a.name=='capture_B0_A0_leap' else a for a in rules.semantic_actions));src=compile_semantic_ruleset(rules);c=SearchMetadataAdapter(ir=src.ir,_legacy_compiled=src._legacy_compiled,support=src.support);n=compile_native_semantic_rules(c);cfg=EvaluationConfig();profile=build_ruleset_profile(c,cfg);ev=Evaluator(c,profile,cfg);candidate=SnapshotEvaluator(ev,n);engine=semantic_engine_for(c);semantic_ev=copy.copy(ev);semantic_ev._attack_maps=lambda state:tuple(frozenset(index_to_square(t,7) for t in engine.attacked_squares(state.position,o)) for o in (0,1));rows=[]
for blocker in (False,True):
 board=[None]*49
 for j,p in ((0,Piece(0,'H0','H0')), (48,Piece(1,'H0','H0')), (8,Piece(0,'B0','B0')), (9,Piece(1,'A0','A0'))):board[j]=p
 if blocker:board[15]=Piece(0,'B0','B0')
 pos=Position(tuple(board),(Hands(),Hands()),0,c.ruleset_fingerprint,());packed=ns.pack_current_position(n,pos,ply_count=0);core=[engine.attacked_squares(pos,o) for o in (0,1)];native=[ns.attacked_squares(n,packed,o) for o in (0,1)];score=semantic_ev.evaluate(SimpleNamespace(position=pos));raw=candidate.evaluate_capsule(packed)
 assert core==native and score==raw and ((9 in core[0])== (not blocker))
 rows.append({'blocker':blocker,'Core_maps':[sorted(x) for x in core],'Native_maps':[sorted(x) for x in native],'Core_score':score,'raw_score':raw,'target9attacked':9 in core[0]})
out={'complete':True,'rows':rows,'scope':'twoasymmetricguardedsemanticstates commonattackauthority only;no fullprice/legality/history/domain or deployment'};(B/'result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out))
