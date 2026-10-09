"""Single cold generated-root profile to choose a Core execution hotspot.
No teacher/price/strength comparison. Profiling adds overhead; old caller caps
unchanged. Source cohort recovered from source-prior-diagnosis-relative.zip, or live
ignored declaration. D3/2048nodes/2seconds, fixed Unit ordering/v3 leaf, q0.
Keep only normalized project function paths, no raw private-path profiler dump.
"""
from pathlib import Path
import cProfile,pstats,json,sys,time,hashlib,zipfile
sys.path.insert(0,str(Path.cwd()))
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.unfamiliar_search import validate_pv
from scripts.research_record import record_value
p=Path(__file__).parent;out=p/'source-prior-caller-profile.json';assert not out.exists()
with zipfile.ZipFile(p/'source-prior-diagnosis-relative.zip') as z:raw=z.read('.local_agent/source-prior-transfer-20261009/declaration.json')
case=json.loads(raw)['rules'][1];c=compile_ruleset_for_execution(ruleset_from_dict(case['rules']));s=GameSession(c);before=s.state;cfg=EvaluationConfig(dynamic_mobility_weight=0,anchor_escape_weight=0,promotion_potential_weight=0);profile,_=build_semantic_opportunity_profile(c,cfg)
anchors={t.type_id for t in c.piece_types if t.is_anchor}
class FixedOrder:
 def __init__(self):self.leaf=Evaluator(c,profile,cfg)
 def evaluate(self,state):return self.leaf.evaluate(state)
 def capture_order_value(self,moving,captured):return (0 if captured.current_type_id in anchors else 1000)*10-(0 if moving.current_type_id in anchors else 1000)//10
 def type_value(self,t):return 0 if t in anchors else 1000
player=AlphaBetaPlayer(c,evaluator_override=FixedOrder(),use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False));prof=cProfile.Profile();start=time.perf_counter();prof.enable();decision=player.choose_action(s,SearchLimits(max_depth=3,max_nodes=2048,max_time_seconds=2,quiescence_max_depth=0,quiescence_hard_max_depth=0));prof.disable();seconds=time.perf_counter()-start;validate_pv(s,decision);assert s.state==before
rows=[];root=Path.cwd().resolve()
for (filename,line,name),(primitive,calls,total,cumulative,callers) in pstats.Stats(prof).stats.items():
 f=Path(filename)
 if f.is_absolute() and f.is_relative_to(root) and not f.is_relative_to(root/'.venv'):rows.append(dict(file=f.relative_to(root).as_posix(),line=line,function=name,calls=calls,self_seconds=total,cumulative_seconds=cumulative))
rows.sort(key=lambda r:r['cumulative_seconds'],reverse=True)
report=dict(scope=__doc__,seed=case['seed'],declaration_sha256=hashlib.sha256(raw).hexdigest(),seconds=seconds,decision=record_value(decision),top_project_functions=rows[:25],limitations='Inclusive cumulative times overlap; profiled deadline changes effective node count, no additive decomposition or unprofiled speed estimate. Never bypass Native App Control.')
out.write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps(rows[:14],indent=2))
