"""Typed full-stock interface fixtures, not new legal-use observations."""
from collections import Counter
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace as NS
import pytest
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.terminal import TerminalResult,TerminalStatus as T
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.shogi_contact_interval_choice import shogi_contact_intervals,shogi_contact_choice

C=compile_ruleset_for_execution(build_standard_shogi_ruleset())
GAME=NS(compiled=C,terminal=lambda child:child.result)
STOCK=dict(P=18,L=4,N=4,S=4,G=4,B=2,R=2)


def state(tokens=(),*,rest_owner=0,side=0,result=None):
    board=[None]*81;board[0]=Piece(0,'K','K');board[80]=Piece(1,'K','K');remaining=Counter(STOCK)
    for sq,p in tokens:board[sq]=p;remaining[p.base_type_id]-=1
    assert min(remaining.values())>=0
    hands=[Hands.empty(),Hands.empty()];hands[rest_owner]=Hands(tuple(sorted((t,n) for t,n in remaining.items() if n)))
    position=replace(initial_state(C).position,board=tuple(board),hands=tuple(hands),side_to_move=side)
    return NS(position=position,result=result or TerminalResult(T.ONGOING))


@pytest.mark.parametrize('law',['geometric_half','linear_mixture'])
def test_all20_modes_share_exact_maximum_and_gold_mode_aliases(law):
    x=shogi_contact_intervals(law);assert len(x)==20
    assert x['board','TR']==(F(1),F(1))
    assert all(0<lo<=hi<=1 for lo,hi in x.values())
    for promoted in ('TP','TL','TN','TS'):assert x['board',promoted]==x['board','G']
    assert set(k for k in x if k[0]=='hand')=={('hand',t) for t in STOCK}


@pytest.mark.parametrize('owner',[0,1])
@pytest.mark.parametrize('law',['geometric_half','linear_mixture','both'])
def test_signed_hand_transfer_and_terminal_priority(owner,law):
    rich=state(rest_owner=owner);poor=state(rest_owner=1-owner)
    win=state(rest_owner=1-owner,result=TerminalResult(T.CHECKMATE,owner))
    loss=state(rest_owner=owner,result=TerminalResult(T.CHECKMATE,1-owner))
    draw=state(rest_owner=1-owner,result=TerminalResult(T.MAX_PLY))
    call=lambda children:shogi_contact_choice(children,GAME,owner=owner,duration=law,complete=True)
    assert call({'rich':rich,'poor':poor})['selected']=='rich'
    assert call({'rich':rich,'win':win})['selected']=='win'
    assert call({'poor':poor,'loss':loss})['selected']=='poor'
    assert call({'poor':poor,'draw':draw})['selected']=='draw'
    assert call({'rich':rich,'draw':draw})['selected']=='rich'


def test_real_coefficient_uncertainty_is_not_replaced_by_midpoint():
    a=state(((31,Piece(0,'S','S')),(33,Piece(1,'G','G'))))
    b=state(((31,Piece(1,'S','S')),(33,Piece(0,'G','G'))))
    for law in ('geometric_half','linear_mixture'):
        result=shogi_contact_choice({'a':a,'b':b},GAME,owner=0,duration=law,complete=True)
        assert result['complete'] and result['selected'] is None
        x=shogi_contact_intervals(law);signs={s>g for s,g in product(x['board','S'],x['board','G'])}
        assert signs=={True,False}
    assert shogi_contact_choice({'a':a,'b':b},GAME,owner=0,duration='both',complete=True)['selected'] is None


def test_board_current_hand_base_and_original_promotion_identity_preserved():
    p=state(((31,Piece(0,'P','TP',True)),))
    result=shogi_contact_choice({'a':p,'z':p},GAME,owner=0,duration='geometric_half',complete=True)
    assert result['selected']=='a'
    assert result['features']['a']['board','TP']==1
    assert result['features']['a']['hand','P']==17
    assert p.position.board[31].base_type_id=='P' and p.position.board[31].promoted
    dropped=state(((31,Piece(0,'P','P')),))
    features=shogi_contact_choice({'a':dropped},GAME,owner=0,duration='geometric_half',complete=True)['features']['a']
    assert features['board','P']==1 and features['hand','P']==17


@pytest.mark.parametrize('change',['stock','promoted_hand','origin','aux','shape','rules','checked','anchor'])
def test_one_unsupported_child_rejects_the_whole_table(change):
    good=state();bad=state();p=bad.position
    if change=='stock':p=replace(p,hands=(p.hands[0].remove('P'),p.hands[1]))
    elif change=='promoted_hand':p=replace(p,hands=(p.hands[0].add('TP'),p.hands[1]))
    elif change=='origin':
        bad=state(((31,Piece(0,'P','G',True)),));p=bad.position
    elif change=='aux':p=replace(p,aux_state=(((0,-1),1),))
    elif change=='shape':p=replace(p,board_width=3,board_height=27)
    elif change=='rules':p=replace(p,ruleset_fingerprint='different')
    elif change=='checked':bad=state(((36,Piece(1,'R','R')),));p=bad.position
    else:
        board=list(p.board);board[80]=None;p=replace(p,board=tuple(board))
    bad.position=p
    r=shogi_contact_choice({'good':good,'bad':bad},GAME,owner=0,duration='geometric_half',complete=True)
    assert not r['complete'] and r['selected'] is None and r['unsupported_choice']=='bad'


@pytest.mark.parametrize('terminal',[TerminalResult(T.STALEMATE),TerminalResult(T.NO_CONTEST),
 TerminalResult(T.REPETITION),TerminalResult(T.PERPETUAL_CHECK,0),TerminalResult(T.RULE_LOSS,0),TerminalResult(T.CHECKMATE,True)])
def test_unqualified_adjudication_never_becomes_a_material_leaf(terminal):
    r=shogi_contact_choice({'bad':state(result=terminal)},GAME,owner=0,duration='both',complete=True)
    assert not r['complete'] and r['selected'] is None


def test_incomplete_table_never_selects_and_each_law_remains_separate():
    children={'a':state(),'b':state()}
    assert not shogi_contact_choice(children,GAME,owner=0,duration='both',complete=False)['complete']
    r=shogi_contact_choice(children,GAME,owner=0,duration='both',complete=True)
    assert r['selected']=='a' and set(r['by_law'])=={'geometric_half','linear_mixture'}
