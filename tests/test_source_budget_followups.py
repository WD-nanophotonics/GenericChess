from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def load(n):return json.loads((ROOT/'docs/research/data'/n).read_text())

def test_mixed_source_partial_controls_not_reprobed():
    old=load('mixed_syzygy_source_20261006.json');new=load('mixed_syzygy_source_v2_20261006.json')
    assert not old['complete'] and old['outer_wdl_calls']==10
    assert 'owner/base inventory increased' in old['error']
    assert new['complete'] and len(new['rows'])==24 and new['rows'][:10]==old['rows']
    assert new['outer_wdl_calls']==24 and new['prior_outer_wdl_calls']==10
    qq=next(x for x in new['rows'] if x['material']=='KQQvK')
    pieces=[p for p in qq['request']['local_state']['position']['board'] if p and p['current_type_id']=='Q']
    assert sorted(p['base_type_id'] for p in pieces)==['P','Q']
    assert all(x['source_wdl50'] in (-2,-1,0,1,2) for x in new['rows'])

def test_bare_minor_geometric_coverage_and_dispatch_scope():
    r=load('bare_minor_mate_geometry_20261006.json');d=load('bare_minor_escape_dispatch_20261006.json')
    assert r['complete'] and r['no_bare_minor_checkmate']
    assert all(x['worlds']==223944 and x['checked_worlds']==x['escape_witnesses'] for x in r['modes'].values())
    assert d['complete'] and len(d['rows'])==16 and d['public_transitions']==52
    assert {(x['mode'],x['origin'],x['bk']) for x in d['rows']}=={(m,o,k) for m in 'NB' for o in (m,'P') for k in (0,7,27,63)}

def test_mixed_capture_complete_tie_risk():
    r=load('rook_knight_capture_fork_20261006.json')
    assert r['complete'] and r['choices_frozen_before_probes']
    assert len(r['children'])==r['public_transitions']==r['outer_probe_calls']==4
    assert r['policies']['unit']['full_ties']==['c3b3','c3c2']
    assert r['policies']['unit']['utility_interval']==[-1,0]
    for law in ('geometric_half','linear_mixture'):
        assert r['policies'][law]['full_ties']==['c3b3']
        assert r['policies'][law]['regret_interval']==[0,0]
    assert r['children']['c3b3']['source_root_utility']==0
    assert r['children']['c3c2']['source_root_utility']==-1

def test_followup_input_integrity():
    for name in ('mixed_syzygy_source_20261006.json','mixed_syzygy_source_v2_20261006.json','bare_minor_mate_geometry_20261006.json','bare_minor_escape_dispatch_20261006.json','rook_knight_capture_fork_20261006.json'):
        r=load(name);assert r['source_hashes_unchanged']
        for p,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin
