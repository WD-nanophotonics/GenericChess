"""Actual saved-source exposure controls; no new game or Player execution."""
from copy import deepcopy
from pathlib import Path
import gzip
import hashlib
import json

import pytest
from scripts.audit_published_leaper_exposure import audit_exposure, prefix_stopping_diagnostics


@pytest.fixture(scope='module')
def source_slice():
    path=Path('tests/fixtures/published_leaper_exposure_slice.json.gz')
    return json.loads(gzip.decompress(path.read_bytes()))


def audit(fixture, **options):
    return audit_exposure(*(fixture[k] for k in ('packet','games','raw_returns','plan','executed')), **options)


def alter_original(fixture, query, **changes):
    """Keep wrapper integrity valid while challenging the semantic binding."""
    entry=fixture['raw_returns'][str(query['query_id'])]
    original=json.loads(entry['original_utf8'])
    query.update(changes);original.update(changes)
    entry['original_utf8']=json.dumps(original)
    entry['sha256']=hashlib.sha256(entry['original_utf8'].encode()).hexdigest()


def test_actual_saved_source_replays_and_discloses_empty_pvs(source_slice):
    result=audit(source_slice)
    assert result['counts']['saved_games']==2
    assert result['counts']['saved_actual_actions_replayed']==120
    assert result['counts']['unique_full_decision_contexts']==115
    assert result['counts']['matched_long_short_contexts']==5
    assert result['counts']['matched_same_action']==4
    assert result['counts']['matched_changed_action']==1
    assert result['counts']['empty_PV_returns']==2
    assert all(q['minimax_value']=='UNLABELLED' for q in result['queries'])
    assert result['prefix_stopping_diagnostics'][0]['common_actual_move_prefix']==4
    assert all(result[k]==0 for k in ('new_Player_calls','new_solver_calls','new_games'))


def test_tampered_original_bytes_are_rejected(source_slice):
    data=deepcopy(source_slice)
    data['raw_returns']['0']['original_utf8']+=' '
    with pytest.raises(ValueError,match='bytes hash'):
        audit(data,verify_pvs=False)


def test_query_cannot_silently_change_saved_return(source_slice):
    data=deepcopy(source_slice);data['games'][0]['queries'][0]['decision']['score']+=1
    with pytest.raises(ValueError,match='original returned'):
        audit(data,verify_pvs=False)


@pytest.mark.parametrize('field,value,match',[
    ('record_before_sha256','different-history','incoming record'),
    ('seat',1,'clock/seat'),('seat',False,'integers'),
    ('ply_before',3,'clock/seat'),('case_id','another-case','different game'),
    ('policy','short','resource policy'),('requested_seconds',0.5,'resource policy'),
    ('choose_wall_seconds',float('nan'),'actual cost|original returned'),
    ('choose_wall_seconds',float('inf'),'actual cost'),
    ('choose_cpu_seconds',-1,'actual cost'),
    ('timing_eligible',False,'timing qualification'),
])
def test_forged_metadata_still_fails_literal_binding(source_slice,field,value,match):
    data=deepcopy(source_slice);q=data['games'][0]['queries'][0]
    alter_original(data,q,**{field:value})
    with pytest.raises(ValueError,match=match):audit(data,verify_pvs=False)


def test_after_record_hash_cannot_be_replaced_by_a_position_hash(source_slice):
    data=deepcopy(source_slice);data['games'][0]['queries'][0]['record_after_sha256']='position-only'
    with pytest.raises(ValueError,match='after-record'):audit(data,verify_pvs=False)


def test_unknown_extra_validation_fields_are_not_implicitly_trusted(source_slice):
    data=deepcopy(source_slice);data['games'][0]['queries'][0]['root_WDL']=0
    with pytest.raises(ValueError,match='unexpected validation'):audit(data,verify_pvs=False)


def test_unbound_return_is_not_deleted_from_denominator(source_slice):
    data=deepcopy(source_slice);data['raw_returns']['120']=deepcopy(data['raw_returns']['0'])
    with pytest.raises(ValueError,match='unbound original'):audit(data,verify_pvs=False)


def test_false_saved_pv_continuation_is_rejected(source_slice):
    data=deepcopy(source_slice);q=data['games'][0]['queries'][0]
    d=deepcopy(q['decision']);d['principal_variation'][1]['pattern_id']='uncompiled'
    alter_original(data,q,decision=d)
    with pytest.raises(ValueError,match='PV continuation'):audit(data)


def test_boolean_long_seat_not_silently_accepted_as_zero(source_slice):
    data=deepcopy(source_slice);data['games'][0]['long_seat']=False
    with pytest.raises(ValueError,match='policy seat'):audit(data,verify_pvs=False)


def test_missing_game_cannot_become_a_smaller_successful_sample(source_slice):
    data=deepcopy(source_slice);data['games'].pop()
    with pytest.raises(ValueError,match='planned denominator'):audit(data,verify_pvs=False)


def test_draw_outcome_does_not_label_all_its_decisions(source_slice):
    result=audit(source_slice,verify_pvs=False)
    assert any(g['result']['winner']is None for g in result['games'])
    assert all(q['minimax_value']=='UNLABELLED'for q in result['queries'])
    assert all(q['quality']=='UNKNOWN_ACTION_QUALITY'for q in result['queries']if q['legal_actions']>1)