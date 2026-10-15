"""Real path-rule successor divergence despite equal board/ply/counts."""
from dataclasses import replace
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.core.actions import PassAction
from generic_chess.core.transition import apply_action,initial_state
from generic_chess.core.movegen import legal_actions
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.rules.schema import RuleSet,RuleConsecutiveActionAdjudication
from generic_chess.rules.compiler import compile_ruleset
from scripts.exact_generic_preference_solver_v3 import _runtime_key


def histories():
    king=PieceType('K','Anchor',tuple(LeapAtom((x,y)) for x in (-1,0,1) for y in (-1,0,1) if x or y),is_anchor=True)
    rook=PieceType('R','Ray',tuple(RayAtom(d) for d in ((1,0),(-1,0),(0,1),(0,-1))))
    board=[None]*16;board[0]=Piece(0,'K','K');board[5]=Piece(0,'R','R');board[15]=Piece(1,'K','K')
    rs=RuleSet(board_size=4,piece_types=(king,rook),initial_position=tuple(tuple(board[i:i+4]) for i in range(0,16,4)),drop_allowed={'R':((False,)*16,)*2},capture_disposition='remove_from_game',max_ply=64,repetition_limit=100,pass_enabled=True,consecutive_action_adjudications=(RuleConsecutiveActionAdjudication('pass',3,'DRAW'),))
    c=compile_ruleset(rs)
    def play(seq):
        s=initial_state(c)
        for step in seq:
            if step=='pass':a=PassAction()
            else:
                f,t=step;a=next(a for a in legal_actions(s,c) if not isinstance(a,PassAction) and a.from_square.rank*4+a.from_square.file==f and a.to_square.rank*4+a.to_square.file==t)
            s=apply_action(s,a,c)
        return s
    loop=[(0,1),(15,14),(1,0),(14,15)]
    return c,play(['pass','pass']+loop),play(loop+['pass','pass'])


def test_history_sensitive_reference_key_separates_real_successor_values():
    c,a,b=histories()
    assert a.position==b.position and a.ply_count==b.ply_count
    assert dict(a.repetition_counts)==dict(b.repetition_counts) and a.history!=b.history
    ra,rb=(SearchPathRuntime.from_state(s,c) for s in (a,b))
    assert ra.search_key()!=rb.search_key()  # Core already preserves this distinction.
    assert _runtime_key(ra,policy='draw')!=_runtime_key(rb,policy='draw')
    assert apply_action(a,PassAction(),c).terminal_status.status.value=='ongoing'
    assert apply_action(b,PassAction(),c).terminal_status.status.value=='action_class_draw'


def test_full_history_reference_key_is_stable_after_actual_runtime_unwind():
    c,a,_=histories();rt=SearchPathRuntime.from_state(a,c);before=_runtime_key(rt,policy='draw')
    action=next(x for x in rt.legal_actions() if isinstance(x,PassAction))
    rt.push(action);assert _runtime_key(rt,policy='draw')!=before;rt.pop()
    assert _runtime_key(rt,policy='draw')==before;rt.assert_balanced()
