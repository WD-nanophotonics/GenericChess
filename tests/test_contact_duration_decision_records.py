import hashlib
import json
from fractions import Fraction as F
from pathlib import Path
from scripts.partial_contact_prior import PartialContactPrior

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'docs/research/data'


def test_cold_process_records_include_external_startup_not_hidden_free_cost():
    r = json.loads((DATA/'partial_contact_cold_20261006.json').read_text())
    assert r['complete'] and r['source_hashes_unchanged'] and len(r['rows']) == 3
    for path, digest in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest
    assert r['public_transitions'] == r['source_queries'] == r['geometry_queries'] == 0
    for row in r['rows']:
        assert row['exit_code'] == 0 and row['stderr'] == ''
        assert row['measured'] == json.loads(row['stdout'])
        assert row['external_seconds'] >= row['measured']['whole_child_seconds']
        assert row['startup_and_parent_overhead_seconds'] > 0
    assert r['seconds'] < 15


def test_chess_duration_cdf_totals_and_all_provenance_pins():
    r = json.loads((DATA/'chess_duration_decision_20261006.json').read_text())
    assert r['complete'] and r['source_hashes_unchanged'] and r['arithmetic_terms'] == 129
    for path, digest in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest
    prior = PartialContactPrior(r['cumulative'], 249984, normalizer='Q')
    assert all(prior.cdf['Q'][h][0] >= row[1] for table in prior.cdf.values() for h, row in table.items())
    assert r['Q_minus_R']['weak_order_proved'] and not r['Q_minus_R']['strict_order_proved']
    assert not r['N_minus_B']['weak_order_proved']
    assert r['public_transitions'] == r['source_queries'] == r['geometry_queries'] == 0


def test_exact_two_three_threshold_and_true_choice_reversal():
    r = json.loads((DATA/'chess_duration_decision_20261006.json').read_text())
    x = F(r['two_three_boundary']['mass_at_three_for_equality'])
    assert x == F(4057, 11526)
    assert (1-x)*r['two_three_boundary']['negative_two'] + x*r['two_three_boundary']['positive_three'] == 0
    prior = PartialContactPrior(r['cumulative'], 249984, normalizer='Q')
    at = prior.duration({'2': 1-x, '3': x})['normalized']
    assert at['N'] == at['B']
    for h, policy in r['policies'].items():
        assert len(policy['tie_set']) == 1
        if h in ('1', '2'): assert policy['selected'].endswith('e4-d3')
        else: assert policy['selected'].endswith('e4-e3')
        scores = {k: F(v) for k, v in policy['scores'].items()}
        assert policy['selected'] == max(scores, key=scores.get)
