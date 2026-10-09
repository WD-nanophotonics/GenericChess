"""D3 decision-changing horizon check at first qualifying frozen root102.
No D4 extension from this run; independent reference keeps4096/5sec fuse.
First frozen no-win root with actual equal-unit/nonzero-v3 exchange.
Exposed development selection, never population performance. Fix unit ordering,
Core, cold state/TT,4096nodes/10seconds. D2q0 fullwidth oracle and D2q2hard8;
do not extend a capped cell. Report chosen action and actual legal replies.
"""
from pathlib import Path
from dataclasses import replace
import sys,json,time,hashlib
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.core.transition import apply_action
from generic_chess.core.movegen import legal_actions
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.alphabeta.search import reference_minimax
from generic_chess.ai.limits import SearchLimits
from scripts.unfamiliar_search import CountedEvaluator,validate_pv,ReferenceLimit
from scripts.research_record import record_value,write_record
folder=Path(__file__).parent;out=folder/'exchange-depth3.json';assert not out.exists()
frontier=json.loads((folder/'exchange-frontier.json').read_bytes())
selected=[]
for r in frontier['rows']:
    if r['delta']['unit']==0 and r['delta']['v3'] and r['seed'] not in selected:selected.append(r['seed'])
selected=selected[:1]
frozen=json.loads((folder/'opening-preflight.json').read_bytes())
result=dict(scope=__doc__,producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),selected_seeds=selected,cases=[],complete=False)
config=EvaluationConfig(dynamic_mobility_weight=0,anchor_escape_weight=0,promotion_potential_weight=0)
for case in frozen['cases']:
    if case['seed'] not in selected:continue
    c=compile_ruleset_for_execution(ruleset_from_dict(case['rules']));s=GameSession(c);before=s.state
    p,scope=build_semantic_opportunity_profile(c,config)
    unit={t:0 if pt.is_anchor else 1000 for t,pt in c.types_by_id.items()}
    profiles={'unit':replace(p,board_value_by_type=unit,hand_value_by_base_type=unit),'v3':p}
    class FixedOrder:
        def __init__(self,leaf):self.leaf=leaf
        def evaluate(self,state):return self.leaf.evaluate(state)
        def capture_order_value(self,moving,captured):return unit[captured.current_type_id]*10-unit[moving.current_type_id]//10
        def type_value(self,tid):return unit[tid]
    row=dict(seed=case['seed'],board_values=p.board_value_by_type,calls=[]);result['cases'].append(row)
    for name,profile in profiles.items():
        ev=Evaluator(c,profile,config);counter=CountedEvaluator(ev)
        reference_error=None
        try: reference,action=reference_minimax(before,3,counter,c)
        except ReferenceLimit as exc: reference,action=None,None;reference_error=str(exc)
        for q in (0,2):
            player=AlphaBetaPlayer(c,evaluator_override=FixedOrder(ev),use_native_semantic_legality=False,use_disk_cache=False,tuning=SearchTuning(use_root_tactical=False))
            start=time.perf_counter();dec=player.choose_action(s,SearchLimits(max_depth=3,max_nodes=4096,max_time_seconds=10,quiescence_max_depth=q,quiescence_hard_max_depth=8 if q else 0))
            assert s.state==before;validate_pv(s,dec)
            complete=dec.completed_depth==3
            if not q and complete and reference is not None:assert dec.score==reference
            row['calls'].append(dict(model=name,q=q,complete=complete,seconds=time.perf_counter()-start,decision=record_value(dec),reference_q0=dict(score=reference,action=record_value(action),scorings=counter.calls,cap_failure=reference_error)))
            write_record(out,result);print(case['seed'],name,q,complete,dec.score,str(dec.action),flush=True)
result['complete']=True;write_record(out,result)
