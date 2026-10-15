"""Actual-rule controls for opt-in finite-threshold and terminal-first variants."""
from dataclasses import replace
import pytest
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from scripts.generic_session_win_proof import verify_session_certificate
from scripts.generic_session_win_proof_threshold import prove_session_win_threshold
from scripts.generic_session_win_proof_terminal_first import prove_session_win_terminal_first
from scripts.generic_session_win_proof_check_first import prove_session_win_check_first
from scripts.generic_proof_fixtures import krk_ruleset
from test_generic_session_win_proof import session, claim



def test_threshold_declines_artificial_depth_unknown_without_false_draw():
    s=session(claim(0,'WIN'));r=prove_session_win_threshold(s,max_depth=1,seconds=3.)
    assert r.status=='UNKNOWN' and r.reason=='requires_complete_rule_horizon' and r.nodes==0 and r.certificate is None


@pytest.mark.parametrize('solver',[prove_session_win_threshold,prove_session_win_terminal_first,prove_session_win_check_first])
@pytest.mark.parametrize('outcome',['WIN','LOSS','RESTART','NO_CONTEST'])
def test_actual_finite_claims_and_whole_record_preserved(solver,outcome):
    rs=replace(krk_ruleset(4),max_ply=4,declarations=(claim(0,outcome),))
    s=GameSession(compile_ruleset_for_execution(rs));root=s.to_record();state=s.state
    r=solver(s,max_depth=5,max_nodes=65536,seconds=3.)
    assert s.to_record()==root and s.state==state
    if r.certificate:
        assert verify_session_certificate(s,r.certificate,seconds=3.)['verified']
    if outcome=='WIN':
        assert r.status=='PROVEN_WIN' and r.eager_board_successors==0 and r.claims_assessed==1


@pytest.mark.parametrize('solver',[prove_session_win_threshold,prove_session_win_terminal_first,prove_session_win_check_first])
@pytest.mark.parametrize('cap',[0,1])
def test_exhausted_budget_is_unknown_and_exact_count(solver,cap):
    s=GameSession(compile_ruleset_for_execution(replace(krk_ruleset(4),max_ply=4)))
    r=solver(s,max_depth=5,max_nodes=cap,seconds=3.)
    assert r.status=='UNKNOWN' and r.reason=='node_budget' and r.nodes==cap and r.certificate is None


@pytest.mark.parametrize('solver',[prove_session_win_threshold,prove_session_win_terminal_first,prove_session_win_check_first])
def test_cancelled_actual_session_not_mutated(solver):
    s=GameSession(compile_ruleset_for_execution(replace(krk_ruleset(4),max_ply=4)));root=s.to_record()
    r=solver(s,max_depth=5,cancel=lambda:True,seconds=3.)
    assert r.status=='UNKNOWN' and r.reason=='cancelled' and s.to_record()==root


@pytest.mark.parametrize('name',[
    'test_actual_capture_hand_then_drop_mate_is_preserved',
    'test_real_forced_promotion_mate_retains_base_piece',
    'test_real_pass_draw_defense_cannot_be_omitted',
    'test_actual_played_perpetual_history_win_is_not_mislabeled_mate',
    'test_actual_no_progress_draw_and_depth_unknown_remain_distinct',
    'test_semantic_action_ids_survive_transport_and_forged_ids_fail_public_execution'])
@pytest.mark.parametrize('solver',[prove_session_win_terminal_first,prove_session_win_check_first])
def test_terminal_ordering_preserves_real_mechanisms(name,solver):
    import test_generic_session_proof_mechanisms as controls
    getattr(controls,name)(solver)


def test_terminal_order_preserves_losing_claim_before_later_restart_defense():
    s=session(claim(1,'LOSS','a'),claim(1,'RESTART','z'),k=0,b=2,r=10,turn=1)
    r=prove_session_win_terminal_first(s,target=0,max_depth=8,seconds=3.)
    assert r.status=='UNKNOWN' and r.certificate is None and r.claims_assessed==2 and r.eager_board_successors==0


def test_check_hint_never_drops_a_quiet_or_defender_choice():
    from scripts.generic_session_win_proof_check_first import _checking_children
    from scripts.generic_session_win_proof_batch_pn import _children, _Forward
    from scripts.generic_win_proof import _Budget
    s=session(claim(0,'LOSS'),claim(0,'RESTART','z'))
    forward=_Forward(s.compiled,s.state,s.to_record(),s.result)
    old=list(_children(forward,_Budget(65536,3.,None),[0,0]))
    new=list(_checking_children(forward,_Budget(65536,3.,None),[0,0],0))
    assert {repr(x) for x in old}=={repr(x) for x in new}
    assert new[:2]==old[:2]
    board=[child for choice,child in new if choice.kind=='ACTION']
    assert any(c.state.history[-1].gave_check for c in board)
    assert any(not c.state.history[-1].gave_check for c in board)
