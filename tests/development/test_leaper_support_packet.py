"""Public packet provenance, deadline and data-only capsule boundaries."""
from pathlib import Path
from datetime import datetime,timedelta
import gzip,hashlib,json,shutil
import pytest
from scripts.verify_leaper_delayed_capture import load
from scripts.verify_leaper_support_packet import qualify
from scripts.leaper_radius_admission import qualify as radius_qualify

BASE=Path(__file__).resolve().parents[2]/'docs/research/data'
DATA=BASE/'leaper_support_and_delayed_win_20261024'
OLD=BASE/'leaper_delayed_capture_20261024'


def replace_payload(root,name,payload):
    encoded=(json.dumps(payload,ensure_ascii=False,sort_keys=True)+'\n').encode()
    raw=gzip.compress(encoded,mtime=0)if name.endswith('.gz')else encoded
    (root/name).write_bytes(raw)
    manifest=load(root/'manifest.json');row=manifest['files'][name]
    row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),private_original_sha256=hashlib.sha256(encoded).hexdigest())
    (root/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')


def test_complete_public_packet_binds_nine_components_without_capsule_execution():
    q=qualify(DATA,OLD)
    assert q['hashed_files']==65 and q['unique_full_records']==208
    assert q['planned_explicit_new_target_moves']==157
    assert q['source_capsule_executions']==q['new_Player_queries']==q['new_graph_or_solver_calls']==0


def test_an_archived_source_string_is_data_even_when_it_would_raise(tmp_path):
    root=tmp_path/'capsule';shutil.copytree(DATA,root)
    name='helper-posthoc-source.json.gz';payload=load(root/name)
    payload['source_utf8']='raise RuntimeError("source capsule was executed")\n'
    payload['sha256']=hashlib.sha256(payload['source_utf8'].encode()).hexdigest()
    replace_payload(root,name,payload)
    assert qualify(root,OLD)['source_capsule_executions']==0


def test_rehashed_receipt_cannot_extend_original_deadline(tmp_path):
    root=tmp_path/'deadline';shutil.copytree(DATA,root)
    name='existence-registration.json.gz';payload=load(root/name)
    payload['original_deadline']=(datetime.fromisoformat(payload['original_deadline'])+timedelta(days=1)).isoformat()
    replace_payload(root,name,payload)
    with pytest.raises(AssertionError,match='original deadline changed'):qualify(root,OLD)


def test_sharp_radius_bound_preserves_failed_and_successful_controls():
    reg=load(DATA/'radius-admission-registration.json');m=load(DATA/'radius-admission.json.gz')
    q=radius_qualify(reg,m)
    assert q['admission_thresholds']==[4,5]
    assert q['leading_n6']==[-46,-70]and q['leading_n5']==[84,192]


def test_radius_control_cannot_be_replaced_by_a_duplicate():
    from copy import deepcopy
    reg=load(DATA/'radius-admission-registration.json');m=load(DATA/'radius-admission.json.gz')
    m['controls'][2]=deepcopy(m['controls'][0])
    with pytest.raises(AssertionError):radius_qualify(reg,m)


def test_prospective_input_cannot_silently_change_the_clock(tmp_path):
    root=tmp_path/'next-clock';shutil.copytree(DATA,root)
    name='next-b-tempo.json';payload=load(root/name)
    payload['proposed_rule']['max_ply']=64
    replace_payload(root,name,payload)
    with pytest.raises(AssertionError,match='prospective full rule'):
        qualify(root,OLD)
