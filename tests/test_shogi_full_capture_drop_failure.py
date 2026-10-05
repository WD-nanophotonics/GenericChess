"""Preserve observed cap failure; never turn the unexecuted drop into evidence."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_failed_family_stops_before_drop_without_clipping_counter():
    raw=json.loads((ROOT/'docs/research/data/shogi_full_capture_drop_20261006.json').read_text())
    assert not raw['complete'] and raw['source_hashes_unchanged'] and raw['initial_restored']
    assert raw['error']=='ValueError: cumulative5000 enumeration cap'
    assert raw['runtime_pushes']==raw['runtime_pops']==len(raw['path'])==5
    assert raw['cumulative_pushes']==71 and raw['conservative_enumeration_charge']==5010>5000
    assert raw['prior_charge']+raw['new_preflight_charge']+raw['candidates']+raw['returned_actions']==5010
    assert raw['path'][-1]['row']==[0]*8
    assert 'drop_threshold' not in raw and 'final_row' not in raw
    assert all('base_type_id' not in step['action'] and '@' not in step['action'] for step in raw['path'])
    for path,pin in raw['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
