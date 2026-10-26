"""Adversarial semantic/denominator controls; synthetic returns are not trials."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest
from scripts.leaper_truth_compatibility import bind_context, digest
from scripts.research_record import record_value
from scripts.score_published_leaper_choices import (
    literal_contexts, qualify_returns, summarize_comparison, analyze, load_source,
)


@pytest.fixture(scope='module')
def contract_source():
    raw = json.loads(gzip.decompress(Path('docs/research/data/leaper_h6_initial_truth_20261023/inputs.json.gz').read_bytes()))
    family = next(f for f in raw['families'] if f.get('rule') is not None)
    row = next(r for r in raw['rows'] if r['family'] == family['family'])
    context = bind_context(family['rule'], row['full_record'])
    actions = list(context.session.legal_actions())
    assert len(actions) >= 2
    packet = {'rows': [dict(id='synthetic-control', RuleSet=family['rule'], record=row['full_record'],
                           root=record_value(context.session.state), fingerprint=context.identity['ruleset_fingerprint'],
                           prefix_length=context.identity['ply'], terminal=False, status='PREPARED',
                           legal_actions=[record_value(a) for a in actions], n=3, family='synthetic')]}
    # Producer schedule: depth1 baseline then scan_hint; depth4 reversed.
    rows = []
    for slot, (depth, arm) in enumerate([(1, 'baseline'), (1, 'scan_hint'), (4, 'scan_hint'), (4, 'baseline')]):
        action = record_value(actions[0])
        rows.append(dict(case_id='synthetic-control', requested_depth=depth, arm=arm, slot=slot,
                         input_fingerprint=context.identity['ruleset_fingerprint'], status='RETURNED',
                         decision=dict(action=action, choice_kind='ACTION', declaration=None,
                                       principal_variation=[action], completed_depth=depth,
                                       termination_reason='completed_depth', score=1000),
                         root_unchanged=True, pv_legal=True, outer_seconds=0.1))
    return packet, rows


def comparison(packet, rows, before='baseline', after='scan_hint', depth=1):
    contexts, maps = literal_contexts(packet)
    qualified = qualify_returns(rows, 'phase1', contexts, maps)
    meta = {r['id']: r for r in packet['rows']}
    return summarize_comparison(contexts, meta, qualified, before, after, depth, depth)


def test_identical_actions_cancel_without_truth(contract_source):
    packet, rows = contract_source
    result = comparison(packet, rows)
    assert result['counts']['same_action_pairs'] == 1
    assert result['mean_bounds'] == ['0', '0']
    assert result['rows'][0]['action_quality'] == 'UNKNOWN_NO_MATCHING_TRUTH'
    assert analyze(packet, {'phase1': rows})['unlabelled_legal_actions'] >= 2


def test_changed_actions_remain_unknown_even_with_same_search_score(contract_source):
    packet, rows = deepcopy(contract_source)
    rows[1]['decision']['action'] = packet['rows'][0]['legal_actions'][1]
    rows[1]['decision']['principal_variation'] = [rows[1]['decision']['action']]
    result = comparison(packet, rows)
    assert result['counts']['changed_action_pairs'] == 1
    assert result['mean_bounds'] == ['-2', '2']


@pytest.mark.parametrize('status', ['ERROR', 'NOT_RUN', 'INELIGIBLE_RETAINED', 'MISSING'])
def test_failed_slot_is_not_deleted_or_given_a_draw_label(contract_source, status):
    packet, rows = deepcopy(contract_source)
    if status == 'MISSING':
        rows.pop(1)
    else:
        rows[1] = {k: v for k, v in rows[1].items() if k not in ('decision', 'input_fingerprint')}
        rows[1]['status'] = status
    result = comparison(packet, rows)
    assert result['counts']['planned_pairs'] == 1
    assert result['counts']['matched_legal_pairs'] == 0
    assert result['mean_bounds'] == ['-2', '2']
    assert result['rows'][0]['candidate']['action'] is None


def test_incomplete_depth_is_distinct_from_actual_selected_action(contract_source):
    packet, rows = deepcopy(contract_source)
    rows[1]['decision'].update(completed_depth=0, termination_reason='time_limit')
    result = comparison(packet, rows)
    assert result['mean_bounds'] == ['0', '0']
    assert result['completed_depth_mean_bounds'] == ['-2', '2']
    assert result['counts']['completed_pairs'] == 0


def test_nominal_search_limit_is_not_formal_outer_timing_qualification(contract_source):
    packet, rows = deepcopy(contract_source)
    rows[1]['outer_seconds'] = 10.1
    result = comparison(packet, rows)
    assert result['mean_bounds'] == ['0', '0']
    assert result['completed_depth_mean_bounds'] == ['0', '0']
    assert result['nominal_outer_limit_mean_bounds'] == ['-2', '2']
    assert 'descriptive only' in result['rows'][0]['candidate']['timing_scope']


@pytest.mark.parametrize('field,value,match', [
    ('requested_depth', True, 'integer'), ('requested_depth', 2, 'outside'),
    ('arm', 'invented', 'outside'), ('case_id', 'foreign-history', 'outside'),
    ('slot', True, 'slot'), ('slot', 10, 'slot'), ('slot', 1, 'schedule'),
    ('input_fingerprint', 'wrong-rule', 'fingerprint'),
    ('status', 'DRAW', 'status'), ('pv_legal', False, 'qualification'),
    ('root_unchanged', False, 'qualification'),
    ('outer_seconds', -1, 'elapsed'), ('outer_seconds', float('nan'), 'elapsed'),
    ('outer_seconds', float('inf'), 'elapsed'), ('outer_seconds', True, 'elapsed'),
])
def test_corrupt_return_is_rejected(contract_source, field, value, match):
    packet, rows = deepcopy(contract_source)
    rows[0][field] = value
    with pytest.raises(ValueError, match=match):
        comparison(packet, rows)


@pytest.mark.parametrize('field,value,match', [
    ('action', {}, 'legal'), ('choice_kind', 'DECLARATION', 'choice'),
    ('declaration', 'claim', 'choice'), ('principal_variation', [{}], 'PV'),
    ('completed_depth', True, 'depth'), ('completed_depth', 2, 'depth'),
])
def test_corrupt_decision_is_rejected(contract_source, field, value, match):
    packet, rows = deepcopy(contract_source)
    rows[0]['decision'][field] = value
    with pytest.raises(ValueError, match=match):
        comparison(packet, rows)


def test_swapped_rotation_slots_are_not_another_valid_pairing(contract_source):
    packet, rows = deepcopy(contract_source)
    rows[0]['slot'], rows[1]['slot'] = rows[1]['slot'], rows[0]['slot']
    with pytest.raises(ValueError, match='schedule'):
        comparison(packet, rows)


def test_duplicate_slot_or_return_not_silently_collapsed(contract_source):
    packet, rows = deepcopy(contract_source)
    rows.append(deepcopy(rows[0]))
    with pytest.raises(ValueError, match='duplicate'):
        comparison(packet, rows)


@pytest.mark.parametrize('field', ['legal_actions', 'fingerprint', 'prefix_length', 'root', 'terminal'])
def test_corrupt_full_context_is_rejected(contract_source, field):
    packet, _ = deepcopy(contract_source)
    row = packet['rows'][0]
    if field == 'legal_actions':
        row[field] = row[field][:-1]
    elif field == 'fingerprint':
        row[field] = 'wrong'
    elif field == 'prefix_length':
        row[field] += 1
    elif field == 'root':
        row[field]['ply_count'] += 1
    elif field == 'terminal':
        row[field] = True
    with pytest.raises(ValueError):
        literal_contexts(packet)


def test_duplicate_context_id_not_reweighted(contract_source):
    packet, _ = deepcopy(contract_source)
    packet['rows'].append(deepcopy(packet['rows'][0]))
    with pytest.raises(ValueError, match='duplicate source context'):
        literal_contexts(packet)


def test_duplicate_context_with_renamed_id_not_counted_twice(contract_source):
    packet, _ = deepcopy(contract_source)
    row = deepcopy(packet['rows'][0]); row['id'] = 'second-name'
    packet['rows'].append(row)
    with pytest.raises(ValueError, match='duplicate full contexts'):
        literal_contexts(packet)


def test_different_source_manifest_cannot_claim_published_commit(tmp_path):
    (tmp_path/'manifest.json').write_text('{"files": []}', encoding='utf-8')
    with pytest.raises(ValueError, match='fixed published source'):
        load_source(tmp_path)


def test_search_score_changes_cannot_narrow_wdl_bounds(contract_source):
    packet, rows = deepcopy(contract_source)
    rows[0]['decision']['score'] = -999999
    rows[1]['decision']['score'] = 999999
    result = comparison(packet, rows)
    assert result['mean_bounds'] == ['0', '0']
    assert result['rows'][0]['action_quality'] == 'UNKNOWN_NO_MATCHING_TRUTH'

def test_empty_pv_is_no_continuation_not_an_illegal_selected_action(contract_source):
    packet, rows = deepcopy(contract_source)
    rows[1]['decision']['principal_variation'] = []
    result = comparison(packet, rows)
    assert result['mean_bounds'] == ['0', '0']
    assert result['rows'][0]['candidate']['PV_scope'] == 'EMPTY_NO_CONTINUATION_SUPPLIED'
