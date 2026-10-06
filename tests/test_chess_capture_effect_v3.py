import hashlib,json
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from scripts.chess_capture_effect_hint_v3 import ChessCaptureEffectHintV3
from scripts.native_chess_contact_intervals import FINGERPRINT
ROOT=Path(__file__).resolve().parents[1]


def test_actual_native_mirror_qsearch_scope_and_pins():
    r=json.loads((ROOT/'docs/research/data/chess_capture_effect_v3_20261006.json').read_text())
    assert r['complete'] and r['source_hashes_unchanged'] and r['seconds']<15
    for p,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin
    assert r['public_transitions']==r['source_pushes']==6
    assert r['runtime_pushes']==r['runtime_pops']==10 and r['entries']==83
    assert len(r['pattern_bits'])==20 and len(r['excluded_drop_patterns'])==5
    assert r['reference_noisy']==['e4d3'] and len(r['children'])==5
    old,new=r['runs'];assert old['score']==0 and new['score']==r['reference_score']==17417
    assert new['runtime_pushes']==5 and new['entries']==33
    assert new['stats']['qnodes']==2 and new['stats']['capture_qactions']==1
    assert r['children']['e4d3']['is_ep'] and r['children']['e4d3']['is_capture']


def test_second_global_hint_failure_is_kept_with_zero_events():
    r=json.loads((ROOT/'docs/research/data/chess_capture_effect_v2_20261006.json').read_text())
    assert not r['complete'] and r['error']=='ValueError: unqualified effect vocabulary'
    assert r['public_transitions']==r['runtime_pushes']==r['source_pushes']==0
    for p,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin


def test_actual_effect_catalog_explains_first_failure_and_later_rights():
    r=json.loads((ROOT/'docs/research/data/chess_capture_vocabulary_20261006.json').read_text())
    assert r['complete'] and r['terms']==50 and r['public_transitions']==0
    rows=[p for p in r['patterns'] if p['unsupported_v2']]
    assert len(rows)==5 and all(p['geometries']==['drop'] for p in rows)
    assert all(p['unsupported_v2']==['remove_from_hand','place'] for p in rows)
    assert rows[0]['pattern_id']=='legacy_064'
    rights=[p for p in r['patterns'] if p['unsupported_v1']==['clear_right']]
    assert len(rights)==4 and not any(p['unsupported_v2'] for p in rights)
    for p,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin


def test_excluded_drop_is_not_accepted_as_quiet_board_action():
    geometry={'d':NS(kind='drop'),'b':NS(kind='leap')}
    drop=NS(pattern_id='drop',geometry_ids=['d'],effects=[NS(kind='place')])
    quiet=NS(pattern_id='quiet',geometry_ids=['b'],effects=[NS(kind='clear_right')])
    h=ChessCaptureEffectHintV3(FINGERPRINT,[drop,quiet],geometry)
    assert not h.legal_pattern_captures('quiet') and h.excluded==['drop']
    with pytest.raises(ValueError,match='excluded'):h.legal_pattern_captures('drop')
    with pytest.raises(ValueError,match='mixed'):
        ChessCaptureEffectHintV3(FINGERPRINT,[NS(pattern_id='mixed',geometry_ids=['d','b'],effects=[])],geometry)
