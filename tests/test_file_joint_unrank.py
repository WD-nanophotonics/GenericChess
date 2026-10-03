from itertools import product
import json
from pathlib import Path

import pytest

from scripts.audit_file_joint_unrank import JointSpace, audit
from scripts.audit_secured_exchange_common_context import Budget


def test_every_rank_matches_independent_physical_oracle_without_duplicates():
    eligibility = ((0,), (0, 1), (0, 1), (1,))
    pairs = [(a, b) for a in range(3) for b in range(1, 4) if a != b]
    space = JointSpace(eligibility, pairs, 2, (1, 1))
    oracle = set()
    for frame in product(pairs, repeat=2):
        free = [(file, r) for file in range(2) for r in range(4) if r not in frame[file]]
        for own in free:
            for enemy in free:
                if own == enemy or 0 not in eligibility[own[1]] or 1 not in eligibility[enemy[1]]:
                    continue
                oracle.add(tuple((frame[file], tuple(sorted((r, g) for f, r, g in
                                 ((*own, 0), (*enemy, 1)) if f == file))) for file in range(2)))
    drawn = [space.unrank(rank) for rank in range(space.total)]
    assert len(drawn) == len(set(drawn)) == len(oracle)
    assert set(drawn) == oracle
    assert space.unrank(0) in oracle and space.unrank(space.total - 1) in oracle
    for invalid in (-1, space.total, 0.5):
        with pytest.raises(ValueError):
            space.unrank(invalid)


def test_recorded_full_draw_and_abort():
    result = audit()
    recorded = json.loads((Path(__file__).resolve().parents[1] /
                           'docs/research/data/file_joint_unrank_20261004.json').read_text())
    for key in recorded:
        if key == 'elapsed_seconds':
            continue
        # JSON tuples are represented as arrays.
        assert json.loads(json.dumps(result[key])) == recorded[key]
    with pytest.raises(TimeoutError):
        audit(Budget(seconds=-1))
