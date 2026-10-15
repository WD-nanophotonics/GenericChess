"""Paid subtree candidates remain bound to full history and need verification."""
from dataclasses import replace
import pytest
from scripts.generic_proof_fixtures import compile_krk,krk_state
from scripts.generic_win_proof import verify_certificate,StrategyCursor
from scripts.generic_win_proof_retained import PartialProofStore,prove_win_retained


def test_collected_subtree_is_independently_verified_and_physically_executable():
    c=compile_krk();s=krk_state(c,0,15,10,0);store=PartialProofStore(16)
    r=prove_win_retained(c,s,store=store,max_nodes=4096,seconds=3.)
    assert r.nodes<=4096 and r.pushes==r.pops and store.certificates
    for cert in list(store.certificates):
        assert cert.root.ply_count==s.ply_count+2 and len(cert.root.history)==len(s.history)+2
        receipt=verify_certificate(c,cert.root,cert,seconds=3.)
        assert receipt['verified']
        cur=StrategyCursor(c,cert,seconds=3.)
        while cur.node.edges:cur.advance(cur.state,cur.node.edges[-1][0])
        assert cur.state.terminal_status.winner==cert.target


def test_same_board_other_clock_or_history_never_hits():
    c=compile_krk();s=krk_state(c,0,15,10,0);store=PartialProofStore()
    prove_win_retained(c,s,store=store,max_nodes=4096,seconds=3.)
    cert=store.certificates[0]
    assert store.take(c,replace(cert.root,ply_count=0),cert.target) is None
    assert store.take(c,replace(cert.root,history=cert.root.history[:-1]),cert.target) is None
    assert store.take(c,cert.root,1-cert.target) is None
    assert store.take(compile_krk(8),cert.root,cert.target) is None
    assert store.take(c,cert.root,cert.target)==cert
    assert store.take(c,cert.root,cert.target) is None


def test_zero_storage_and_budget_cancellation_are_bounded():
    c=compile_krk();s=krk_state(c,0,15,10,0)
    for count in (0,1,2):
        store=PartialProofStore(count)
        r=prove_win_retained(c,s,store=store,max_nodes=512,seconds=2.)
        assert len(store.certificates)<=count and r.nodes<=512 and r.pushes==r.pops
    store=PartialProofStore()
    r=prove_win_retained(c,s,store=store,max_nodes=4096,seconds=0)
    assert not store.certificates and r.status=='UNKNOWN' and r.nodes==0
    r=prove_win_retained(c,s,store=store,cancel=lambda:True)
    assert not store.certificates and r.status=='UNKNOWN' and r.pushes==r.pops
    with pytest.raises(ValueError):PartialProofStore(65)


@pytest.mark.parametrize('name',[
    'test_rook_drop_mate_preserves_hand_semantics',
    'test_forced_promotion_is_part_of_actual_winning_action',
    'test_pass_is_defense_not_discarded_as_nonchecking_move',
    'test_semantic_chess_mate_proof_has_lossless_semantic_actions',
    'test_no_progress_and_declarations_fail_closed',
    'test_incomplete_adjudication_history_unknown_and_not_silently_reset',
])
def test_retention_meets_existing_cross_mechanism_contract(name,monkeypatch):
    import test_generic_win_proof_semantics as semantics
    def wrapped(*args,**kwargs):
        return prove_win_retained(*args,store=PartialProofStore(8),**kwargs)
    monkeypatch.setattr(semantics,'prove_win',wrapped)
    getattr(semantics,name)()
