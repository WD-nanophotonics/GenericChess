"""Independent normalization even without a complete Horse histogram."""
import hashlib,json
from fractions import Fraction as F
from pathlib import Path
import pytest
from scripts.audit_diagnostic_moment_bounds import moment
ROOT=Path(__file__).resolve().parents[1]

def test_frozen_exact_normalizer_and_unresolved_orders():
    r=json.loads((ROOT/'docs/research/data/diagnostic_moment_bounds_20261006.json').read_text())
    assert r['complete'] and r['source_hashes_unchanged'] and r['law_reversal']
    assert r['horse_direct_edges']==508 and r['horse_direct_worlds']==44196
    assert r['distance_terms']==62<=100 and r['comparisons']==30<=64 and r['seconds']<15
    assert r['geometry_queries']==r['source_queries']==r['public_transitions']==r['runtime_pushes']==0
    for row in r['rows']:
        means={k:F(v) for k,v in row['exact_means'].items()};lo,hi=map(F,row['horse_interval'])
        assert lo==F(44196,704880)*moment(row['law'],1)
        assert hi==lo+F(704880-44196,704880)*moment(row['law'],2)
        assert row['rook_normalization_qualified'] and all(row['rook_strict_max_checks'].values())
        assert means['R']>hi>=lo and all(means['R']>v for k,v in means.items() if k!='R')
        assert all(F(v)==means[k]/means['R'] for k,v in row['normalized_exact'].items())
    assert r['rows'][0]['horse_above_exact']['S']
    assert not r['rows'][1]['horse_above_exact']['S']  # Bound is insufficient; no inferred rank.
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin

@pytest.mark.parametrize('law,t',[('chosen_fit',1),('geometric_half',True),('linear_mixture',0),('linear_mixture',1.0)])
def test_new_laws_and_invalid_distance_rejected(law,t):
    with pytest.raises(ValueError):moment(law,t)
