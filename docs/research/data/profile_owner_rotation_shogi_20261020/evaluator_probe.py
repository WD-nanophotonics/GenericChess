from dataclasses import replace
import json
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.learning.shogi_rules import sfen_to_gc_state
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Position
from generic_chess.core.coordinates import Square
c=compile_ruleset_for_execution(build_standard_shogi_ruleset()); n=c.board_size
config=EvaluationConfig(); profile=build_ruleset_profile(c,config); ev=Evaluator(c,profile,config)
def mirror(state, flip_turn=False):
    board=[None]*(n*n)
    for idx,p in enumerate(state.position.board):
        if p is None: continue
        rank,file=divmod(idx,n); dst=(n-1-rank)*n+(n-1-file)
        board[dst]=Piece(1-p.owner,p.base_type_id,p.current_type_id,p.promoted)
    pos=replace(state.position,board=tuple(board),hands=(state.position.hands[1],state.position.hands[0]),side_to_move=(1-state.position.side_to_move if flip_turn else state.position.side_to_move))
    return replace(state,position=pos)
fixtures={
 'promoted_and_asymmetric_hands':'8k/9/4+p4/4P4/9/9/9/9/K8 b 2P1g 1',
 'mixed_promoted_hand_side1':'8k/9/3+P5/9/5B3/9/9/9/K8 w 2rP 7',
}
out={}
for name,sfen in fixtures.items():
    s=sfen_to_gc_state(c,sfen)
    m=mirror(s)
    mf=mirror(s,True)
    out[name]={'sfen':sfen,'score':ev.evaluate(s),'owner_swap_same_turn_score':ev.evaluate(m),'owner_swap_and_turn_score':ev.evaluate(mf),'expected_antisymmetry_same_turn':ev.evaluate(m)==-ev.evaluate(s),'expected_same_actor_advantage_after_turn_swap':ev.evaluate(mf)==ev.evaluate(s),'material':{'board':len([p for p in s.position.board if p]),'hands':[h.count('P')+h.count('G')+h.count('R')+h.count('B') for h in s.position.hands]}}
print(json.dumps(out,sort_keys=True))
