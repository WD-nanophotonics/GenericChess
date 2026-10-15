"""Real certificate horizon admission and physical execution regressions."""
import pytest
from dataclasses import replace
from generic_chess.core.transition import apply_action
from scripts.generic_proof_fixtures import compile_krk,krk_state
from scripts.generic_proof_player import ProofMaterialPlayer
from scripts.generic_proof_tail import CertifiedTail
from scripts.generic_win_proof import prove_win,StrategyCursor


def setup():
    c=compile_krk();s=krk_state(c,0,2,10,1)
    cert=prove_win(c,s,target=0,max_nodes=65536,seconds=3.,max_depth=8).certificate
    assert cert is not None
    p=ProofMaterialPlayer(c,None)
    p.cursor=StrategyCursor(c,cert,seconds=3.)
    return c,s,p


def test_defender_turn_admission_covers_every_actual_defense():
    c,start,p=setup()
    for first,_ in p.cursor.node.edges:
        c,s,p=setup();tail=CertifiedTail.admit(s,{0:p})
        assert tail.owner==0 and tail.initial_rank>1
        n=0
        while not s.terminal_status.is_terminal:
            a=tail.choose(s) if s.position.side_to_move==0 else (first if n==0 else tail.cursor.node.edges[-1][0])
            assert a is not None
            p.observe(s,a);s=apply_action(s,a,c);tail.observed(s);n+=1
        assert s.terminal_status.winner==0 and n<=tail.initial_rank
        assert tail.remaining_rank==0


def test_no_proof_stale_history_and_rank_cap_do_not_extend_horizon():
    c,s,p=setup()
    assert CertifiedTail.admit(s,{0:ProofMaterialPlayer(c,None)}) is None
    assert CertifiedTail.admit(s,{0:p},max_rank=0) is None
    assert CertifiedTail.admit(replace(s,ply_count=s.ply_count+1),{0:p}) is None
    p.proof_enabled=False
    assert CertifiedTail.admit(s,{0:p}) is None


def test_unobserved_action_cannot_claim_tail_progress():
    c,s,p=setup();tail=CertifiedTail.admit(s,{0:p})
    a=p.cursor.node.edges[0][0]
    child=apply_action(s,a,c)
    with pytest.raises(ValueError,match='binding'):tail.observed(child)
    with pytest.raises(ValueError,match='decrease'):tail.observed(s)


def test_actual_terminal_is_not_admitted_for_extra_play():
    c=compile_krk();s=krk_state(c,1,3,8,0);p=ProofMaterialPlayer(c,None)
    z=p.choose(s,max_nodes=4096,seconds=1.)
    assert z.source=='PROOF'
    p.observe(s,z.action);s=apply_action(s,z.action,c)
    assert s.terminal_status.is_terminal
    assert CertifiedTail.admit(s,{0:p}) is None
