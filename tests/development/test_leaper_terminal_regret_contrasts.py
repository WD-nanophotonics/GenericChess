"""Regret-contrast premises: scope/sign/history controls, never a WDL solver."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import pytest
from scripts.audit_published_leaper_exposure import terminal_outcome_contrasts


@pytest.fixture(scope='module')
def actual_premises():
    return json.loads(gzip.decompress(Path('tests/fixtures/published_leaper_contrast_premises.json.gz').read_bytes()))


def contrast(data):
    return terminal_outcome_contrasts(data['games'],data['prefix_rows'],data['qualified_queries'])


def test_actual_source_outcome_margin_is_policy_regret_contrast_not_labels(actual_premises):
    result=contrast(actual_premises)
    assert result['planned_color_pairs']==12
    assert result['timing_eligible_color_pairs']==11
    assert result['differing_outcome_pairs']==2
    assert result['short_minus_long_total_actor_regret']==2
    assert result['timing_eligible_short_minus_long_total_actor_regret']==2
    assert result['source_action_WDL_labels_created']==0
    selected=[r for r in result['rows']if r['excess_regret_policy']=='short']
    assert {r['case_id']:r['candidate_count']for r in selected}=={'n5-f4-h2':52,'n6-f4-h2':67}
    assert all(r['root_WDL']=='UNKNOWN'and r['local_action_labels']==0 for r in result['rows'])
    assert all(r['excess_regret_policy_nonoptimal_decisions_lower_bound']==1 for r in selected)


def test_game_list_order_does_not_flip_policy_attribution(actual_premises):
    data=deepcopy(actual_premises);data['games'].reverse()
    assert contrast(data)==contrast(actual_premises)


def test_wrong_initial_history_cannot_cancel_unknown_root_value(actual_premises):
    data=deepcopy(actual_premises);data['games'][1]['initial_record']['extra']='different-record'
    with pytest.raises(ValueError,match='initial full contexts'):contrast(data)


def test_wrong_rule_cannot_cancel_unknown_root_value(actual_premises):
    data=deepcopy(actual_premises);data['games'][1]['fingerprint']='another-rule'
    with pytest.raises(ValueError,match='initial full contexts'):contrast(data)


@pytest.mark.parametrize('field,value', [('status','no_contest'),('status','ongoing'),('winner',True)])
def test_unusable_terminal_is_not_draw_imputed(actual_premises,field,value):
    data=deepcopy(actual_premises)
    for key in ('Core_terminal','Session_result'):data['games'][0][key][field]=value
    with pytest.raises(ValueError):contrast(data)


def test_session_resignation_is_not_rule_checkmate(actual_premises):
    data=deepcopy(actual_premises);data['games'][0]['Session_result']['resigned_by']=0
    with pytest.raises(ValueError,match='external Session'):contrast(data)


def test_without_policy_color_swap_no_regret_attribution(actual_premises):
    data=deepcopy(actual_premises);data['games'][1]['long_seat']=0
    with pytest.raises(ValueError,match='swapped policy'):contrast(data)


def test_a_forged_prefix_cannot_exclude_first_divergent_decisions(actual_premises):
    data=deepcopy(actual_premises);data['prefix_rows'][0]['common_actual_move_prefix']+=1
    with pytest.raises(ValueError,match='prefix'):contrast(data)


def test_no_narrow_candidate_set_from_unverified_forced_flags(actual_premises):
    data=deepcopy(actual_premises)
    for query in data['qualified_queries']:query['forced_action']=True
    with pytest.raises(ValueError,match='non-forced'):contrast(data)


def test_equal_draws_leave_absolute_regrets_unidentified(actual_premises):
    result=contrast(actual_premises)
    zeros=[r for r in result['rows']if r['short_minus_long_total_actor_regret']==0]
    assert len(zeros)==10
    assert all(r['conclusion']=='NO_POSITIVE_LOWER_BOUND'for r in zeros)
    assert all(r['excess_regret_policy']=='NONE_IDENTIFIED'for r in zeros)
    # Equality is total short-minus-long regret=0, NOT absolute total regret=0.
    assert all(r['local_action_labels']==0 and r['root_WDL']=='UNKNOWN'for r in zeros)