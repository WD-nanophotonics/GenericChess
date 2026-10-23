from copy import deepcopy
from pathlib import Path
import pytest
from scripts.leaper_explorer_truth import load
from scripts.verify_leaper_twoa_safety import verify,SOURCE
from scripts.leaper_clock_rebinding import verify_history_draw_safety

DATA=Path('docs/research/data/leaper_scope_and_headroom_20261024')


def test_rejects_incomplete_attacker_frontier():
    cert=load(DATA/'twoa-safety.json.gz');root=cert['roots'][0]['local_root'];row=cert['safety_rows'][root]
    assert len(row['actions'])>1
    row['actions']=row['actions'][:-1];row['children']=row['children'][:-1]
    with pytest.raises(ValueError,match='attacker frontier incomplete'):verify(cert,load(SOURCE))


def test_barrier_claim_cannot_borrow_equal_position_clock_win_history():
    cert=load(DATA/'twoa-barrier-safety.json.gz');win=load(DATA/'twoa-equalclock.json')
    cert['roots'][0]['record']=win['record'];cert['roots'][0]['state_sha']=win['state_sha']
    with pytest.raises(ValueError,match='barrier lacks actual prehistory'):verify(cert,load(SOURCE))


def test_current_count3_root_is_not_an_arrival_only_sink():
    cert=load(DATA/'twoa-barrier-safety.json.gz');root=cert['roots'][0]['local_root']
    assert root in cert['barriers']
    cert['safety_rows'][root]=dict(index=root,goal='prior_arrival_draw')
    with pytest.raises(ValueError,match='invalid future-arrival exit'):verify(cert,load(SOURCE))


def test_rule_terminal_change_is_outside_original_truth_certificate():
    cert=load(DATA/'twoa-safety.json.gz');cert['rule']['stalemate_result']='loss'
    with pytest.raises(ValueError,match='full source rule differs'):verify(cert,load(SOURCE))


def test_singleton_scale_extension_keeps_original4x4_admission():
    row=load(DATA/'singletons.json.gz')['rows'][0]
    assert row['n']==5
    with pytest.raises(ValueError,match='requires ordinary4x4'):verify_history_draw_safety(row['safety_certificate'],row['rule'],row['record'],row['safety'])
    with pytest.raises(ValueError,match='complete rule differs'):verify_history_draw_safety(row['safety_certificate'],row['rule'],row['record'],row['safety'],frozen_singleton=dict(n=5,mask=17))
