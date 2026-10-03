from fractions import Fraction as F
import json
from pathlib import Path

import pytest

from scripts.audit_actual_actor_population import Actor, audit, summarize


def test_fixed_inventory_uses_actual_source_law():
    row = audit()['fixed_inventory']
    assert row['mean_actor_success_count'] == row['pooled_count_prediction_mean'] == '4/3'
    assert row['pooled_count_squared_error'] == '2/9'
    for kind in ('A', 'B'):
        item = row['types'][kind]
        assert item['pooled_mean'] == item['context_then_actor_mean'] == '2/3'
        weighted = sum((F(s['probability']) * F(s['mean_success']) for s in item['sources'].values()), F())
        uniform = sum((F(s['mean_success']) for s in item['sources'].values()), F()) / len(item['sources'])
        assert weighted == F(2, 3) and uniform == F(1, 2)


def test_variable_inventory_distinguishes_sampling_order_and_prediction():
    row = audit()['variable_inventory']
    assert row['types']['A']['pooled_mean'] == '1/3'
    assert row['types']['B']['pooled_mean'] == '1/2'
    assert row['types']['A']['context_then_actor_mean'] == '3/7'
    assert row['types']['B']['context_then_actor_mean'] == '2/5'
    assert row['mean_actor_success_count'] == row['pooled_count_prediction_mean'] == '1'
    assert row['context_then_actor_prediction_mean'] == '73/70'
    assert row['pooled_count_squared_error'] == '1/36'


def test_malformed_or_incomplete_evidence_never_certifies_population():
    good = (Actor('A', 'left', True),)
    cases = [(), ((F(-1), good), (F(2), good)), ((F(1, 2), good),),
             ((F(1), good + good),), ((F(1), (Actor('A', 'left', None),)),),
             ((F(1), good), (F(0), (Actor('B', 'right', None),)))]
    for contexts in cases:
        with pytest.raises(ValueError):
            summarize(contexts)


def test_zero_mass_type_is_not_silently_normalized():
    with pytest.raises(ValueError, match='positive mass'):
        summarize(((F(1), (Actor('A', 'left', True),)),
                   (F(0), (Actor('B', 'right', True),))))


def test_recorded_exact_certificate_reproduces():
    root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/actual_actor_population_20261004.json').read_text())
    assert recorded == audit()
