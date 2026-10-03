from fractions import Fraction
import hashlib
import json
from pathlib import Path

import pytest

from scripts.label_joint_capability_corpus import count_risks, run
from scripts.audit_secured_exchange_common_context import Budget


def test_exact_loss_gate_requires_both_baselines_and_signal():
    rows = [{'counts': {'P': 1}, 'actor_success_count': 1}]
    good = count_risks(rows, {'P': Fraction(1)}, Fraction(2))
    assert good['finite_gate_passed'] and good['risks'] == {'candidate': '0', 'zero': '1', 'constant': '1'}
    tied = count_risks(rows, {'P': Fraction(1, 2)}, Fraction(1, 2))
    assert not tied['finite_gate_passed']  # No improvement over frozen constant.
    zero = count_risks(rows, {'P': Fraction()}, Fraction())
    assert not zero['finite_gate_passed']
    degenerate = count_risks(rows, {'P': Fraction(1)}, Fraction(1))
    assert not degenerate['positive_baseline_risks'] and not degenerate['finite_gate_passed']
    with pytest.raises(ValueError, match='empty deployment'):
        count_risks([], {'P': Fraction()}, Fraction())


def test_zero_reference_gate_reproduces_and_never_reads_deployment(tmp_path, monkeypatch):
    import scripts.label_joint_capability_corpus as runner
    def forbidden(*args):
        raise AssertionError('zero-reference gate must not read validation labels')
    monkeypatch.setattr(runner, 'board_actor_labels', forbidden)
    reference_path = tmp_path / 'reference.json'
    result = run(reference_path)
    root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/joint_capability_labels_20261004.json').read_text())
    for key in recorded:
        if key != 'elapsed_seconds':
            assert result[key] == recorded[key]
    assert hashlib.sha256(reference_path.read_bytes()).hexdigest() == recorded['reference_sha256']
    reference = json.loads(reference_path.read_text())
    assert result['roots_labelled'] == 8 and result['materialized_transitions'] == 14998
    assert not result['finite_gate_passed'] and not result['all_deployment_labelled']
    for game in reference['games'].values():
        assert not game['nonzero_signal'] and set(game['coefficients'].values()) == {'0'}
        assert len(game['labels']) == 4
        assert all(label['actor_success_count'] == 0 for label in game['labels'])


def test_deadline_does_not_write_qualified_reference(tmp_path):
    path = tmp_path / 'reference.json'
    with pytest.raises(TimeoutError):
        run(path, Budget(seconds=-1))
    assert not path.exists()
