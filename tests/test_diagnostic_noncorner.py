import hashlib,json
from pathlib import Path
from scripts.diagnostic_contact_coordinate_oracle import distance
ROOT=Path(__file__).resolve().parents[1]
def test_selected_whole_mode_slabs_have_independent_ordered_and_mass_checks():
    r=json.loads((ROOT/'docs/research/data/diagnostic_noncorner_20261005.json').read_text())
    assert r['complete'] and len(r['rows'])==18 and r['new_worlds']==140976 and r['seconds']<15
    assert {(x['target'],x['mode']) for x in r['rows']}=={(d,t) for d in (13,40,60) for t in 'ACEHRS'}
    assert r['canonical_candidates']==r['public_transitions']==r['source_queries']==r['enumerated']==0
    for row in r['rows']:
        assert row['worlds']==sum(row['counts'].values())==7832 and row['first_mismatch'] is None
        assert row['cube_sha256']==row['coordinate_sha256'] and row['counts']==row['saved_counts']
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
def test_noncorner_zone_and_direction_are_not_corner_equivalence():
    assert distance('A',3,13,80)==1 and distance('A',3,40,80)==0
    assert distance('E',0,60,80)==0 and distance('S',51,60,0)==1
    assert distance('S',60,51,0)==0
