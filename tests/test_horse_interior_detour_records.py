import hashlib,json
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def record():return json.loads((ROOT/'docs/research/data/horse_interior_detour_20261006.json').read_text())


def test_frozen_subset_and_original_pins():
    r=record();assert r['complete'] and r['source_hashes_unchanged']
    for p,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin
    assert r['new_terms']==34 and r['cumulative_analytic_terms']==4994
    assert r['forward_nodes']==r['compiled_queries']==r['public_transitions']==0
    assert r['cumulative_forward_nodes']==1579 and r['seconds']<15


def test_saved_routes_cover_directed_leg_obstructions_without_center():
    routes=record()['routes'];assert len(routes)==8
    assert len({tuple(x['path'][0]+x['path'][-1]) for x in routes})==8
    for row in routes:
        assert len(row['path'])==4 and len(row['legs'])==3
        for p in row['path']+row['legs']:
            assert p!=[0,0] and max(map(abs,p))<=2
        for a,b,l in zip(row['path'],row['path'][1:],row['legs']):
            dx,dy=b[0]-a[0],b[1]-a[1]
            assert sorted((abs(dx),abs(dy)))==[1,2]
            expected=[a[0]+(1 if dx>0 else -1),a[1]] if abs(dx)==2 else [a[0],a[1]+(1 if dy>0 else -1)]
            assert l==expected


def test_conditional_count_and_loose_bound_do_not_imply_full_census():
    r=record();assert r['close_displacement_sums']==[19,24]
    assert r['ordered_distant_pairs']==30**2-19*24==444
    assert r['qualified_worlds']==444*88==39072
    assert Fraction(r['qualified_mass'])==Fraction(39072,704880)
    assert r['sufficient_horse_contact_bound']==r['ordinary_path_bound']+2*r['removed_leg_edge_bound']==120
    assert 'remaining target/blocker pairs' in r['not_proved']
