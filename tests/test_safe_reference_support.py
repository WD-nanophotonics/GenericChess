import json
from pathlib import Path

import pytest

from scripts.audit_safe_reference_support import audit
from scripts.audit_secured_exchange_common_context import Budget


def test_public_witnesses_reproduce_without_reading_task_labels():
    result = audit()
    recorded = json.loads((Path(__file__).resolve().parents[1] /
                           'docs/research/data/safe_reference_support_20261004.json').read_text())
    for key in recorded:
        if key != 'elapsed_seconds':
            assert result[key] == recorded[key]
    assert result['materialized_transitions'] == len(result['rows']) == 12
    assert all(row['safe_parent_excluded'] and row['ongoing_capture_support'] for row in result['rows'])


def test_support_intersection_is_empty_even_with_nonuniform_weights():
    # Safety allows no capture; each victim event requires one ongoing capture.
    contexts = ({'P'}, set(), {'N', 'P'}, {'N'})
    weights = (2, 7, 3, 11)
    safe = {i for i, captures in enumerate(contexts) if not captures}
    assert sum(weights[i] for i in safe) > 0
    for kind in ('P', 'N'):
        event = {i for i, captures in enumerate(contexts) if kind in captures}
        assert not safe.intersection(event)
        assert sum(weights[i] for i in safe.intersection(event)) == 0


def test_incomplete_replay_is_not_qualified():
    with pytest.raises(RuntimeError, match='transition cap'):
        audit(Budget(seconds=10, transitions_limit=1))
    with pytest.raises(TimeoutError):
        audit(Budget(seconds=-1))
