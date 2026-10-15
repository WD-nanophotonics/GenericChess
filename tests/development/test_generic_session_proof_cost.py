"""A generated-but-unvisited batch must remain visible through the chooser."""
from test_generic_session_win_proof import session
from test_generic_session_proof_player import player
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn

def test_actual_eager_work_survives_unknown_proof_and_legal_fallback():
    s=session();p=player(s,proof_search=prove_session_win_batch_pn)
    d=p.choose(s,max_nodes=4,seconds=3.)
    assert d.choice.action in s.legal_actions() and d.proof_nodes==1
    stats=dict(d.proof_stats)
    assert stats['eager_board_successors']==len(s.legal_actions())>d.proof_nodes
    assert stats['frontiers']==1 and stats['transitions']==1


def test_real_claim_stats_survive_successful_verification():
    from test_generic_session_win_proof import claim
    s=session(claim(0,'WIN'));p=player(s,proof_search=prove_session_win_batch_pn)
    d=p.choose(s,max_nodes=64,seconds=3.)
    assert d.source=='PROOF' and d.verification_nodes>0
    stats=dict(d.proof_stats)
    assert stats['claims_assessed']==1 and stats['eager_board_successors']==0 and stats['transitions']==1
