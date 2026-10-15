"""Exact fresh-root admission through public setup, never state/history injection."""
from dataclasses import replace
import pytest
from generic_chess.rules import build_western_chess_ruleset,compile_ruleset_for_execution
from generic_chess.rules.schema import RuleInitialSetupOption
from generic_chess.session.session import GameSession
from scripts.generic_proof_fixtures import krk_ruleset,krk_state
from scripts.generic_session_setup import fresh_setup_session
from scripts.generic_session_win_proof import prove_session_win,verify_session_certificate


def test_named_setup_replays_real_fresh_state_with_new_fingerprint():
    rules=krk_ruleset(4);compiled=compile_ruleset_for_execution(rules)
    state=krk_state(compiled,1,3,8,0)
    original=state
    extended,session=fresh_setup_session(rules,state,setup_key='known-fresh-root')
    assert extended.initial_position==rules.initial_position and not rules.initial_setup_options
    assert state is original and session.state.position.board==state.position.board
    assert session.compiled.ruleset_fingerprint!=compiled.ruleset_fingerprint
    assert session.to_record().initial_setup_key=='known-fresh-root' and session.to_record().schema_version==3
    assert GameSession.replay(session.compiled,session.to_record()).state==session.state
    # An actual one-move board mate needs no manufactured declaration or price.
    proof=prove_session_win(session,max_depth=1,seconds=3.)
    assert proof.status=='PROVEN_WIN' and verify_session_certificate(session,proof.certificate,seconds=3.)['verified']


def test_builtin_semantic_aux_rights_are_preserved_in_fresh_alternate_board():
    from generic_chess.core.identity import repetition_identity_key
    from generic_chess.core.position import HistoryRecord
    from generic_chess.core.terminal import terminal_result
    rules=build_western_chess_ruleset();current=GameSession(compile_ruleset_for_execution(rules))
    board=list(current.state.position.board);board[16]=board[8];board[8]=None
    position=replace(current.state.position,board=tuple(board));key=repetition_identity_key(position,current.compiled)
    state=replace(current.state,position=position,repetition_counts=((key,1),),history=(HistoryRecord(key,-1,'',False),))
    state=replace(state,terminal_status=terminal_result(state,current.compiled))
    _,session=fresh_setup_session(rules,state,setup_key='fresh-semantic-pawn-layout')
    assert session.state.position.board==state.position.board
    assert session.state.position.aux_state==state.position.aux_state
    assert len(session.state.history)==1 and session.state.history[0].actor==-1
    assert GameSession.replay(session.compiled,session.to_record()).state==session.state


def test_actual_played_history_is_never_reset_even_when_board_is_legal():
    rules=krk_ruleset(4);current=GameSession(compile_ruleset_for_execution(rules))
    current.submit(current.legal_actions()[0]);record=current.to_record();state=current.state
    with pytest.raises(ValueError,match='not expressible'):
        fresh_setup_session(rules,state,setup_key='cannot-reset')
    assert current.state==state and current.to_record()==record and state.ply_count==1 and len(state.history)==2


def test_fresh_noninitial_side_is_rejected_without_adding_a_fake_prefix():
    rules=krk_ruleset(4);compiled=compile_ruleset_for_execution(rules)
    state=krk_state(compiled,0,2,10,1)
    with pytest.raises(ValueError,match='not expressible'):
        fresh_setup_session(rules,state,setup_key='cannot-express-turn1')
    assert state.ply_count==0 and state.position.side_to_move==1


def test_existing_setup_key_and_mismatched_source_rules_are_not_overwritten():
    rules=krk_ruleset(4);compiled=compile_ruleset_for_execution(rules)
    alt=krk_state(compiled,1,3,8,0).position.board
    rows=tuple(tuple(alt[i:i+4]) for i in range(0,16,4))
    rules=replace(rules,initial_setup_options=(RuleInitialSetupOption('kept',rows),))
    state=GameSession(compile_ruleset_for_execution(rules)).state
    with pytest.raises(ValueError,match='already exists'):fresh_setup_session(rules,state,setup_key='kept')
    with pytest.raises(ValueError,match='fingerprint mismatch'):fresh_setup_session(replace(rules,max_ply=63),state,setup_key='new')
    assert rules.initial_setup_options[0].setup_key=='kept'


def test_forged_fresh_history_and_repetition_count_are_not_silently_rebound():
    from generic_chess.core.position import HistoryRecord
    rules=krk_ruleset(4);compiled=compile_ruleset_for_execution(rules)
    state=krk_state(compiled,1,3,8,0);key=state.history[0].position_key
    variants=[replace(state,repetition_counts=((key,2),)),replace(state,history=()),
              replace(state,history=(HistoryRecord(key,0,'played',False),)),replace(state,ply_count=False)]
    for value in variants:
        with pytest.raises(ValueError,match='existing history is never reset'):
            fresh_setup_session(rules,value,setup_key='reject-corruption')
