import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_physical_exchange_support import audit
from scripts.audit_secured_exchange_common_context import Budget


@pytest.fixture(scope='module')
def evidence():
    return audit()


def test_bounded_search_records_incompleteness_without_inventing_zero_expectation(evidence):
    assert not evidence['complete']
    assert evidence['games']['chess']['status'] == 'no_witness_within_cap'
    assert evidence['games']['chess']['scored_frames'] == 8
    assert evidence['games']['shogi']['status'] == 'incomplete'
    assert evidence['games']['shogi']['scored_frames'] == 5
    assert evidence['games']['shogi']['proposals'] == 128
    assert len(evidence['roots']) == 13
    assert all(root['success'] == 0 for root in evidence['roots'])
    assert evidence['materialized_transitions'] == 3098
    assert evidence['materialized_transitions'] == sum(
        1 + action['reply_count'] for root in evidence['roots'] for action in root['actions'])
    assert all(action['first_refutation'] is not None or action['reply_count'] == 0
               for root in evidence['roots'] for action in root['actions'])


def test_frozen_support_records_reproduce(evidence):
    root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/physical_exchange_support_20261003.json').read_text())
    assert recorded['program_sha256'] == hashlib.sha256(
        (root / 'scripts/audit_physical_exchange_support.py').read_bytes()).hexdigest()
    for key in ('protocol_sha256', 'sampler_sha256', 'program_sha256', 'complete', 'games', 'roots', 'materialized_transitions'):
        assert recorded[key] == evidence[key]


def test_no_proposal_and_materialization_exhaustion_are_not_support_decisions():
    empty = audit(proposal_limit=0)
    assert not empty['complete'] and not empty['roots']
    assert all(row['status'] == 'incomplete' for row in empty['games'].values())
    with pytest.raises(RuntimeError, match='transition cap'):
        audit(budget=Budget(transitions_limit=1))
