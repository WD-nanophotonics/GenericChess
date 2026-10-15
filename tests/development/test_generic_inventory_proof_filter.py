"""Actual Session histories: absence filtering never produces a draw or move."""
from functools import lru_cache
from pathlib import Path
import json
import pytest
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_inventory_proof_filter import InventoryNoWinFilter
from scripts.generic_session_win_proof import verify_session_certificate

@lru_cache(None)
def guard():
    return InventoryNoWinFilter('results/dev_aux/task1895','results/dev_aux/task1896/coverage.json')

def actual(name):
    d=json.loads(Path('results/dev_aux/task1897/actual_records.json').read_text());c=compile_ruleset_for_execution(deserialize_ruleset(Path(d['rules']).read_text()))
    return GameSession.replay(c,deserialize_game_record(json.dumps(d['records'][name]['record'])))

@pytest.mark.parametrize('name',['KK','KKN'])
def test_played_dead_inventory_preserves_full_history_and_unknown(name):
    s=actual(name);record=s.to_record();state=s.state;assert len(record.actions)>0 and guard().eligible(s)
    result=guard()(s,max_nodes=16384,seconds=1.5,max_depth=64)
    assert result.status=='UNKNOWN' and result.reason=='certified_inventory_no_win' and result.certificate is None and result.nodes==0
    assert s.to_record()==record and s.state==state and s.result.winner is None

def test_rook_inventory_remains_actual_full_proof_search():
    s=actual('KKR');assert not guard().eligible(s)
    result=guard()(s,max_nodes=1024,seconds=3.,max_depth=64)
    assert result.nodes>0 and result.reason!='certified_inventory_no_win'
    if result.certificate:assert verify_session_certificate(s,result.certificate,seconds=3.)['verified']

def test_cancelled_dead_inventory_has_no_synthetic_result_or_side_effect():
    s=actual('KK');before=s.to_record();result=guard()(s,cancel=lambda:True)
    assert result.reason=='cancelled' and result.status=='UNKNOWN' and result.certificate is None and s.to_record()==before

@pytest.mark.parametrize('target',[True,-1,2])
def test_invalid_target_cannot_be_hidden_by_dead_inventory(target):
    with pytest.raises(ValueError):guard()(actual('KK'),target=target)

def test_forged_played_state_is_not_admitted_as_a_public_record():
    from dataclasses import replace
    s=actual('KK');s._state=replace(s.state,ply_count=s.state.ply_count+1)
    with pytest.raises(ValueError):guard()(s,seconds=3.)

@pytest.mark.parametrize('name',[
 'test_actual_capture_hand_then_drop_mate_is_preserved',
 'test_real_forced_promotion_mate_retains_base_piece',
 'test_real_pass_draw_defense_cannot_be_omitted',
 'test_actual_played_perpetual_history_win_is_not_mislabeled_mate',
 'test_actual_no_progress_draw_and_depth_unknown_remain_distinct',
 'test_semantic_action_ids_survive_transport_and_forged_ids_fail_public_execution'])
def test_other_rule_mechanisms_fall_through_to_full_actual_prover(name):
    import test_generic_session_proof_mechanisms as controls
    getattr(controls,name)(guard())

def test_scored_or_terminal_declarations_are_not_material_deadness():
    from test_generic_session_win_proof import session,claim
    s=session(claim(0,'WIN'));assert not guard().eligible(s)
    result=guard()(s,seconds=3.,max_depth=8)
    assert result.status=='PROVEN_WIN' and verify_session_certificate(s,result.certificate,seconds=3.)['verified']
