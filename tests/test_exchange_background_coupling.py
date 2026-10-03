from collections import Counter
import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_exchange_background_coupling import audit, position_for
from scripts.audit_f24f_western_chess_perft import standard_engine
from scripts.audit_focal_survival_diagnostic import audit as dual_audit


@pytest.fixture(scope='module')
def background():
    return audit()


@pytest.fixture(scope='module')
def dual():
    return dual_audit()


def test_background_control_changes_objective_without_changing_inventory_or_focal_options(background):
    assert background['complete']
    assert all(r == {'same_focal_actions': True, 'shifted_score': 1, 'exposed_score': 0}
               for r in background['comparisons'].values())
    assert all(r['focal_survives_refutation'] and r['net_gain_after_refutation'] == 0
               for r in background['roots'] if r['background'] == 'exposed')
    assert background['materialized_transitions'] == 771
    assert background['enumeration_transitions'] == 765 and background['replayed_transitions'] == 6
    compiled, _ = standard_engine()
    inventories = [Counter((p.owner, p.base_type_id, p.current_type_id) for p in position_for(compiled, 'chess', x).board if p)
                   for x in (False, True)]
    assert inventories[0] == inventories[1]


def test_local_task_separates_background_tax_but_does_not_rescue_frozen_full_inventory(dual):
    physical = [r for r in dual['roots'] if r['population'] == 'frozen_full_inventory']
    controls = [r for r in dual['roots'] if r['population'] == 'background_control']
    assert len(physical) == 12 and len(controls) == 4
    assert all(r['net_score'] == r['local_score'] == 0 for r in physical)
    assert all(r['local_score'] == 1 for r in controls)
    assert all(r['net_score'] == (r['background'] == 'shifted') for r in controls)
    gains = [a for r in physical for a in r['actions'] if a['immediate_gain'] > 0]
    assert len(gains) == 16 and all(a['focal_loss_replies'] > 0 for a in gains)
    assert sum(a['local_ok_net_failure_replies'] for a in gains) == 186
    assert dual['materialized_transitions'] == 2407


def test_dual_tasks_use_every_same_successor_and_reproduce_published_sources(background, dual):
    root = Path(__file__).resolve().parents[1]
    for data, filename, program in [(background, 'exchange_background_coupling_20261003.json', 'audit_exchange_background_coupling.py'),
                                    (dual, 'focal_survival_diagnostic_20261003.json', 'audit_focal_survival_diagnostic.py')]:
        recorded = json.loads((root / 'docs/research/data' / filename).read_text())
        assert recorded['program_sha256'] == hashlib.sha256((root / 'scripts' / program).read_bytes()).hexdigest()
        for field in ('protocol_sha256', 'program_sha256', 'complete', 'roots', 'materialized_transitions'):
            assert data[field] == recorded[field]
    assert dual['materialized_transitions'] == sum(1 + action['reply_count']
        for row in dual['roots'] for action in row['actions'])
    assert dual['input_sha256'] == hashlib.sha256(
        (root / 'docs/research/data/physical_placement_sampling_20261003.json').read_bytes()).hexdigest()
