"""Research interface controls, not legal-root observations or game labels."""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace as NS
import pytest

from generic_chess.core.pieces import Piece
from generic_chess.core.position import Position,Hands
from generic_chess.core.terminal import TerminalResult,TerminalStatus as T
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.native_chess_contact_intervals import (
    native_contact_intervals,contact_interval_choice,FINGERPRINT,EMPTY_AUX,
)

GAME=NS(terminal=lambda child:child.result)


def state(tokens=(),result=None):
    # Deliberately only typed interface fixtures; no claim these are legal roots.
    board=[None]*64;board[0]=Piece(0,'K','K');board[63]=Piece(1,'K','K')
    for i,token in enumerate(tokens,1):
        board[i]=token
    return NS(position=Position(tuple(board),ruleset_fingerprint=FINGERPRINT,aux_state=EMPTY_AUX),
              result=result or TerminalResult(T.ONGOING))


@pytest.mark.parametrize('duration',['geometric_half','linear_mixture','both'])
@pytest.mark.parametrize('owner',[0,1])
def test_complete_capture_tradeoff_and_all_mode_cancellation(duration,owner):
    fixed=[Piece(0,t,t) for t in ('P','N','R','Q')]
    fixed+=[Piece(1,t,t) for t in ('P','N','R','Q')]
    children={'z_capture_N':state(fixed+[Piece(1-owner,'B','B')]),
              'a_capture_B':state(fixed+[Piece(1-owner,'N','N')]),
              'quiet':state(fixed+[Piece(1-owner,'B','B'),Piece(1-owner,'N','N')])}
    result=contact_interval_choice(children,GAME,owner=owner,duration=duration,complete=True)
    assert result['complete'] and result['selected']=='z_capture_N'
    assert ('board','Q') in result['features']['quiet']
    assert result['features']['quiet'][('board','Q')]==0


def test_uncertain_multi_token_exchange_has_no_midpoint_fallback():
    children={'two_N':state([Piece(0,'N','N')]*2),
              'R_and_P':state([Piece(0,'R','R'),Piece(0,'P','P')])}
    for duration in ('geometric_half','linear_mixture','both'):
        result=contact_interval_choice(children,GAME,owner=0,duration=duration,complete=True)
        assert result['complete'] and result['selected'] is None
        intervals=native_contact_intervals(duration)
        winners=set()
        for n,r,p in product(intervals['board','N'],intervals['board','R'],intervals['board','P']):
            scores={'two_N':2*n,'R_and_P':r+p}
            best=max(scores.values());winners.add(min(k for k,v in scores.items() if v==best))
        assert len(winners)==2  # Independent vertices really disagree.


@pytest.mark.parametrize('owner',[0,1])
def test_terminal_priority_over_extreme_positive_negative_material(owner):
    rich=state([Piece(owner,'Q','Q')]*30)
    poor=state([Piece(1-owner,'Q','Q')]*30)
    win=state(result=TerminalResult(T.CHECKMATE,owner))
    loss=state(result=TerminalResult(T.CHECKMATE,1-owner))
    assert contact_interval_choice({'rich':rich,'win':win},GAME,owner=owner,duration='both',complete=True)['selected']=='win'
    assert contact_interval_choice({'poor':poor,'loss':loss},GAME,owner=owner,duration='both',complete=True)['selected']=='poor'
    draw=state(result=TerminalResult(T.MAX_PLY))
    assert contact_interval_choice({'poor':poor,'draw':draw},GAME,owner=owner,duration='both',complete=True)['selected']=='draw'
    assert contact_interval_choice({'rich':rich,'draw':draw},GAME,owner=owner,duration='both',complete=True)['selected']=='rich'
    assert contact_interval_choice({'a_draw':draw,'z_ongoing':state()},GAME,owner=owner,duration='both',complete=True)['selected']=='a_draw'


@pytest.mark.parametrize('tid',['N','B','R','Q'])
def test_qualified_pawn_origin_ties_native_without_erasing_identity(tid):
    native=state([Piece(0,tid,tid)])
    promoted=state([Piece(0,'P',tid,True)])
    result=contact_interval_choice({'a':native,'z':promoted},GAME,owner=0,duration='both',complete=True)
    assert result['selected']=='a' and result['features']['a']==result['features']['z']
    assert native.position!=promoted.position
    assert promoted.position.board[1].base_type_id=='P'


@pytest.mark.parametrize('change',['right','ep','implicit_aux','hand','origin','shape','rules','too_many','anchor','unknown_cancelled'])
def test_one_unsupported_child_makes_whole_table_incomplete(change):
    good=state([Piece(0,'N','N')]);bad=state([Piece(0,'N','N')]);p=bad.position
    if change=='right':
        p=replace(p,aux_state=(((0,-1),1),)+EMPTY_AUX[1:])
    elif change=='ep':
        p=replace(p,aux_state=EMPTY_AUX[:2]+(((2,-1),(3,2)),)+EMPTY_AUX[3:])
    elif change=='implicit_aux':
        p=replace(p,aux_state=())
    elif change=='hand':
        p=replace(p,hands=(Hands((('P',1),)),Hands.empty()))
    elif change=='origin':
        board=list(p.board);board[1]=Piece(0,'N','Q',True);p=replace(p,board=tuple(board))
    elif change=='shape':
        p=replace(p,board_width=4,board_height=16)
    elif change=='rules':
        p=replace(p,ruleset_fingerprint='not-Western')
    elif change=='too_many':
        p=state([Piece(0,'P','P')]*31).position
    elif change=='anchor':
        board=list(p.board);board[63]=None;p=replace(p,board=tuple(board))
    else:
        p=state([Piece(0,'X','X'),Piece(1,'X','X')]).position
    bad.position=p
    result=contact_interval_choice({'a_good':good,'bad':bad},GAME,owner=0,duration='both',complete=True)
    assert result['selected'] is None and not result['complete'] and result['unsupported_choice']=='bad'


@pytest.mark.parametrize('terminal',[TerminalResult(T.NO_CONTEST),TerminalResult(T.RULE_LOSS,0),
                                     TerminalResult(T.STALEMATE,0),TerminalResult(T.CHECKMATE)])
def test_unqualified_terminal_does_not_become_draw_or_disappear(terminal):
    result=contact_interval_choice({'good':state(),'unqualified':state(result=terminal)},GAME,owner=0,duration='both',complete=True)
    assert not result['complete'] and result['selected'] is None


def test_constructor_fingerprint_normalization_and_full_table_contract():
    compiled=compile_ruleset_for_execution(build_western_chess_ruleset())
    assert initial_state(compiled).position.ruleset_fingerprint==FINGERPRINT
    for duration in ('geometric_half','linear_mixture','both'):
        intervals=native_contact_intervals(duration)
        assert intervals['board','Q']==(F(1),F(1))
        assert all(0<lo<=hi<=1 and isinstance(lo,F) and isinstance(hi,F) for lo,hi in intervals.values())
    assert not contact_interval_choice({'a':state()},GAME,owner=0,duration='both')['complete']
    with pytest.raises(ValueError):
        native_contact_intervals('observed_best')
    with pytest.raises(ValueError):
        contact_interval_choice({'a':state()},GAME,owner=True,duration='both',complete=True)
