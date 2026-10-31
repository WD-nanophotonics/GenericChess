"""Terminal-envelope truth conditions on the actual shallow consumer."""
from scripts.aux_new_prefix_terminal import min_fold,max_fold,selected_regret

def test_one_legal_winning_defense_certifies_selected_loss():
    assert min_fold([[-1,1],[-1,-1]])==[-1,-1]

def test_one_cooperative_mate_does_not_prove_forced_win():
    assert min_fold([[1,1],[-1,1]])==[-1,1]

def test_all_terminal_draws_do_prove_draw():
    assert min_fold([[0,0],[0,0]])==[0,0]

def test_unexplored_choices_never_become_draw():
    assert min_fold([])==[-1,1]
    assert max_fold([])==[-1,1]
    assert selected_regret([[-1,1],[-1,1]],[-1,1])==[0,2]

def test_strict_loss_requires_better_root_lower_bound():
    assert selected_regret([[0,0],[-1,-1]],[-1,-1])==[1,1]
    assert selected_regret([[-1,1],[-1,-1]],[-1,-1])==[0,2]

def test_any_immediate_win_makes_root_exact_win():
    assert max_fold([[-1,1],[1,1]])==[1,1]
