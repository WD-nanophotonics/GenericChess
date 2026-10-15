"""Actual public rule outcomes and history/rollback counterexamples."""
from dataclasses import replace
import pytest
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state,apply_action
from generic_chess.core.movegen import legal_actions
from generic_chess.core.terminal import terminal_result,TerminalStatus
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import RuleNoProgressDraw
from scripts.generic_proof_fixtures import krk_ruleset,krk_state,compile_krk
from scripts.generic_public_win_proof import prove_win_public,verify_public_certificate,PublicStrategyCursor
from scripts.generic_proof_public_path import PublicProofPath
from scripts.generic_win_proof import PROVEN_WIN,UNKNOWN,ProofNode,WinCertificate,prove_win


def declared_fixture(k,b,r,threshold):
    rs=krk_ruleset(4);board=[None]*16
    for square,piece in [(k,Piece(0,"K","K")),(b,Piece(1,"K","K")),(r,Piece(0,"R","R"))]:board[square]=piece
    rs=replace(rs,initial_position=tuple(tuple(board[i:i+4]) for i in range(0,16,4)),no_progress_draw=RuleNoProgressDraw(threshold,True))
    c=compile_ruleset(rs);return c,initial_state(c)


def test_real_mate_at_no_progress_threshold_is_proved_and_executed():
    c,s=declared_fixture(1,3,8,1)
    assert prove_win(c,s).reason=="unsupported_no_progress_history"
    result=prove_win_public(c,s,max_nodes=4096,seconds=3.,max_depth=1)
    assert result.status==PROVEN_WIN and result.certificate.tree.rank==1
    assert result.pushes==result.pops and result.nodes>0
    assert verify_public_certificate(c,s,result.certificate,seconds=3.)["verified"]
    cursor=PublicStrategyCursor(c,result.certificate,seconds=3.)
    child=cursor.advance(s,cursor.choose(s))
    assert child.terminal_status.status==TerminalStatus.CHECKMATE and child.terminal_status.winner==0
    assert cursor.node.rank==0


def test_threshold_quiet_draws_cannot_be_forged_as_wins():
    c,s=declared_fixture(0,15,10,1)
    children=[apply_action(s,a,c) for a in legal_actions(s,c)]
    assert all(x.terminal_status.is_terminal and x.terminal_status.winner is None for x in children)
    assert any(x.terminal_status.status==TerminalStatus.NO_PROGRESS_DRAW for x in children)
    result=prove_win_public(c,s,max_nodes=4096,seconds=3.,max_depth=4)
    assert result.status==UNKNOWN and result.reason=="no_forced_win_in_exhausted_tree"
    child=next(x for x in children if x.terminal_status.status==TerminalStatus.NO_PROGRESS_DRAW)
    forged=WinCertificate(c.ruleset_fingerprint,child,0,ProofNode(0,terminal_kind="no_progress_draw"))
    assert not verify_public_certificate(c,child,forged)["verified"]
    actual=prove_win_public(c,child)
    assert actual.status=="ALREADY_TERMINAL" and actual.terminal_kind=="no_progress_draw" and actual.winner is None


def test_complete_declared_history_kept_and_missing_history_unknown():
    c,s=declared_fixture(0,15,10,2)
    s=apply_action(s,legal_actions(s,c)[0],c)
    assert s.ply_count==1 and len(s.history)==2
    result=prove_win_public(c,s,max_nodes=4096,seconds=3.,max_depth=3)
    assert result.reason=="no_forced_win_in_exhausted_tree"
    broken=replace(s,history=())
    result=prove_win_public(c,broken,max_nodes=4096,seconds=3.,max_depth=3)
    assert result.status==UNKNOWN and result.reason=="incomplete_adjudication_history"
    assert result.pushes==result.pops


def test_public_push_cancel_after_atomic_transition_never_commits_partial_child():
    c,s=declared_fixture(0,15,10,2);path=PublicProofPath(s,c);calls=[]
    def check():
        calls.append(1)
        if len(calls)==2:raise RuntimeError("cancel-after-transition")
    with pytest.raises(RuntimeError,match="cancel-after-transition"):
        path.push(legal_actions(s,c)[0],checkpoint=check)
    path.assert_balanced();assert path.state is s and path.pushes==0


def test_public_prover_and_verifier_cancel_at_actual_child(monkeypatch):
    c=compile_krk();s=krk_state(c,0,2,10,1);roots=[]
    original=PublicProofPath.__init__
    def record(self,*args):original(self,*args);roots.append(self)
    monkeypatch.setattr(PublicProofPath,"__init__",record)
    result=prove_win_public(c,s,target=0,max_nodes=65536,seconds=3.,cancel=lambda:bool(roots) and roots[0].depth>0)
    assert result.reason=="cancelled" and result.status==UNKNOWN
    roots[0].assert_balanced();assert roots[0].state==s
    cert=prove_win_public(c,s,target=0,max_nodes=65536,seconds=3.,max_depth=8).certificate
    assert cert is not None and len(cert.tree.edges)==2
    calls=[]
    def stop():calls.append(1);return len(calls)>5
    receipt=verify_public_certificate(c,s,cert,seconds=3.,cancel=stop)
    assert not receipt["verified"] and receipt["reason"]=="cancelled"
    for action,_ in cert.tree.edges:
        cursor=PublicStrategyCursor(c,cert,seconds=3.)
        cursor.advance(s,action)
        while cursor.node.edges:cursor.advance(cursor.state,cursor.node.edges[0][0])
        assert cursor.state.terminal_status.winner==0


def test_public_full_history_certificate_rejects_stale_and_forged_defense():
    c=compile_krk();s=krk_state(c,0,2,10,1)
    cert=prove_win_public(c,s,target=0,max_nodes=65536,seconds=3.,max_depth=8).certificate
    assert cert is not None
    assert not verify_public_certificate(c,replace(s,history=()),cert)["verified"]
    forged=replace(cert,tree=replace(cert.tree,edges=cert.tree.edges[:1]))
    assert not verify_public_certificate(c,s,forged)["verified"]


def test_zero_time_and_zero_nodes_preserve_unknown_without_win():
    c,s=declared_fixture(1,3,8,1)
    for args,reason in [(dict(seconds=0),"time_budget"),(dict(max_nodes=0),"node_budget"),(dict(cancel=lambda:True),"cancelled")]:
        result=prove_win_public(c,s,**args)
        assert result.status==UNKNOWN and result.reason==reason and result.nodes==0


@pytest.mark.parametrize("name",[
    "test_rook_drop_mate_preserves_hand_semantics",
    "test_forced_promotion_is_part_of_actual_winning_action",
    "test_pass_is_defense_not_discarded_as_nonchecking_move",
    "test_semantic_chess_mate_proof_has_lossless_semantic_actions",
    "test_actual_mate_at_ply_limit_precedes_draw_limit",
    "test_certificate_binds_aux_rights_and_lossless_action_identity",
])
def test_public_solver_keeps_existing_cross_rule_contract(name,monkeypatch):
    import test_generic_win_proof_semantics as semantics
    monkeypatch.setattr(semantics,"prove_win",prove_win_public)
    monkeypatch.setattr(semantics,"verify_certificate",verify_public_certificate)
    monkeypatch.setattr(semantics,"StrategyCursor",PublicStrategyCursor)
    getattr(semantics,name)()



def test_same_board_same_ply_different_reset_history_has_different_terminal():
    from scripts.generic_proof_rnb_bridge import uci
    c0,s0=declared_fixture(0,15,5,5)
    rs=krk_ruleset(4)
    rs=replace(rs,initial_position=tuple(tuple(s0.position.board[k:k+4]) for k in range(0,16,4)),
               repetition_limit=100,max_ply=16,no_progress_draw=RuleNoProgressDraw(5,True,("R",)))
    c=compile_ruleset(rs);root=initial_state(c)
    def play(seq):
        path=PublicProofPath(root,c)
        for move in seq:
            action=next(a for a in path.legal_actions() if uci(a)==move)
            path.push(action)
        return path
    king=play(["a1b1","d4c4","b1a1","c4d4"])
    rook=play(["b2a2","d4c4","a2b2","c4d4"])
    assert king.position==rook.position and king.state.ply_count==rook.state.ply_count==4
    assert king.state.history!=rook.state.history
    for path in (king,rook):
        action=next(a for a in path.legal_actions() if uci(a)=="a1b1")
        path.push(action)
    assert king.terminal_status.status==TerminalStatus.NO_PROGRESS_DRAW
    assert not rook.terminal_status.is_terminal
    assert prove_win_public(c,king.state).terminal_kind=="no_progress_draw"
    assert prove_win_public(c,rook.state,max_depth=0).status==UNKNOWN
    for path in (king,rook):
        while path.depth:path.pop()
        path.assert_balanced();assert path.state==root



def test_optin_hybrid_public_proof_physically_finishes_without_material_calls():
    from scripts.generic_proof_player import ProofMaterialPlayer
    c,s=declared_fixture(11,4,3,4)
    def forbidden(*args):raise AssertionError("proved win must not read material")
    player=ProofMaterialPlayer(c,forbidden,proof_search=prove_win_public,cursor_factory=PublicStrategyCursor)
    decision=player.choose(s,max_nodes=65536,seconds=2.)
    assert decision.source=="PROOF" and decision.nodes<=65536 and decision.proof_rank>1
    source=s
    while not source.terminal_status.is_terminal:
        if source.position.side_to_move==0:
            step=player.choose(source,max_nodes=64,seconds=1.)
            assert step.source=="PROOF_CONTINUATION" and step.nodes==0
            action=step.action
        else:action=player.cursor.node.edges[-1][0]
        old_rank=player.cursor.node.rank
        player.observe(source,action);source=apply_action(source,action,c)
        assert player.cursor.node.rank<old_rank
    assert source.terminal_status.winner==0 and source.terminal_status.status==TerminalStatus.CHECKMATE


def test_public_certificate_with_runtime_verifier_fails_closed_and_normal_continues():
    from scripts.generic_proof_player import ProofMaterialPlayer
    c,s=declared_fixture(1,3,8,1);called=[]
    def normal(state,nodes,seconds,cancel):
        called.append(True);return legal_actions(state,c)[0],1
    player=ProofMaterialPlayer(c,None,proof_search=prove_win_public,normal_search=normal)
    decision=player.choose(s,max_nodes=4096,seconds=1.)
    assert called and decision.source=="EXTERNAL_SEARCH" and decision.proof_nodes>0
    assert decision.proof_reason=="verification_unsupported_no_progress_history"
    assert decision.verification_nodes==0 and decision.nodes==decision.proof_nodes+1
