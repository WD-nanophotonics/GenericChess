"""Scoped family selection matches concrete scores; no source labels."""
from fractions import Fraction as F
from types import SimpleNamespace as NS
import pytest
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.terminal import TerminalStatus as TS,TerminalResult
from scripts.contact_rb_choice import rb_contact_choice


class Game:
    def terminal(self,child):
        return child.terminal


def child(r,b,owner=0,terminal=None):
    board=[Piece(0,'K','K'),Piece(1,'K','K')]
    board += [Piece(1-owner,'R','R')]*r+[Piece(1-owner,'B','B')]*b
    return NS(position=NS(board=board,hands=(Hands(),Hands())),
              terminal=terminal or TerminalResult(TS.ONGOING))


def test_every_positive_contact_completion_agrees_for_both_owners():
    for owner in (0,1):
        rows={'quiet':child(1,1,owner),'take-B':child(1,0,owner),'take-R':child(0,1,owner)}
        assert rb_contact_choice(rows,Game(),owner=owner,complete=True)['selected']=='take-R'
        for i in range(1,30):
            g=F(i,30);r=(53760*g+194432*g*g+1792*g**3)/249984
            lo=F(33936,249984)*g;hi=(33936*g+88832*g*g)/249984
            for b in (lo,(lo+hi)/2,hi):
                scores={'quiet':-r-b,'take-B':-r,'take-R':-b}
                assert max(scores,key=scores.get)=='take-R'


def test_terminal_first_and_canonical_ties():
    rows={'z':child(0,1),'a':child(0,1),'quiet':child(1,1)}
    assert rb_contact_choice(rows,Game(),owner=0,complete=True)['selected']=='a'
    rows['draw']=child(0,0,terminal=TerminalResult(TS.STALEMATE))
    assert rb_contact_choice(rows,Game(),owner=0,complete=True)['selected']=='draw'
    rows['win']=child(0,0,terminal=TerminalResult(TS.CHECKMATE,0))
    rows['loss']=child(0,0,terminal=TerminalResult(TS.CHECKMATE,1))
    assert rb_contact_choice(rows,Game(),owner=0,complete=True)['selected']=='win'


def test_incomplete_and_unqualified_shapes_fail_closed():
    assert rb_contact_choice({'a':child(0,1)},Game(),owner=0)['selected'] is None
    assert rb_contact_choice({'a':child(0,0,terminal=TerminalResult(TS.NO_CONTEST))},
                             Game(),owner=0,complete=True)['selected'] is None
    for r,b in ((2,0),(0,0)):
        with pytest.raises(ValueError):
            rb_contact_choice({'a':child(r,b)},Game(),owner=0,complete=True)
    wrong=child(0,1);wrong.position.board[-1]=Piece(1,'P','B',True)
    with pytest.raises(ValueError,match='unqualified ordinary'):
        rb_contact_choice({'a':wrong},Game(),owner=0,complete=True)
    held=child(0,1);held.position.hands=(Hands((('R',1),)),Hands())
    with pytest.raises(ValueError,match='held modes'):
        rb_contact_choice({'a':held},Game(),owner=0,complete=True)
