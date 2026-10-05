import hashlib,json
from pathlib import Path
from scripts.audit_shogi_promotion_cubes import coordinate_steps,PROFILES
ROOT=Path(__file__).resolve().parents[1]
def test_real_shogi_selected_profiles_have_full_ordered_qualification():
    r=json.loads((ROOT/'docs/research/data/shogi_promotion_qualified_20261005.json').read_text())
    assert r['complete'] and len(r['rows'])==24 and len(r['controls'])==12 and r['worlds']==151680
    assert r['canonical_candidates']==1056 and r['enumerated']==74 and r['cumulative_seconds']<15
    assert r['public_transitions']==r['source_queries']==0
    for row in r['rows']:
        assert sum(row['counts'].values())==row['worlds']==6320 and row['first_mismatch'] is None
        assert row['cube_sha256']==row['coordinate_sha256']
    assert all(x['actual']==x['expected'] for x in r['controls'])
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
def test_coordinate_options_preserve_forced_modes_and_owner_rotation():
    assert set(coordinate_steps(49,0,0))=={(58,0),(58,2)}
    assert set(coordinate_steps(67,0,0))=={(76,2)}
    assert set(coordinate_steps(58,1,0))=={(75,3),(77,3)}
    assert set(coordinate_steps(40,2,0))=={(49,2),(48,2),(50,2),(39,2),(41,2),(31,2)}
    for mode in range(4):assert set(coordinate_steps(13,mode,1))=={(80-d,p) for d,p in coordinate_steps(67,mode,0)}
    assert PROFILES[2].base=='P' and PROFILES[2].current=='TP' and PROFILES[3].base=='N'
def test_metadata_failure_has_zero_observations():
    r=json.loads((ROOT/'docs/research/data/shogi_promotion_cubes_20261005.json').read_text())
    assert not r['complete'] and r['worlds']==r['canonical_candidates']==r['enumerated']==0 and r['error']=='AttributeError: fingerprint'
