"""Conservative hand-scope diagnostic, not another production classifier.
One real four-ply sequence captures P and Q into owner0stock. Both rules agree
on this prefix, but only Q can drop in the mixed rule. Compare a counterfactual
P-stock removal at the reached mixed-rule root, preserving Q stock. Report
one-ply actions/boards only: identity/repetition/history are not quotiented.
Question: does the current all-or-nothing safe subset leave an observable
per-type scope limitation worth a later narrow study? Do not zero P globally.
"""
from pathlib import Path
from dataclasses import replace
import sys,hashlib
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from conftest import make_ruleset,king_type,T
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.core.pieces import Piece
from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square
from generic_chess.core.position import Hands
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.movegen import legal_actions_from_position, _apply_action_unchecked
from generic_chess.session.session import GameSession
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from scripts.research_record import record_value,write_record
folder=Path(__file__).parent;out=folder/'mixed-hand-callers.json';assert not out.exists()
types=[king_type(),T('R',*[RayAtom(v) for v in ((1,0),(-1,0),(0,1),(0,-1))]),T('P',LeapAtom((0,1))),T('Q',LeapAtom((1,1)))]
zero=(False,)*64;mask=tuple(i==9 for i in range(64))
base=make_ruleset(8,types,drop_all={t.type_id:zero for t in types if not t.is_anchor})
rows=[[None]*8 for _ in range(8)];rows[0][0]=Piece(0,'K','K');rows[7][7]=Piece(1,'K','K');rows[3][3]=Piece(0,'R','R');rows[4][3]=Piece(1,'P','P');rows[4][5]=Piece(1,'Q','Q')
base=replace(base,initial_position=tuple(map(tuple,rows)))
result={'scope':__doc__,'producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':[]}
for mixed in (False,True):
    drops=dict(base.drop_allowed)
    if mixed:drops['Q']=(mask,mask)
    c=compile_ruleset_for_execution(replace(base,drop_allowed=drops));s=GameSession(c)
    for start,end in [((3,3),(3,4)),((7,7),(6,7)),((3,4),(5,4)),((6,7),(7,7))]:s.submit(BoardMove(Square(*start),Square(*end)))
    position=s.state.position
    assert position.hands[0].count('P')==position.hands[0].count('Q')==1
    profile,scope=build_semantic_opportunity_profile(c,EvaluationConfig())
    row=dict(mixed=mixed,policy=scope['hand_policy'],hands=record_value(position.hands),hand_values=profile.hand_value_by_base_type,ply=s.state.ply_count)
    if mixed:
        changed=replace(position,hands=(position.hands[0].remove('P'),position.hands[1]))
        original=legal_actions_from_position(position,c);alternative=legal_actions_from_position(changed,c)
        assert original==alternative
        for action in original:
            a=_apply_action_unchecked(position,action,c);b=_apply_action_unchecked(changed,action,c)
            assert a.board==b.board and a.hands[0].count('Q')==b.hands[0].count('Q')
        assert repetition_identity_key(position,c)!=repetition_identity_key(changed,c)
        row.update(counterfactual_one_ply_action_checks=len(original),same_boards=True,identity_distinct=True)

        from generic_chess.ai.evaluation.evaluator import Evaluator
        from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
        from generic_chess.ai.alphabeta.search import reference_minimax
        from generic_chess.ai.alphabeta.tuning import SearchTuning
        from generic_chess.ai.limits import SearchLimits
        from scripts.unfamiliar_search import CountedEvaluator,validate_pv
        config=EvaluationConfig(dynamic_mobility_weight=0,anchor_escape_weight=0,promotion_potential_weight=0)
        hands=dict(profile.hand_value_by_base_type);hands['P']=0
        models={'old_scale':profile,'only_P_zero':replace(profile,hand_value_by_base_type=hands)}
        unit={t:0 if pt.is_anchor else 1000 for t,pt in c.types_by_id.items()}
        class FixedOrder:
            def __init__(self,leaf):self.leaf=leaf
            def evaluate(self,state):return self.leaf.evaluate(state)
            def capture_order_value(self,moving,captured):return unit[captured.current_type_id]*10-unit[moving.current_type_id]//10
            def type_value(self,tid):return unit[tid]
        row['calls']=[]
        for name,profile in models.items():
            ev=Evaluator(c,profile,config)
            for depth in (1,2):
                counted=CountedEvaluator(ev);reference,action=reference_minimax(s.state,depth,counted,c)
                before=s.state;player=AlphaBetaPlayer(c,evaluator_override=FixedOrder(ev),use_native_semantic_legality=False,use_disk_cache=False,tuning=SearchTuning(use_root_tactical=False))
                dec=player.choose_action(s,SearchLimits(max_depth=depth,max_nodes=4096,max_time_seconds=5,quiescence_max_depth=0,quiescence_hard_max_depth=0))
                assert dec.completed_depth==depth and dec.score==reference and s.state==before;validate_pv(s,dec)
                row['calls'].append(dict(model=name,depth=depth,reference_score=reference,reference_scorings=counted.calls,decision=record_value(dec)))
        row['scope_note']='Only supplied P-zero control; no product classifier extension, identity/repetition merging or validation qualification. Pstock is constant on these nonterminal shallow frontiers, so a score offset need not change decisions.'

    result['cases'].append(row)
result['complete']=True;write_record(out,result)
print(result['cases'])
