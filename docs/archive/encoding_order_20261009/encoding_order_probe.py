"""Does equivalent transformation spelling alter public ordering cost?

Existing effect/explicit fixture, unchanged physical transitions and one fixed
legacy-profile evaluator. D3/4096nodes/5sec/q0, TT on/root scan off, sorted and
staged, two rotated repeats. Two full-width D3 Core references. Changed premise
is ordering representation, not another qsupport test. Caps stay unknown; exact
scores must agree on completed depth. No price/default/strength conclusion.
"""
from rect_probe import *
sys.path.insert(0,str(root/'tests/product'))
from test_qsearch_semantic_effects import transform_rules
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.core.transition import legal_successors
from generic_chess.ai.alphabeta.ordering import MoveOrderer,StagedMovePicker
from generic_chess.ai.alphabeta.statistics import SearchStatistics

def main():
 p=Path(__file__).parent;out=p/'encoding-order-probe.json';assert not out.exists()
 r=dict(complete=False,declaration=__doc__,cases=[]);physical=[]
 for encoding in ('effect','explicit'):
  definition=transform_rules(encoding=encoding);c=compile_ruleset_for_execution(definition);s=GameSession(c)
  children=[nxt.position for a,nxt in legal_successors(s.state,c) if getattr(a,'pattern_id','').startswith('sem_')]
  assert len(children)==1;physical.append(children[0])
  cfg=EvaluationConfig(dynamic_mobility_weight=0,anchor_escape_weight=0,promotion_potential_weight=0)
  ev=Evaluator(c,build_ruleset_profile(c,cfg),cfg);counted=CountedEvaluator(ev,seconds=5,evaluations=4096)
  ref,_=reference_minimax(s.state,3,counted,c)
  row=dict(encoding=encoding,rules=ruleset_to_dict(definition),reference_score=ref,reference_leaves=counted.calls,searches=[],ordering=[]);r['cases'].append(row)
  for staged in (False,True):
   tuning=SearchTuning(use_root_tactical=False,use_staged_move_picker=staged);orderer=MoveOrderer();actions=list(s.legal_actions())
   ordered=list(StagedMovePicker(s.state,actions,ev,3,None,None,orderer,tuning,SearchStatistics())) if staged else orderer.order(s.state,actions,ev,3,None,None,tuning)
   row['ordering'].append(dict(staged=staged,actions=[record_value(a) for a in ordered]))
  for repeat in (0,1):
   for staged in ((False,True) if repeat==0 else (True,False)):
    player=AlphaBetaPlayer(c,evaluator_override=ev,use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False,use_staged_move_picker=staged));before=s.state;t=time.perf_counter()
    dec=player.choose_action(s,SearchLimits(max_depth=3,max_nodes=4096,max_time_seconds=5,quiescence_max_depth=0,quiescence_hard_max_depth=0));validate_pv(s,dec);assert s.state==before
    if dec.completed_depth==3:assert dec.score==ref
    row['searches'].append(dict(staged=staged,repeat=repeat,seconds=time.perf_counter()-t,decision=record_value(dec)));write_record(out,r)
 assert physical[0]==physical[1]
 r['complete']=True;r['same_physical_semantic_child']=True;r['producer_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();write_record(out,r)
 print([(z['encoding'],z['reference_score'],[(x['staged'],x['decision']['completed_depth'],x['decision']['nodes']) for x in z['searches']]) for z in r['cases']])
if __name__=='__main__':main()
