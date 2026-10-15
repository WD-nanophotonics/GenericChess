"""Qualify experimental batched forward states against actual Session authority."""
from dataclasses import replace
import pytest
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.rules import compile_ruleset_for_execution,build_western_chess_ruleset
from generic_chess.rules.schema import RuleNoProgressDraw
from scripts.generic_win_proof import _Budget,_same_state
from scripts.generic_session_win_proof import execute,verify_session_certificate
from scripts.generic_session_win_proof_pn import prove_session_win_pn
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn,_Forward,_children
from test_generic_session_win_proof import session,claim
from test_generic_session_proof_mechanisms import played,layout
from scripts.generic_proof_fixtures import krk_ruleset
from generic_chess.core.pieces import Piece


def fixtures():
    yield session()
    yield session(claim(0,'WIN'),claim(0,'LOSS','second'),claim(0,'RESTART','third'))
    yield session(claim(1,'LOSS'),k=0,b=2,r=10,turn=1)
    rs=replace(krk_ruleset(4),drop_allowed={'R':((True,)*16,)*2},capture_disposition='capture_to_hand')
    rs=layout(rs,[(1,Piece(0,'K','K')),(3,Piece(1,'K','K')),(4,Piece(0,'R','R')),(8,Piece(1,'R','R'))])
    yield played(rs,['a2a3','d1d2'])
    yield GameSession(compile_ruleset_for_execution(replace(krk_ruleset(4),no_progress_draw=RuleNoProgressDraw(1,True))))
    yield GameSession(compile_ruleset_for_execution(build_western_chess_ruleset()))


@pytest.mark.parametrize('index',range(6))
def test_every_batched_child_binds_full_actual_session_record_state_result(index):
    s=list(fixtures())[index];root=s.to_record();cost=[0,0]
    forward=_Forward(s.compiled,s.state,root,s.result)
    children=list(_children(forward,_Budget(65536,10.,None),cost))
    assert cost[0]==len(s.legal_actions()) and cost[1]==sum(d.owner==s.state.position.side_to_move for d in s.compiled.declarations)
    for choice,child in children:
        actual=GameSession.replay(s.compiled,root);execute(actual,choice)
        assert _same_state(child.state,actual.state) and _same_state(child.record,actual.to_record()) and _same_state(child.result,actual.result)
    assert _same_state(root,s.to_record())


@pytest.mark.parametrize('kind',['claim','defense','drop','no_progress'])
def test_same_budget_tree_and_independent_actual_session_verification(kind):
    s={'claim':lambda:session(claim(0,'WIN')),
       'defense':lambda:session(claim(1,'LOSS'),k=0,b=2,r=10,turn=1),
       'drop':lambda:list(fixtures())[3],
       'no_progress':lambda:list(fixtures())[4]}[kind]()
    target=0
    kwargs=dict(target=target,max_nodes=65536,seconds=5.,max_depth=8)
    old=prove_session_win_pn(s,**kwargs);new=prove_session_win_batch_pn(s,**kwargs)
    assert new.status==old.status and new.nodes==old.nodes and new.transitions==old.transitions
    assert new.certificate==old.certificate
    if new.certificate is not None:assert verify_session_certificate(s,new.certificate,max_nodes=65536,seconds=5.)['verified']


def test_batch_crossing_atomic_cancel_or_deadline_returns_unknown(monkeypatch):
    import scripts.generic_session_win_proof_batch_pn as m
    original=m.legal_successors;s=session();root=s.to_record();flag=[False]
    def crossing(*args):
        out=original(*args);flag[0]=True;return out
    monkeypatch.setattr(m,'legal_successors',crossing)
    result=prove_session_win_batch_pn(s,cancel=lambda:flag[0],seconds=3.)
    assert result.status=='UNKNOWN' and result.reason=='cancelled' and result.certificate is None
    assert result.eager_board_successors>0 and result.transitions==0 and s.to_record()==root


def test_immediate_claim_still_avoids_eager_board_batch(monkeypatch):
    import scripts.generic_session_win_proof_batch_pn as m
    def forbidden(*args):raise AssertionError('irrelevant board batch')
    monkeypatch.setattr(m,'legal_successors',forbidden)
    s=session(claim(0,'WIN'));r=prove_session_win_batch_pn(s,seconds=3.)
    assert r.status=='PROVEN_WIN' and r.claims_assessed==1 and r.eager_board_successors==0
    assert verify_session_certificate(s,r.certificate,seconds=3.)['verified']


def test_losing_claim_prefix_does_not_hide_later_actual_restart():
    s=session(claim(1,'LOSS','a_loss'),claim(1,'RESTART','z_restart'),k=0,b=2,r=10,turn=1)
    r=prove_session_win_batch_pn(s,target=0,seconds=3.)
    assert r.status=='UNKNOWN' and r.certificate is None and r.claims_assessed==2 and r.eager_board_successors==0

@pytest.mark.parametrize('name',[
    'test_actual_capture_hand_then_drop_mate_is_preserved',
    'test_real_forced_promotion_mate_retains_base_piece',
    'test_real_pass_draw_defense_cannot_be_omitted',
    'test_actual_played_perpetual_history_win_is_not_mislabeled_mate',
    'test_actual_no_progress_draw_and_depth_unknown_remain_distinct',
    'test_semantic_action_ids_survive_transport_and_forged_ids_fail_public_execution'])
def test_existing_physical_mechanism_controls_with_batched_model(name):
    import test_generic_session_proof_mechanisms as controls
    getattr(controls,name)(prove_session_win_batch_pn)


def test_batched_witness_can_feed_actual_session_player_without_default_switch():
    from test_generic_session_proof_player import player
    from scripts.generic_session_proof_player import commit_session_decision
    s=session(claim(0,'WIN'));p=player(s,proof_search=prove_session_win_batch_pn)
    d=p.choose(s,max_nodes=4096,seconds=3.)
    assert d.source=='PROOF' and d.proof_nodes==2
    assert commit_session_decision(s,d,[p]).winner==0 and p.cursor.node.rank==0

@pytest.mark.parametrize('outcome',['NO_CONTEST','RESTART','LOSS','WIN'])
def test_all_supported_declaration_outcomes_and_real_scores_match_session(outcome):
    from generic_chess.rules.schema import RuleDeclaration,RuleWeightedMaterialMetric,RuleDeclarationOutcomeBand
    declaration=RuleDeclaration('scored',0,require_not_in_check=False,
        weighted_metric=RuleWeightedMaterialMetric(weights={'R':5}),
        outcome_bands=(RuleDeclarationOutcomeBand(5,outcome),),failure_outcome='LOSS')
    s=session(declaration);root=s.to_record();forward=_Forward(s.compiled,s.state,root,s.result)
    choice,child=next(_children(forward,_Budget(4096,3.,None),[0,0]))
    actual=GameSession.replay(s.compiled,root);actual.declare('scored')
    assert _same_state(child.result,actual.result) and _same_state(child.record,actual.to_record())
    assert child.result.declaration_score==5 and actual.to_record().declaration.weighted_score==5
    if outcome in ('NO_CONTEST','RESTART'):assert child.result.winner is None


def test_conditional_claim_changes_after_real_capture_without_history_reset():
    from generic_chess.rules.schema import RuleDeclaration,RuleWeightedMaterialMetric,RuleDeclarationOutcomeBand
    from scripts.generic_proof_rnb_bridge import uci
    declaration=RuleDeclaration('scored',0,require_not_in_check=False,
        weighted_metric=RuleWeightedMaterialMetric(weights={'R':5}),
        outcome_bands=(RuleDeclarationOutcomeBand(5,'WIN'),RuleDeclarationOutcomeBand(0,'RESTART')),failure_outcome='LOSS')
    s=session(declaration,k=0,b=3,r=6)
    old=next(_children(_Forward(s.compiled,s.state,s.to_record(),s.result),_Budget(4096,3.,None),[0,0]))[1]
    assert old.result.winner==0 and old.result.declaration_score==5
    for text in ['a1a2','d1c2']:s.submit(next(a for a in s.legal_actions() if uci(a)==text))
    root=s.to_record();child=next(_children(_Forward(s.compiled,s.state,root,s.result),_Budget(4096,3.,None),[0,0]))[1]
    actual=GameSession.replay(s.compiled,root);actual.declare('scored')
    assert child.result.winner is None and child.result.declaration_score==0 and child.result.declaration_outcome=='RESTART'
    assert _same_state(child.record,actual.to_record()) and _same_state(child.state,actual.state)
    assert len(child.state.history)==3 and len(child.record.actions)==2


def test_rule_metric_counts_actual_hands_and_preserves_claim_score():
    from generic_chess.rules.schema import RuleDeclaration,RuleWeightedMaterialMetric,RuleDeclarationOutcomeBand
    declaration=RuleDeclaration('hand-score',0,require_not_in_check=False,
        weighted_metric=RuleWeightedMaterialMetric(weights={'R':5},include_hands=True),
        outcome_bands=(RuleDeclarationOutcomeBand(10,'WIN'),),failure_outcome='LOSS')
    # These are fixed RULE claim weights, never a learning reward or candidate theta.
    rs=replace(krk_ruleset(4),drop_allowed={'R':((True,)*16,)*2},capture_disposition='capture_to_hand',declarations=(declaration,))
    rs=layout(rs,[(1,Piece(0,'K','K')),(3,Piece(1,'K','K')),(4,Piece(0,'R','R')),(8,Piece(1,'R','R'))])
    s=played(rs,['a2a3','d1d2']);root=s.to_record()
    choice,child=next(_children(_Forward(s.compiled,s.state,root,s.result),_Budget(4096,3.,None),[0,0]))
    actual=GameSession.replay(s.compiled,root);actual.declare(choice.declaration_id)
    assert child.result.winner==0 and child.result.declaration_score==10
    assert _same_state(child.result,actual.result) and _same_state(child.record,actual.to_record())
