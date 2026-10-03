from fractions import Fraction
import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_exchange_additivity_target import audit, finite_targets
from scripts.audit_secured_exchange_common_context import Budget


@pytest.fixture(scope='module')
def result():
    return audit()


def test_two_successful_actors_share_one_victim_and_one_turn_gain(result):
    assert result['complete'] and result['joint_success'] == 1 and result['successful_actor_count'] == 2
    assert len(result['actors']) == 2
    assert {tuple(row['source']) for row in result['actors']} == {(3, 3), (0, 0)}
    assert all(row['success'] == 1 and row['selected_capture']['success'] for row in result['actors'])
    assert all(row['victim'] == [1, 'P', [0, 3]] and row['capture_terminal'] == 'ongoing' for row in result['actors'])
    assert all(len(row['replies']) == 1 and row['replies'][0]['custody_delta'] == 1
               and row['replies'][0]['terminal'] == 'ongoing' for row in result['actors'])
    assert result['materialized_transitions'] == 219 and result['replayed_transitions'] == 4
    assert result['materialized_transitions'] == result['replayed_transitions'] + sum(
        1 + action['reply_count'] for actor in result['actors'] for action in actor['actions'])


def test_equal_marginals_do_not_determine_union_but_always_add_to_count(result):
    overlap, disjoint = [result['finite_laws'][key] for key in ('overlap', 'disjoint')]
    assert overlap['A'] == overlap['B'] == disjoint['A'] == disjoint['B'] == '1/2'
    assert overlap['union'] == '1/2' and disjoint['union'] == '1'
    assert overlap['successful_actor_count'] == disjoint['successful_actor_count'] == '1'
    assert overlap['A_union_increment_given_B'] == '0' and disjoint['A_union_increment_given_B'] == '1/2'
    for law in (overlap, disjoint):
        assert Fraction(law['successful_actor_count']) == Fraction(law['A']) + Fraction(law['B'])
    with pytest.raises(ValueError, match='normalized'):
        finite_targets(((Fraction(1, 2), (True, False)),))
    with pytest.raises(ValueError, match='binary'):
        finite_targets(((Fraction(1), (1, True)),))


def test_frozen_inputs_actions_and_source_reproduce(result):
    root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/exchange_additivity_target_20261004.json').read_text())
    for key in ('protocol_sha256', 'program_sha256', 'input_sha256', 'actors', 'finite_laws', 'materialized_transitions'):
        assert recorded[key] == result[key]
    assert result['program_sha256'] == hashlib.sha256((root / 'scripts/audit_exchange_additivity_target.py').read_bytes()).hexdigest()
    frozen = json.loads((root / 'docs/research/data/nonterminal_physical_support_20261003.json').read_text())
    assert result['actors'][0]['actions'] == frozen['roots'][0]['root']['actions']


def test_abort_never_qualifies_an_additivity_statement():
    with pytest.raises(RuntimeError, match='transition cap'):
        audit(Budget(transitions_limit=1))
