"""Actual internal-Xiangqi capture/recapture sensitivity; not price quality.
Hold the root, transitions, hand semantics and normalization fixed; no search.
"""
from pathlib import Path
import hashlib,sys
root=Path.cwd();sys.path.insert(0,str(root))
from dataclasses import replace
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.session.session import GameSession
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from scripts.research_record import record_value,write_record
compiled=compile_ruleset_for_execution(build_xiangqi_diagnostic_ruleset());session=GameSession(compiled);initial=session.state
config=EvaluationConfig(dynamic_mobility_weight=0,anchor_escape_weight=0,promotion_potential_weight=0)
profile,scope=build_semantic_opportunity_profile(compiled,config)
unit={t:0 if meta.is_anchor else 1000 for t,meta in compiled.support.type_metadata.items()}
controls={'unit':replace(profile,board_value_by_type=unit,hand_value_by_base_type=unit),'v3':profile}
evaluators={name:Evaluator(compiled,p,config) for name,p in controls.items()}
def signed(e,state):return e.evaluate(state)*(1 if state.position.side_to_move==0 else -1)
rows=[];transitions=0
for action in legal_actions(initial,compiled):
 child=apply_action(initial,action,compiled);transitions+=1
 # Detect actual material transfer, not a semantic action name.
 before=sum(p is not None and p.owner==1 and p.current_type_id=='H' for p in initial.position.board)
 after=sum(p is not None and p.owner==1 and p.current_type_id=='H' for p in child.position.board)
 if before-after!=1:continue
 for reply in legal_actions(child,compiled):
  final=apply_action(child,reply,compiled);transitions+=1
  c_before=sum(p is not None and p.owner==0 and p.current_type_id=='C' for p in child.position.board)
  c_after=sum(p is not None and p.owner==0 and p.current_type_id=='C' for p in final.position.board)
  if c_before-c_after!=1:continue
  rows.append(dict(capture=record_value(action),reply=record_value(reply),hands=[record_value(x.position.hands) for x in (initial,child,final)],material={name:[signed(e,x) for x in (initial,child,final)] for name,e in evaluators.items()}))
assert rows and session.state==initial
assert any(row['material']['unit']!=row['material']['v3'] for row in rows)
write_record(root/'.local_agent/guard-projection-20261009/rectangle-price-witness.json',dict(scope=__doc__,producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),product_sha256=hashlib.sha256((root/'generic_chess/ai/evaluation/semantic.py').read_bytes()).hexdigest(),transitions=transitions,rows=rows,board_values=dict(profile.board_value_by_type)))
print(dict(witnesses=len(rows),transitions=transitions,material=[r['material'] for r in rows]))
