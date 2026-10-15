"""Proof-number alternative must meet the original certificate contract."""
from dataclasses import replace
import pytest
from scripts.generic_proof_fixtures import compile_krk,krk_state
from scripts.generic_win_proof import verify_certificate,StrategyCursor,PROVEN_WIN,UNKNOWN
from scripts.generic_win_proof_pn import prove_win_pn

@pytest.mark.parametrize('root',[(1,3,8,0),(0,2,10,1),(0,15,10,0)])
def test_pn_wins_independently_checked_and_executed(root):
    c=compile_krk();s=krk_state(c,*root)
    r=prove_win_pn(c,s,target=0,max_nodes=65536,seconds=5.,max_depth=32)
    assert r.pushes==r.pops and r.completed_depth==0
    assert r.peak_depth>=0
    if r.status==PROVEN_WIN:
        assert verify_certificate(c,s,r.certificate,seconds=5.)['verified']
        cur=StrategyCursor(c,r.certificate,seconds=5.)
        while cur.node.edges:cur.advance(cur.state,cur.node.edges[-1][0])
        assert cur.state.terminal_status.winner==0
    else:assert r.status==UNKNOWN

@pytest.mark.parametrize('args,reason',[({'max_nodes':0},'node_budget'),({'seconds':0},'time_budget'),({'max_depth':0},'depth_budget'),({'cancel':lambda:True},'cancelled')])
def test_pn_cutoff_never_win(args,reason):
    c=compile_krk();s=krk_state(c,0,15,10,0)
    r=prove_win_pn(c,s,**args)
    assert r.status==UNKNOWN and r.reason==reason and r.pushes==r.pops


def test_pn_draw_not_empty_all_win():
    c=compile_krk();s=krk_state(c,1,3,4,1)
    r=prove_win_pn(c,s,target=0)
    assert r.status=='ALREADY_TERMINAL' and r.winner is None


@pytest.mark.parametrize('name',[
    'test_rook_drop_mate_preserves_hand_semantics',
    'test_forced_promotion_is_part_of_actual_winning_action',
    'test_pass_is_defense_not_discarded_as_nonchecking_move',
    'test_semantic_chess_mate_proof_has_lossless_semantic_actions',
    'test_no_progress_and_declarations_fail_closed',
    'test_incomplete_adjudication_history_unknown_and_not_silently_reset',
])
def test_pn_meets_same_cross_mechanism_contract(name,monkeypatch):
    import test_generic_win_proof_semantics as semantics
    monkeypatch.setattr(semantics,'prove_win',prove_win_pn)
    getattr(semantics,name)()
