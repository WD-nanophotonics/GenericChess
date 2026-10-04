from fractions import Fraction
import hashlib
import json
from pathlib import Path

from scripts.label_local_service_corpus import run

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_reference_precedes_complete_independent_validation(tmp_path):
    path = tmp_path / 'reference.json'
    result = run(path)
    recorded = json.loads((ROOT / 'docs/research/data/local_service_validation_20261004.json').read_text())
    for key in recorded:
        if key != 'elapsed_seconds':
            assert result[key] == recorded[key]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == result['reference_sha256']
    reference = json.loads(path.read_text())
    assert result['reference_complete'] and result['all_deployment_labelled']
    assert result['roots_labelled'] == 20 and result['materialized_transitions'] == 15465
    assert not result['finite_gate_passed']
    for game in reference['games'].values():
        assert game['nonzero_signal']
        assert all(0 <= Fraction(v) <= 1 for v in game['coefficients'].values())
    assert sum(row['opponent_drop_replies'] for row in result['games']['shogi']['labels']) > 0


def test_failed_baselines_and_exact_inventory_adjustment_identity():
    result = json.loads((ROOT / 'docs/research/data/local_service_validation_20261004.json').read_text())
    reference = json.loads((ROOT / 'docs/research/data/local_service_reference_20261004.json').read_text())
    for game, row in result['games'].items():
        ref = reference['games'][game]
        h = Fraction(ref['constant'])
        v = {t: Fraction(value) for t, value in ref['coefficients'].items()}
        # One real capture removes one ordinary own actor: h_candidate=H-v_t.
        adjustment = sum((2 * (h - label['actor_success_count']) * v[label['victim_type']]
                          - v[label['victim_type']]**2 for label in row['labels']), Fraction()) / len(row['labels'])
        risks = {t: Fraction(value) for t, value in row['risks'].items()}
        assert adjustment == risks['constant'] - risks['candidate']
        assert row['predictions'] == [str(h - v[label['victim_type']]) for label in row['labels']]
    chess = {t: Fraction(v) for t, v in result['games']['chess']['risks'].items()}
    shogi = {t: Fraction(v) for t, v in result['games']['shogi']['risks'].items()}
    assert chess['candidate'] > chess['zero']
    assert shogi['candidate'] > shogi['constant']
