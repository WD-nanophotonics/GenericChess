from fractions import Fraction
import hashlib
from itertools import product
import json
from pathlib import Path

from scripts.audit_dead_placement_conditioning import audit, completion_count


def test_coefficient_matches_independent_assignment_oracle():
    # Enumerate all physical assignments, including the empty symbol.
    cells = ((0,), (0, 1), (1,), (0, 1))
    assignments = list(product((-1, 0, 1), repeat=len(cells)))
    valid = [row for row in assignments if row.count(0) == row.count(1) == 1
             and all(group == -1 or group in cells[index] for index, group in enumerate(row))]
    assert completion_count(cells, (1, 1)) == len(valid) == 7
    assert completion_count(((0,),), (1, 1)) == 0


def test_fixed_frame_redraw_has_wrong_joint_conditioned_marginal():
    # Equal parent frames A/B have respectively one/three valid child assignments.
    counts = [completion_count(cells, (1,)) for cells in [((0,), (), ()), ((0,), (0,), (0,))]]
    assert counts == [1, 3]
    conditioned = [Fraction(count, sum(counts)) for count in counts]
    assert conditioned == [Fraction(1, 4), Fraction(3, 4)]
    assert conditioned != [Fraction(1, 2)] * 2


def test_production_counts_vary_and_reproduce_frozen_inputs():
    result = audit(); root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/dead_placement_conditioning_20261003.json').read_text())
    assert result['complete'] and result['varying_completion_counts']
    assert len(result['rows']) == 6
    assert all(0 < Fraction(row['nondead_probability']) < 1 for row in result['rows'])
    for key in ('protocol_sha256', 'program_sha256', 'input_sha256', 'complete', 'rows', 'varying_completion_counts'):
        assert result[key] == recorded[key]
    assert result['program_sha256'] == hashlib.sha256(
        (root / 'scripts/audit_dead_placement_conditioning.py').read_bytes()).hexdigest()
