from itertools import product
import json
from pathlib import Path

import pytest

from scripts.audit_file_joint_count import audit, combine_files, file_terms
from scripts.audit_secured_exchange_common_context import Budget


def test_joint_polynomial_matches_exhaustive_physical_space_and_pawn_weights():
    eligibility = ((0,), (0, 1), (0, 1), (1,))
    pairs = [(a, b) for a in range(3) for b in range(1, 4) if a != b]
    quotas = (1, 1)
    terms = file_terms(eligibility, pairs, quotas)
    _, tables = combine_files(terms, 2, quotas)
    counts = []
    for frame in product(pairs, repeat=2):
        free = [(file, rank) for file in range(2) for rank in range(4) if rank not in frame[file]]
        valid = [(own, enemy) for own in free for enemy in free if own != enemy
                 and 0 in eligibility[own[1]] and 1 in eligibility[enemy[1]]]
        counts.append(len(valid))
    assert tables[-1][quotas] == sum(counts)
    assert len(set(counts)) > 1  # Equal Pawn-frame weights would be biased.
    assert tables[0] == {(0, 0): 1}


def test_full_count_certificate_and_abort():
    result = audit()
    recorded = json.loads((Path(__file__).resolve().parents[1] /
                           'docs/research/data/file_joint_count_20261004.json').read_text())
    for key in recorded:
        if key != 'elapsed_seconds':
            assert result[key] == recorded[key]
    assert result['maximum_table_states'] <= 81
    with pytest.raises(TimeoutError):
        audit(Budget(seconds=-1))


def test_overlapping_pawn_pair_rejected():
    with pytest.raises(ValueError):
        file_terms(((0,), (1,)), [(0, 0)], (1, 1))
