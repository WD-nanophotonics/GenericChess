import ast,collections,copy,hashlib,json,random,sys,time
from pathlib import Path
from types import SimpleNamespace
R=Path.cwd();sys.path.insert(0,str(R/'.local_agent/pinned_bebe'));B=Path(__file__).resolve().parent;D=json.loads((B/'DECLARATION.json').read_bytes());E=R/'.local_agent/fixed_q4_tradeoff/.local_agent'
from scripts.research_record import record_value
from generic_chess.generation.generator import generate_game
from generic_chess.generation.config import GeneratorConfig
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.session.session import GameSession
from generic_chess.core.position import Position,Hands
from generic_chess.core.pieces import Piece
from generic_chess.core.terminal import TerminalResult,TerminalStatus
from generic_chess.core.coordinates import index_to_square
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.alphabeta.quiescence import enemy_board_count,material_inventory,noisy_child
from generic_chess.ai.alphabeta.search import INF,terminal_score
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.mirror import pack_semantic_action
from generic_chess.native import semantic as ns
meta=(E/'q4-prospective-20261011-repaired/producer.py').read_bytes();cls=next(x for x in ast.parse(meta).body if isinstance(x,ast.ClassDef) and x.name=='SearchMetadataAdapter');exec(compile(ast.Module(body=[cls],type_ignores=[]),'<frozenmetadata>','exec'),globals())
# Use the already validated projection-ply continuation for botharms.
exec(compile((R/'results/dev_aux/task074/proposed_adapter.py').read_bytes(),'<auxiliary capsule projection fix>','exec'),globals())
source=(E/'native-capsule-q4-20261011/driver.json').read_bytes();driver=json.loads(source)['changed_function'];driver=driver.replace('rt = CapsuleRuntime(initial, c, witnesses)','rt = CapsuleRuntime(initial, c, witnesses)\n    if ARM == "Native_attackmaps_only":\n        ev = copy.copy(ev)\n        ev._attack_maps = lambda state: tuple(frozenset(index_to_square(x,c.board_size) for x in ns.attacked_squares(rt.native,rt.capsule,owner)) for owner in (0,1))');exec(compile(driver,'<same lexical driver with map source choice>','exec'),globals());d={'depth':2,'q':4,'hardq':8,'nodes':100000,'seconds':90}
roots=[];sample=json.loads((E/'q4-prospective-20261011-repaired/samples.json').read_bytes())['samples']
for seed in (1006,1008):
 g=generate_game(GeneratorConfig(seed=seed,board_size=8,setup_preset='bilateral_random',allow_hybrid=True));src=compile_legacy_ruleset_for_semantic_execution(g.ruleset);c=SearchMetadataAdapter(ir=src.ir,_legacy_compiled=src._legacy_compiled,support=src.support);cfg=EvaluationConfig();prof=build_ruleset_profile(c,cfg);ev=Evaluator(c,prof,cfg);s=GameSession(c);rng=random.Random(seed+7000)
 for ply in range(9):
  if ply in (0,8):
   name=f'seed{seed}-ply{ply}';old=next(x for x in sample if x.get('root')==name);assert record_value(s.state)==old['initial'] and record_value(prof)==old['profile'];roots.append((name,c,s.state,s._search_history_witnesses,ev))
  if ply<8:s.submit(rng.choice(sorted(s.legal_actions(),key=repr)))
class StopCheck:
 @staticmethod
 def stopped():
  for root in (R,Path('C:/Users/wdai/Documents/ChatGPT/GenericChess 2')):
   for file in ('rollout.json','advisor.json','slack.json'):
    p=root/'.local_agent'/file;x=json.loads(p.read_bytes());assert not x.get('user_paused') and not x.get('stopped') and not x.get('pause_reason'),'stopflag'
rows=[];started=time.perf_counter();p=SimpleNamespace(rr=StopCheck)
for name,c,initial,w,ev in roots:
 for order in range(2):
  for ARM in (D['arms'] if order==0 else D['arms'][::-1]):
   StopCheck.stopped();assert time.perf_counter()-started<1500
   t=time.perf_counter();v=search(c,initial,w,ev,True);caller=time.perf_counter()-t;rows.append({'root':name,'order':order,'arm':ARM,'caller_seconds':caller,**v});(B/'result.json').write_bytes((json.dumps({'complete':False,'rows':rows},separators=(',',':'))+'\n').encode());print(name,order,ARM,v['reason'],v['score'],round(caller,3),flush=True)
(B/'result.json').write_bytes((json.dumps({'complete':True,'rows':rows,'batch_seconds':time.perf_counter()-started,'scope':'NewNativeattackmap premise inprivatefrozendriver;projectionfixshared;sequentialoppositeorders notexclusive/Elo/defaultacceptance.'},separators=(',',':'))+'\n').encode())
