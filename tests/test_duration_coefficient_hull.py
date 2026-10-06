import hashlib
import json
from fractions import Fraction as F
from pathlib import Path
import pytest
from scripts.partial_contact_prior import PartialContactPrior
from scripts.duration_coefficient_hull import exact_vertices, affine_rank, realize_vertex_weights, universal_static_choice

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'docs/research/data'


def prior():
    r = json.loads((DATA/'chess_duration_decision_20261006.json').read_text())
    return PartialContactPrior(r['cumulative'], 249984, normalizer='Q')


def test_saved_rank_and_exact_inverse_duration_weights():
    r = json.loads((DATA/'duration_coefficient_hull_20261006.json').read_text())
    assert r['complete'] and r['source_hashes_unchanged']
    for path, digest in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest
    assert r['rank']['affine_rank'] == 4 and r['rank']['updates'] == 110
    assert r['action_vertex_terms'] == 54
    assert not r['static_choice']['universal_canonical'] and r['static_choice']['common_maximizers'] == []
    assert r['public_transitions'] == r['geometry_queries'] == r['source_queries'] == 0
    p = prior(); vertices = exact_vertices(p)
    assert affine_rank(vertices)['affine_rank'] == 4
    for weights in ({'1': 1}, {'1': F(1,3), '3': F(2,3)},
                    {'2': F(2,5), '7': F(1,5), 'infinity': F(2,5)}):
        masses = realize_vertex_weights(p, weights)
        actual = p.duration(masses)['normalized']
        for mode in p.cdf:
            expected = sum(v*vertices[h][mode] for h, v in weights.items())
            assert actual[mode] == (expected, expected)


def test_partial_h_unknown_corners_not_claimed_attainable():
    r = json.loads((DATA/'diagnostic_duration_order_20261006.json').read_text())
    p = PartialContactPrior(r['cumulative'], r['total'])
    with pytest.raises(ValueError): exact_vertices(p)


def test_universal_canonical_ties_and_interpolated_mixtures():
    vertices = {'short': {'R': F(1), 'N': F(1,4)}, 'long': {'R': F(1), 'N': F(3,4)}}
    stable = universal_static_choice(vertices, {'a': {'R': 1}, 'b': {'N': 1}})
    assert stable['universal_canonical'] and stable['selected'] == 'a'
    # Same maximizer b at both vertices, but a ties and wins canonically at one.
    mixed = universal_static_choice(vertices, {'a': {'R': 1}, 'b': {'N': 2}})
    assert not mixed['universal_canonical'] and mixed['common_maximizers'] == []
    tied = universal_static_choice(vertices, {'a': {'R': 1}, 'b': {'R': 1}})
    assert tied['selected'] == 'a' and tied['common_maximizers'] == ['a', 'b']


@pytest.mark.parametrize('weights', [{}, {'1': 2}, {'1': -1, '2': 2}, {'bad': 1}, {'1': 1.0}, {'1': True}])
def test_invalid_inverse_weights_rejected(weights):
    with pytest.raises(ValueError): realize_vertex_weights(prior(), weights)
