"""Shared-resource fallback and actual proof continuation, not mocked wins."""
from dataclasses import replace
import pytest
from scripts.generic_proof_fixtures import compile_krk,krk_state
from scripts.generic_proof_player import ProofMaterialPlayer
from generic_chess.core.transition import apply_action
from generic_chess.core.movegen import legal_actions


def material(position,target):
    return sum((1 if p.owner==target else -1)*720 for p in position.board
               if p is not None and p.current_type_id=='R')


def test_same_total_visit_budget_proof_and_plain_arms():
    c=compile_krk();s=krk_state(c,0,15,10,0)
    for cap in (0,1,4,16,64,256):
        for enabled in (False,True):
            p=ProofMaterialPlayer(c,material,proof_enabled=enabled,max_depth=4)
            d=p.choose(s,max_nodes=cap,seconds=1.)
            assert d.nodes==d.proof_nodes+d.verification_nodes+d.search_nodes<=cap
            assert d.proof_nodes<=cap//4 and d.verification_nodes<=cap//4
            if d.action is not None:assert d.action in legal_actions(s,c)


def test_unproved_win_falls_back_to_actual_material_search():
    c=compile_krk();s=krk_state(c,0,15,10,0)
    d=ProofMaterialPlayer(c,material).choose(s,max_nodes=128,seconds=1.)
    assert d.source in ('MATERIAL_SEARCH','LEGAL_FALLBACK') and d.proof_reason in ('node_budget','time_budget')
    assert d.action in legal_actions(s,c) and d.search_nodes>0


def test_proof_continuation_executes_after_every_opponent_defense():
    c=compile_krk();start=krk_state(c,0,2,10,1)
    from scripts.generic_win_proof import prove_win,StrategyCursor
    r=prove_win(c,start,target=0,max_nodes=65536,seconds=5.,max_depth=8)
    assert r.certificate is not None and len(r.certificate.tree.edges)==2
    # Take every initial defense through the real player's observe/choose API.
    for defense,_ in r.certificate.tree.edges:
        p=ProofMaterialPlayer(c,material);p.cursor=StrategyCursor(c,r.certificate,seconds=5.)
        p.observe(start,defense);s=apply_action(start,defense,c)
        while not s.terminal_status.is_terminal:
            if s.position.side_to_move==0:
                d=p.choose(s,max_nodes=128,seconds=1.)
                assert d.source=='PROOF_CONTINUATION' and d.nodes==0 and d.proof_rank>0
                a=d.action
            else:a=p.cursor.node.edges[-1][0]
            oldrank=p.cursor.node.rank
            p.observe(s,a);s=apply_action(s,a,c)
            assert p.cursor.node.rank<oldrank
        assert s.terminal_status.winner==0


def test_stale_cursor_is_discarded_and_cannot_commit_a_stale_move():
    c=compile_krk();s=krk_state(c,1,3,8,0);p=ProofMaterialPlayer(c,material)
    d=p.choose(s,max_nodes=4096,seconds=1.);assert d.source=='PROOF'
    different=krk_state(c,0,15,10,0)
    d=p.choose(different,max_nodes=64,seconds=1.)
    assert d.source!='PROOF_CONTINUATION'
    if d.action is not None:assert d.action in legal_actions(different,c)


def test_cancel_and_zero_time_never_dispatch_search_or_commit():
    c=compile_krk();s=krk_state(c,1,3,8,0)
    for args,cause in [({'cancel':lambda:True},'cancelled'),({'seconds':0},'time_budget')]:
        d=ProofMaterialPlayer(c,material).choose(s,**args)
        assert d.action is None and d.nodes==0 and d.exit_cause==cause


def test_proof_never_reads_material_evaluator():
    c=compile_krk();s=krk_state(c,1,3,8,0)
    def forbidden(*args):raise AssertionError('material leaked into proof')
    d=ProofMaterialPlayer(c,forbidden).choose(s,max_nodes=4096,seconds=1.)
    assert d.source=='PROOF' and d.search_nodes==0 and d.proof_rank==1


def test_failed_verification_retains_cost_and_uses_normal_search(monkeypatch):
    from scripts import generic_proof_player as module
    from scripts.generic_win_proof import StrategyCursor
    c=compile_krk();s=krk_state(c,1,3,8,0)
    def zero_verification(compiled,cert,**kwargs):
        return StrategyCursor(compiled,cert,max_nodes=0,seconds=1.)
    monkeypatch.setattr(module,'StrategyCursor',zero_verification)
    d=module.ProofMaterialPlayer(c,material).choose(s,max_nodes=4096,seconds=1.)
    assert d.proof_reason=='verification_node_budget'
    assert d.proof_nodes>0 and d.verification_nodes==0 and d.search_nodes>0
    assert d.source=='MATERIAL_SEARCH' and d.action in legal_actions(s,c)
    assert d.nodes<=4096


def test_price_independent_trigger_skips_new_proof_but_keeps_existing_strategy():
    c=compile_krk();s=krk_state(c,0,2,10,1)
    def forbidden(*args,**kwargs):raise AssertionError('untriggered proof called')
    p=ProofMaterialPlayer(c,material,proof_trigger=lambda state:False,proof_search=forbidden)
    d=p.choose(s,max_nodes=128,seconds=1.)
    assert d.proof_nodes==0 and d.verification_nodes==0 and d.proof_reason=='trigger_skipped'
    from scripts.generic_win_proof import StrategyCursor,prove_win
    cert=prove_win(c,s,target=0,max_nodes=65536,seconds=3.).certificate
    p.cursor=StrategyCursor(c,cert,seconds=3.)
    a=p.cursor.node.edges[0][0];p.observe(s,a);child=apply_action(s,a,c)
    d=p.choose(child,max_nodes=128,seconds=1.)
    assert d.source=='PROOF_CONTINUATION' and d.proof_nodes==0 and d.proof_rank>0



def no_progress_fixture():
    from generic_chess.rules.schema import RuleNoProgressDraw
    from generic_chess.rules.compiler import compile_ruleset
    from scripts.generic_proof_fixtures import krk_ruleset
    c=compile_ruleset(replace(krk_ruleset(4),no_progress_draw=RuleNoProgressDraw(10,True)))
    return c,krk_state(c,0,15,10,0)


def test_unsupported_proof_runtime_still_calls_provided_normal_player():
    c,s=no_progress_fixture();called=[]
    def normal(state,nodes,seconds,cancel):
        assert state==s and 0<nodes<=64 and seconds>0
        called.append(True);return legal_actions(state,c)[0],1
    d=ProofMaterialPlayer(c,None,normal_search=normal).choose(s,max_nodes=64,seconds=1.)
    assert called and d.source=='EXTERNAL_SEARCH'
    assert d.proof_reason=='unsupported_no_progress_history'
    assert d.action in legal_actions(s,c) and d.nodes==d.search_nodes==1
    assert not apply_action(s,d.action,c).terminal_status.is_terminal


def test_unsupported_internal_runtime_has_explicit_public_legal_fallback():
    c,s=no_progress_fixture()
    def forbidden(*args):raise AssertionError('unsupported internal AB must not pretend to search')
    d=ProofMaterialPlayer(c,forbidden).choose(s,max_nodes=64,seconds=1.)
    assert d.action in legal_actions(s,c) and d.source=='LEGAL_FALLBACK'
    assert d.exit_cause=='public_legal_fallback_unsupported_runtime'
    assert d.nodes==0 and d.proof_reason=='unsupported_no_progress_history'


def test_verified_continuation_checks_cancel_after_atomic_terminal(monkeypatch):
    from scripts import generic_proof_player as module
    from scripts.generic_win_proof import StrategyCursor, prove_win
    c=compile_krk();s=krk_state(c,1,3,8,0)
    cert=prove_win(c,s,max_nodes=4096,seconds=2.).certificate
    assert cert is not None
    for mode in ('cancel','time'):
        p=ProofMaterialPlayer(c,material);p.cursor=StrategyCursor(c,cert,seconds=2.)
        stopped=[False];clock=[0.];original=module.terminal_result
        def crossing(*args):
            result=original(*args);stopped[0]=True;clock[0]=2.;return result
        with monkeypatch.context() as patch:
            patch.setattr(module,'terminal_result',crossing)
            d=p.choose(s,max_nodes=64,seconds=1.,cancel=(lambda:stopped[0]) if mode=='cancel' else None,_clock=lambda:clock[0])
        assert d.action is None and d.source!='PROOF_CONTINUATION'
        assert d.exit_cause==('cancelled' if mode=='cancel' else 'time_budget')
        assert d.nodes==0 and p.cursor is not None


def test_new_verified_cursor_cannot_commit_after_cancel_during_choice():
    from scripts.generic_win_proof import StrategyCursor
    c=compile_krk();s=krk_state(c,1,3,8,0);flag=[False]
    class CancelAtChoice(StrategyCursor):
        def choose(self,state):
            choice=super().choose(state);flag[0]=True;return choice
    p=ProofMaterialPlayer(c,material,cursor_factory=CancelAtChoice)
    d=p.choose(s,max_nodes=4096,seconds=3.,cancel=lambda:flag[0])
    assert flag[0] and d.exit_cause=='cancelled' and d.action is None
    assert p.cursor is None and d.proof_nodes>0 and d.verification_nodes>0


@pytest.mark.parametrize('mode',['cancel','time'])
def test_real_external_material_search_receipt_is_checked_after_callback(mode):
    c=compile_krk();s=krk_state(c,0,15,10,0);flag=[False];clock=[0.];receipts=[]
    def normal(state,nodes,seconds,cancel):
        # Actual bounded material search, not a fake winning label or move.
        result=ProofMaterialPlayer(c,material,proof_enabled=False,max_depth=1).choose(state,max_nodes=32,seconds=1.)
        assert result.action in legal_actions(state,c) and result.search_nodes>0
        receipts.append(result);flag[0]=True;clock[0]=2.
        return result.action,result.search_nodes
    p=ProofMaterialPlayer(c,material,proof_enabled=False,normal_search=normal)
    result=p.choose(s,max_nodes=64,seconds=1.,cancel=(lambda:flag[0]) if mode=='cancel' else None,_clock=lambda:clock[0])
    assert result.exit_cause==('cancelled' if mode=='cancel' else 'time_budget')
    assert result.search_nodes==receipts[0].search_nodes and result.nodes==result.search_nodes
    if mode=='cancel':assert result.action is None
    else:assert result.action==receipts[0].action and result.source=='EXTERNAL_SEARCH'
    assert p.cursor is None and s.ply_count==0


def test_internal_material_cancel_does_not_return_a_move_for_commit():
    c=compile_krk();s=krk_state(c,0,15,10,0);flag=[False]
    def evaluate(position,target):
        score=material(position,target);flag[0]=True;return score
    result=ProofMaterialPlayer(c,evaluate,proof_enabled=False,max_depth=2).choose(s,max_nodes=64,seconds=1.,cancel=lambda:flag[0])
    assert result.exit_cause=='cancelled' and result.action is None and result.search_nodes>0
