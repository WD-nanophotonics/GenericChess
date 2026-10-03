from fractions import Fraction
import json
from math import factorial
from pathlib import Path

import pytest

from scripts.audit_reverse_placement_efficiency import audit, unrestricted_layouts
from scripts.audit_secured_exchange_common_context import Budget


def test_unrestricted_physical_count_has_no_token_labelling_factor():
    for cells in (8, 63, 81):
        assert unrestricted_layouts(cells) == factorial(cells) // (factorial(cells - 8) * 2**4)


def test_shared_normalizer_identity_with_unequal_compatibility_rows():
    # Three Pawn frames, four valid L/N frames; one L/N frame has zero support.
    pairs = {(0, 0), (0, 1), (1, 1), (2, 2)}
    m, u, w = 3, 2, 4
    old_weight = Fraction(1, m * u)
    reverse_weights = {}
    for a in range(w):
        compatible = [p for p in range(m) if (a, p) in pairs]
        for p in compatible:
            reverse_weights[a, p] = Fraction(1, w) * Fraction(len(compatible), m) / len(compatible)
    assert set(reverse_weights) == pairs
    assert set(reverse_weights.values()) == {Fraction(1, w * m)}
    for predicate in (pairs, {(0, 1), (2, 2)}):
        assert sum(reverse_weights[pair] for pair in predicate) / (len(predicate) * old_weight) == Fraction(u, w)
    assert {pair: weight / sum(reverse_weights.values()) for pair, weight in reverse_weights.items()} == {
        pair: Fraction(1, len(pairs)) for pair in pairs}


def test_exact_certificate_and_abort_gate():
    result = audit()
    recorded = json.loads((Path(__file__).resolve().parents[1] /
                           'docs/research/data/reverse_placement_efficiency_20261004.json').read_text())
    for key in recorded:
        if key != 'elapsed_seconds':
            assert result[key] == recorded[key]
    assert result['W81'] == 18255611345850
    assert not result['reverse_improves_raw_acceptance']
    with pytest.raises(TimeoutError):
        audit(Budget(seconds=-1))
