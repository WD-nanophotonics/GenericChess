from fractions import Fraction as F
from scripts.leaper_h6_occupation import occupation_solver


def test_no_root_fork_does_not_mean_no_later_fork_or_same_mu_rate():
    # All root actions have DRAW minimax value, but the next defender can
    # choose DRAW or a loss. Uniform path occupation differs from root mu.
    visit,cost=occupation_solver([(1,2),(3,4),(),(),()],{2:None,3:0,4:None},[0,1,1,0,0],lambda n:None)
    probs,decisions,forks,losses,firstfork,firstloss=visit(0,6,())
    assert probs==(F(0),F(3,4),F(1,4))
    assert decisions==F(3,2)and forks==F(1,2)and forks/decisions==F(1,3)
    assert sum(firstfork)==F(1,2)and firstfork[0]==0 and firstfork[1]==F(1,2)
    assert losses==F(1,4)and sum(firstloss)==F(1,4)and firstloss[1]==F(1,4)


def test_repeat_draw_and_terminal_priority_keep_probability_mass():
    visit,cost=occupation_solver([(1,),(0,)],{},[0,1],lambda n:None)
    p,d,f,l,ff,fl=visit(0,6,())
    assert p==(F(0),F(1),F(0)) and d==2 and f==l==sum(ff)==sum(fl)==0


def test_ever_event_is_not_expected_number_of_event_visits():
    # Root fork WIN/DRAW, then a second fork on the winning continuation.
    visit,_=occupation_solver([(1,2),(3,4),(),(),()],{2:None,3:0,4:None},[0,0,1,1,1],lambda n:None)
    p,d,f,l,ff,fl=visit(0,6,())
    assert f==F(3,2)and sum(ff)==1
