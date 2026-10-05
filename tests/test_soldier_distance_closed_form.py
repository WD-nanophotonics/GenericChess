"""Frozen independent controls, not repeated BFS production."""
import hashlib,json
from pathlib import Path
import pytest
from scripts.soldier_distance_closed_form import histogram,pair_counts
ROOT=Path(__file__).resolve().parents[1]

def test_frozen_small_controls_and_full_mass():
    raw=json.loads((ROOT/'docs/research/data/soldier_distance_closed_form_20261006.json').read_text())
    assert raw['complete'] and raw['saved_full_match'] and raw['source_hashes_unchanged']
    assert raw['worlds']==684 and raw['expanded_nodes']==2109<=5000 and raw['seconds']<15
    for row in raw['rows']:
        assert row['complete']
        for pair in row['pairs']:
            s,d=pair['source'],pair['target'];w=row['width']
            analytic=pair_counts(w,row['height'],row['river'],s//w,d//w,abs(s%w-d%w))
            assert {t:n for t,n in analytic.items() if n}=={int(t):n for t,n in pair['histogram'].items()}
    full=histogram(9,10,5)
    assert full['histogram']=={int(t):n for t,n in raw['full_analytic']['histogram'].items()}
    assert full['unreachable']==423600 and full['total']==704880 and full['strata']==890
    for path,pin in raw['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin

def test_forced_prefix_detour_and_disjoint_elbows():
    assert pair_counts(3,4,1,0,3,0)=={3:8,0:1,5:1}
    assert pair_counts(3,4,1,1,3,0)=={2:9,4:1}
    assert pair_counts(3,4,1,0,1,2)=={3:8,0:2}
    assert pair_counts(3,4,1,1,3,2)=={4:10}
    assert pair_counts(3,4,1,2,2,2)=={2:9,0:1}
    assert pair_counts(3,4,1,3,0,0)=={0:10}

@pytest.mark.parametrize('shape',[(True,4,1),(3,4,True),(3,4,0),(3,4,4),(1,4,1),(3.0,4,1)])
def test_invalid_shapes_not_admitted(shape):
    with pytest.raises(ValueError):histogram(*shape)

def test_partition_retains_all_mass_without_human_or_rule_fit():
    for w,h,r in ((2,2,1),(3,3,1),(3,3,2),(9,10,5)):
        raw=histogram(w,h,r)
        assert sum(raw['histogram'].values())+raw['unreachable']==raw['total']
        assert raw['unreachable']>=0 and all(n>0 for n in raw['histogram'].values())
    with pytest.raises(ValueError):pair_counts(3,4,1,1,1,0)
    with pytest.raises(ValueError):pair_counts(3,4,1,True,1,1)
