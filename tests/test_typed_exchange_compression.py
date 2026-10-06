import hashlib
import itertools
import json
from pathlib import Path
import pytest
from scripts.typed_exchange_order import dominates, typed_set_order
from scripts.typed_exchange_compression import compress, compressed_order

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'docs/research/data'
Q0 = {'kind': 'quiet', 'vector': [0, 0, 0, 0, 0]}
Q1 = {'kind': 'quiet', 'vector': [1, 0, 0, 0, 0]}
DRAW = {'kind': 'source_terminal', 'source_terminal': {'value': 0, 'winner': None}}


def test_preserved_naive_fault_and_completed_compressed_provenance():
    old = json.loads((DATA/'typed_exchange_order_20261006.json').read_text())
    assert not old['complete'] and old['endpoint_pair_checks'] == 816
    assert old['error'] == 'ValueError: comparison budget exceeded'
    new = json.loads((DATA/'typed_exchange_compression_20261006.json').read_text())
    assert new['complete'] and new['source_hashes_unchanged'] and new['budget'] == {'checks': 80, 'remaining': 432}
    for raw in (old, new):
        for path, digest in raw['source_sha256'].items():
            assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest
    for key, comparison in new['comparisons'].items():
        f = comparison['forward']; b = comparison['reverse']
        assert f['complete'] and b['complete']
        assert f['weak_order_proved'] == key.endswith('/all_ties')
        assert not b['weak_order_proved']
        if f['weak_order_proved']: assert f['candidate_paths_subset_of_baseline']


def test_all_paths_and_source_class_recover_from_compression():
    raw = json.loads((DATA/'chess_adjudicated_exchange_20261006.json').read_text())
    result = compress(raw['leaves'])
    assert len(result['path_to_signature']) == 27
    assert set(p for paths in result['groups'].values() for p in paths) == set(raw['leaves'])
    assert len(result['representatives']) == 4
    for path, signature in result['path_to_signature'].items():
        assert path in result['groups'][signature]
        assert raw['leaves'][path]['kind'] == result['representatives'][signature]['kind']
        assert dominates(raw['leaves'][path], result['representatives'][signature])
        assert dominates(result['representatives'][signature], raw['leaves'][path])


def test_small_disjoint_poset_all_sets_against_every_isotone_boolean_utility():
    rows = [Q0, Q1, DRAW]
    sets = [{str(i): rows[i] for i in range(3) if mask & (1 << i)} for mask in range(1, 8)]
    utilities = [(a, b, d) for a, b, d in itertools.product((0, 1), repeat=3) if a <= b]
    for x in sets:
        for y in sets:
            direct = typed_set_order(x, y)
            compressed = compressed_order(x, y, {'remaining': 512, 'checks': 0})
            true = all(min(u[int(p)] for p in x) >= min(u[int(p)] for p in y) for u in utilities)
            assert direct['weak_order_proved'] == compressed['weak_order_proved'] == true
            assert not compressed['strict_improvement_proved']


def test_budget_is_checked_before_pairs_without_partial_proof():
    budget = {'remaining': 1, 'checks': 0}
    result = compressed_order({'x': Q1}, {'y': Q0, 'z': DRAW}, budget)
    assert not result['complete'] and result['weak_order_proved'] is None
    assert budget == {'remaining': 0, 'checks': 1}
    assert 'witnesses' not in result


@pytest.mark.parametrize('bad', [
    {'kind': 'quiet', 'vector': [0]},
    {'kind': 'quiet', 'vector': [0]*5, 'source_terminal': {'value': 0}},
    {'kind': 'source_terminal', 'vector': [0]*5, 'source_terminal': {'value': 0}},
    {'kind': 'source_terminal', 'source_terminal': {'value': True}},
    {'kind': 'source_terminal', 'source_terminal': {'value': 1, 'winner': None}},
    {'kind': 'ongoing'}])
def test_malformed_class_or_goal_never_gets_a_certificate(bad):
    with pytest.raises(ValueError): compress({'bad': bad})
