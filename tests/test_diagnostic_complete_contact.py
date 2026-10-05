import hashlib,json
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
from scripts.diagnostic_contact_coordinate_oracle import distance
ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/'docs/research/data'/name).read_text())
def test_full_mass_slabs_moments_and_predeclared_law_reversal():
    r=read('diagnostic_native_contact_mirrored_20261005.json')
    assert r['complete'] and len(r['completed_target_slabs'])==90
    assert r['charged_canonical_candidates']==3972 and r['cumulative_seconds']<15
    for row in r['rows']:
        mode=row['profile']['current'];counts=Counter()
        for slab in r['completed_target_slabs']:
            cell=next(x for x in slab['rows'] if x['profile']['current']==mode)
            assert sum(cell['counts'].values())==7832;counts.update(cell['counts'])
        assert counts.get('0',0)==row['unreachable']
        assert {k:v for k,v in counts.items() if k!='0'}==row['histogram']
        assert sum(counts.values())==704880
        for law in ('geometric_half','linear_mixture'):
            moment=lambda t:F(1,2**t) if law=='geometric_half' else F(2,(t+1)*(t+2))
            mean=sum((n*moment(int(t)) for t,n in row['histogram'].items()),F(0))/704880
            assert mean==F(row['means'][law])
    weights=r['normalized_by_law']
    assert F(weights['geometric_half']['weights']['C'])>F(weights['geometric_half']['weights']['S'])
    assert F(weights['linear_mixture']['weights']['C'])<F(weights['linear_mixture']['weights']['S'])
    assert not r['human_reference_imported'] and r['public_transitions']==r['source_queries']==0
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin

def test_independent_target_zero_and_full_shape_certificates_are_distinct():
    r=read('diagnostic_contact_independent_20261005.json')
    assert r['complete'] and sum(x['worlds'] for x in r['rows'])==46992
    assert all(x['target']==0 and x['match'] for x in r['rows'])
    assert r['analytic']['rook_histogram']=={'1':130800,'2':570240,'3':3840}
    assert r['analytic']['cannon_reachable']==106304 and r['analytic']['cannon_zero']==598576
    # A zero-valued target index is a real capture; C still needs an interior screen.
    assert distance('R',9,0,89)==1 and distance('C',2,0,1)==1
    assert distance('C',1,0,2)==4 and distance('C',9,0,89)==0
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin

def test_failed_serialization_preserves_zero_observations():
    r=read('diagnostic_native_contact_census_20261005.json')
    assert not r['complete'] and not r['rows'] and not r['completed_target_slabs']
    assert r['preprocessing']['canonical_candidates']==2791 and 'unsupported research record: set' in r['error']
