import hashlib
import json
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import pytest
from scripts.partial_contact_prior import PartialContactPrior
from scripts.audit_partial_contact_prior import endpoint_masses

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'docs/research/data'


def source():
    return json.loads((DATA/'diagnostic_duration_order_20261006.json').read_text())


def prior():
    s = source(); return PartialContactPrior(s['cumulative'], s['total'])


def test_frozen_constructor_inputs_and_budget():
    r = json.loads((DATA/'partial_contact_prior_20261006.json').read_text())
    assert r['complete'] and r['source_hashes_unchanged']
    for path, digest in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest
    assert r['public_transitions'] == r['geometry_queries'] == r['source_queries'] == 0
    assert r['arithmetic_terms'] == 144 and r['benchmark_horizon_terms_per_kind'] == 9000
    assert r['seconds'] < 15
    assert r['differences']['H_minus_C_E']['strict_order_proved']
    assert not r['differences']['H_minus_S']['weak_order_proved']


def test_endpoint_h_intervals_match_independent_partial_moments():
    p = prior(); h = json.loads((DATA/'horse_zero_obstruction_20261006.json').read_text())
    for row in h['moments']:
        a = p.duration(endpoint_masses(row['law']))
        assert a['raw']['H'] == tuple(F(v) for v in row['horse_interval'])
        assert a['normalized']['R'] == (F(1), F(1))
        assert all(0 <= lo <= hi <= 1 for lo, hi in a['normalized'].values())
        assert a['normalized']['H'][0] != a['normalized']['H'][1]


def test_every_atom_and_convex_ratio_coupling():
    p = prior(); delta = {'H': 1, 'C': -1, 'E': -1}
    universal = p.difference(delta)
    for h in p.horizons:
        a = p.duration({h: 1})
        actual = tuple(a['normalized']['H'][i]-a['normalized']['C'][i]-a['normalized']['E'][i] for i in (0, 1))
        assert actual == universal['horizon_bounds'][h]
    # Normalized differences use R-weighted atoms, not the duration masses.
    masses = {'0': F(1, 7), '1': F(2, 7), '3': F(1, 7), 'infinity': F(3, 7)}
    a = p.duration(masses)
    denom = a['normalizer_raw']*p.total
    weights = {h: v*p.cdf['R'][h][0]/denom for h, v in masses.items() if h != '0'}
    assert sum(weights.values()) == 1
    for i in (0, 1):
        ratio = sum(v*universal['horizon_bounds'][h][i] for h, v in weights.items())
        assert ratio == a['normalized']['H'][i]-a['normalized']['C'][i]-a['normalized']['E'][i]
        assert universal['lower'] <= ratio <= universal['upper']


def test_common_epistemic_h_cancels_instead_of_double_penalty():
    p = prior(); a = p.duration(endpoint_masses('geometric_half'))['normalized']
    independent_boxes = a['R'][0]+10*a['H'][0] - (a['C'][1]+10*a['H'][1])
    assert independent_boxes < 0
    coupled = p.difference({'R': 1, 'C': -1})
    assert coupled['lower'] > 0  # identical10H in both portfolios cancels


def test_c_s_reversal_does_not_get_false_universal_order():
    p = prior()
    short = p.duration({'1': 1})['normalized']
    medium = p.duration({'2': 1})['normalized']
    assert short['C'][0] < short['S'][0] and medium['C'][0] > medium['S'][0]
    r = p.difference({'C': 1, 'S': -1})
    assert r['lower'] < 0 < r['upper'] and not r['weak_order_proved']
    assert p.difference({})['lower'] == p.difference({})['upper'] == 0


@pytest.mark.parametrize('masses', [{}, {'0': 1}, {'1': 0.5, '0': 0.5},
                                   {'1': True}, {'1': -1, '2': 2}, {'18': 1}, {'1': 2}])
def test_bad_duration_rejected_without_float_or_tail_fallback(masses):
    with pytest.raises(ValueError): prior().duration(masses)


@pytest.mark.parametrize('delta', [{'K': 1}, {'H': 0.5}, {'H': True}])
def test_bad_inventory_delta_rejected(delta):
    with pytest.raises(ValueError): prior().difference(delta)


def test_invalid_cdf_and_input_aliases():
    s = source(); c = deepcopy(s['cumulative']); p = PartialContactPrior(c, s['total'])
    c['R']['1'][0] = 0
    assert p.cdf['R']['1'][0] == 130800  # copied qualified input
    with pytest.raises(ValueError): PartialContactPrior(c, s['total'])
    c = deepcopy(s['cumulative']); c['H']['3'] = [1, 2]
    with pytest.raises(ValueError): PartialContactPrior(c, s['total'])
    c = deepcopy(s['cumulative']); c['H']['infinity'] = [704880, 704881]
    with pytest.raises(ValueError): PartialContactPrior(c, s['total'])
    c = deepcopy(s['cumulative']); del c['A']['1']
    with pytest.raises(ValueError): PartialContactPrior(c, s['total'])
