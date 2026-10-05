"""Frozen independent controls; do not rerun the bounded BFS producer."""
import hashlib,json
from pathlib import Path
import pytest
from scripts.cannon_distance_closed_form import histogram

ROOT=Path(__file__).resolve().parents[1]

def test_full_and_small_independent_counts_and_budget():
    raw=json.loads((ROOT/'docs/research/data/cannon_distance_closed_form_20261006.json').read_text())
    assert raw['complete'] and raw['saved_full_match'] and raw['source_hashes_unchanged']
    assert raw['worlds']==840 and raw['expanded_nodes']==4910<=5000 and raw['seconds']<15
    for row in raw['rows']:
        expected=histogram(row['width'],row['height'])
        assert expected['histogram']=={int(t):n for t,n in row['histogram'].items()}
        assert expected['unreachable']==row['unreachable'] and expected['total']==row['worlds']
    full=histogram(9,10)
    assert full['histogram']=={1:3840,2:32400,3:64800,4:5264}
    assert full['unreachable']==598576 and full['total']==704880
    for path,pin in raw['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin

def test_axis_symmetry_and_all_mass_retained():
    for width,height in ((2,2),(2,4),(3,3),(9,10),(10,9)):
        r=histogram(width,height)
        assert r==histogram(height,width)
        assert all(n>=0 for n in r['histogram'].values()) and r['unreachable']>=0
        assert sum(r['histogram'].values())+r['unreachable']==r['total']
    assert histogram(2,2)['unreachable']==24

@pytest.mark.parametrize('shape',[(1,9),(9,1),(True,9),(3.0,3),(-1,3)])
def test_line_and_noninteger_shapes_not_silently_admitted(shape):
    with pytest.raises(ValueError):histogram(*shape)
