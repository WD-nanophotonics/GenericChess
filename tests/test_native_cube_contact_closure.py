import hashlib,json
from pathlib import Path
import pytest
from scripts.native_cube_contact_qualified import QualifiedNativeCubeKernel
from scripts.shared_contact_prefix import Profile
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
ROOT=Path(__file__).resolve().parents[1]
def test_prospective_worldwise_cube_closure_and_full_virtual_lists():
    r=json.loads((ROOT/'docs/research/data/native_cube_contact_qualified_20261005.json').read_text())
    assert r['complete'] and len(r['rows'])==6 and len(r['controls'])==12
    assert r['canonical_candidates']==512 and r['enumerated']==24 and r['cumulative_seconds']<15
    for row in r['rows']:
        assert row['worlds']==3360 and row['first_mismatch'] is None
        assert row['ordered_cube_sha256']==row['ordered_coordinate_sha256']
        assert sum(row['census']['histogram'].values())+row['census']['unreachable']==3360
    assert all(row['actual']==row['coordinate'] for row in r['controls'])
    assert r['renamed_census']==r['rows'][0]['census'] and r['public_transitions']==r['source_queries']==0
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin

def test_native_admission_does_not_silently_drop_promotion():
    c=compile_semantic_ruleset(build_standard_shogi_ruleset())
    with pytest.raises(ValueError,match='native nonpromotable'):
        QualifiedNativeCubeKernel(c,(Profile('P','P'),))

def test_original_missing_closure_failure_remains_unobserved():
    r=json.loads((ROOT/'docs/research/data/native_cube_contact_closure_20261005.json').read_text())
    assert not r['complete'] and not r['rows'] and r['canonical_candidates']==96 and r['enumerated']==0
    assert 'closure' in r['error']
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
