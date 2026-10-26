"""Existing-record counterexamples for censored path versus episode bounds."""
from copy import deepcopy
from fractions import Fraction
import gzip
import json
from pathlib import Path
import pytest
from scripts.paired_path_bounds import analyze_pair


@pytest.fixture(scope='module')
def controls():
    return json.loads(gzip.decompress(Path('tests/fixtures/paired_path_source_controls.json.gz').read_bytes()))


def run_case(case,ends=None,**kwargs):
    return analyze_pair(case['rule'],case['initial'],*(case['ends']if ends is None else ends),**kwargs)


def cut(record,length):
    result=deepcopy(record);result['actions']=result['actions'][:length];return result


def test_real_complete_pair_has_exact_prefix_and_episode_contrast(controls):
    result=run_case(controls['positive'])
    assert result['actual_Core_terminal_games']==2
    assert result['baseline_minus_candidate_observed_prefix_actor_WDL_regret_bounds']==['1','1']
    assert result['complete_episode_actor_WDL_regret_contrast']=='1'
    assert result['candidate_planned_mean_game_point_completion_bounds']==['3/4','3/4']
    assert result['local_action_WDL_labels_created']==0


def test_shared_ongoing_endpoint_is_zero_prefix_but_unknown_game_score(controls):
    case=controls['positive'];length=len(case['initial']['actions'])+case['common_actions']
    a,b=[cut(end,length)for end in case['ends']];assert a==b
    result=run_case(case,[a,b])
    assert result['same_complete_endpoint_context']is True
    assert result['baseline_minus_candidate_observed_prefix_actor_WDL_regret_bounds']==['0','0']
    assert result['complete_episode_actor_WDL_regret_contrast']is None
    assert result['candidate_planned_mean_game_point_completion_bounds']==['0','1']
    assert all(s['actual_candidate_game_points']is None for s in result['slots'])


def test_no_moves_played_is_not_a_draw_or_completed_pair(controls):
    case=controls['positive'];result=run_case(case,[case['initial'],case['initial']])
    assert result['actual_Core_terminal_games']==0
    assert result['baseline_minus_candidate_observed_prefix_actor_WDL_regret_bounds']==['0','0']
    assert result['candidate_planned_mean_game_point_completion_bounds']==['0','1']
    assert all(s['observed_path_actions']==0 for s in result['slots'])


def test_same_board_and_clock_do_not_merge_actual_different_histories(controls):
    result=run_case(controls['history_alias'])
    a,b=[s['context']for s in result['slots']]
    assert a['position_sha256']==b['position_sha256']and a['ply']==b['ply']==11
    assert a['repetition_counts']!=b['repetition_counts']and a['history_sha256']!=b['history_sha256']
    assert result['same_complete_endpoint_context']is False
    assert result['baseline_minus_candidate_observed_prefix_actor_WDL_regret_bounds']==['-2','2']
    assert result['candidate_planned_mean_game_point_completion_bounds']==['0','1']


def test_one_ply_before_actual_mate_stays_unknown_without_solving(controls):
    case=controls['positive'];a,b=deepcopy(case['ends']);b['actions'].pop()
    result=run_case(case,[a,b])
    assert [s['status']for s in result['slots']]==['TERMINAL','ONGOING']
    assert result['baseline_minus_candidate_observed_prefix_actor_WDL_regret_bounds']==['-1','1']
    assert result['candidate_planned_mean_game_point_completion_bounds']==['1/4','3/4']
    assert result['complete_episode_actor_WDL_regret_contrast']is None


@pytest.mark.parametrize('missing',[0,1])
def test_missing_path_retains_two_planned_slots_without_inventing_prefix(missing,controls):
    case=controls['positive'];ends=deepcopy(case['ends']);ends[missing]=None
    result=run_case(case,ends)
    assert result['planned_games']==2 and result['qualified_observed_paths']==1
    assert result['slots'][missing]['status']=='MISSING_UNOBSERVED_PATH'
    assert result['baseline_minus_candidate_observed_prefix_actor_WDL_regret_bounds']is None
    assert result['slots'][missing]['actual_candidate_game_points']is None
    expected=['1/2','1']if missing==0 else['1/4','3/4']
    assert result['candidate_planned_mean_game_point_completion_bounds']==expected


def test_missing_both_slots_has_no_observed_regret_and_no_half_score(controls):
    result=run_case(controls['positive'],[None,None])
    assert result['qualified_observed_paths']==result['actual_Core_terminal_games']==0
    assert result['candidate_planned_mean_game_point_completion_bounds']==['0','1']
    assert result['baseline_minus_candidate_observed_prefix_actor_WDL_regret_bounds']is None


@pytest.mark.parametrize('fault',['foreign_prefix','shorter','resignation','bad_rule','illegal_action'])
def test_invalid_source_is_not_deleted_or_credited_as_terminal(fault,controls):
    case=controls['positive'];ends=deepcopy(case['ends'])
    if fault=='foreign_prefix':ends[1]=case['alternative_initial']
    elif fault=='shorter':ends[1]=cut(case['initial'],0)
    elif fault=='resignation':
        ends[1]=deepcopy(case['initial']);ends[1]['resigned_by']=0
    elif fault=='bad_rule':ends[1]['ruleset_fingerprint']='not-the-pinned-rule'
    else:ends[1]['actions'][0]['to']=[99,99]
    result=run_case(case,ends)
    assert result['planned_games']==2 and result['qualified_observed_paths']==1
    assert result['slots'][1]['status']=='INVALID_SOURCE'
    assert result['candidate_planned_mean_game_point_completion_bounds']==['1/4','3/4']
    assert result['actual_Core_terminal_games']==1
    assert result['complete_episode_actor_WDL_regret_contrast']is None


def test_swapped_candidate_label_reverses_regret_and_game_score(controls):
    result=run_case(controls['positive'],candidate_seat_a=1)
    assert result['baseline_minus_candidate_observed_prefix_actor_WDL_regret_bounds']==['-1','-1']
    assert result['candidate_planned_mean_game_point_completion_bounds']==['1/4','1/4']


def test_timing_exclusion_preserves_actual_terminal_facts(controls):
    result=run_case(controls['positive'],timing_eligible=(False,True))
    assert result['actual_Core_terminal_games']==2
    assert result['complete_pair_timing_eligible']is False
    assert result['complete_episode_actor_WDL_regret_contrast']=='1'
    assert result['candidate_planned_mean_game_point_completion_bounds']==['3/4','3/4']


@pytest.mark.parametrize('seat',[True,-1,2,'0'])
def test_ambiguous_candidate_seat_cannot_change_attribution(seat,controls):
    with pytest.raises(ValueError,match='seat'):run_case(controls['positive'],candidate_seat_a=seat)


@pytest.mark.parametrize('flags',[(1,True),('false',True),(True,)])
def test_timing_claims_must_not_be_truthy_strings(flags,controls):
    with pytest.raises(ValueError,match='timing'):run_case(controls['positive'],timing_eligible=flags)


def path_case(case,index,weight=1):
    return dict(rule=case['rule'],initial_record=case['initial'],endpoint_record=case['ends'][index],candidate_seat=index,weight=weight)


def test_weighted_complete_paths_cancel_roots_only_at_matched_seat_weights(controls):
    from scripts.paired_path_bounds import observed_regret_sum
    case=controls['positive']
    assert observed_regret_sum([path_case(case,0),path_case(case,1)])['baseline_minus_candidate_experienced_actor_WDL_regret_bounds']==['1','1']
    assert observed_regret_sum([path_case(case,0,2),path_case(case,1)])['baseline_minus_candidate_experienced_actor_WDL_regret_bounds']==['0','2']
    assert observed_regret_sum([path_case(case,0),path_case(case,1,2)])['baseline_minus_candidate_experienced_actor_WDL_regret_bounds']==['1','3']
    assert observed_regret_sum([path_case(case,0,'1/2'),path_case(case,1,'1/2')])['baseline_minus_candidate_experienced_actor_WDL_regret_bounds']==['1/2','1/2']


def test_one_completed_unpaired_draw_keeps_unknown_initial_potential(controls):
    from scripts.paired_path_bounds import observed_regret_sum
    result=observed_regret_sum([path_case(controls['positive'],0)])
    assert result['baseline_minus_candidate_experienced_actor_WDL_regret_bounds']==['-1','1']
    assert any(t['bounds']==[-1,1]for t in result['residual_context_potentials'])


def test_actual_equal_board_different_initial_histories_do_not_cancel(controls):
    from scripts.paired_path_bounds import observed_regret_sum
    case=controls['history_alias']
    paths=[dict(rule=case['rule'],initial_record=case['ends'][i],endpoint_record=case['full_ends'][i],candidate_seat=i)for i in(0,1)]
    result=observed_regret_sum(paths)
    assert result['qualified_paths']==2
    assert result['baseline_minus_candidate_experienced_actor_WDL_regret_bounds']==['-2','2']
    assert sorted(t['coefficient']for t in result['residual_context_potentials']if t['bounds']==[-1,1])==['-1','1']


def test_missing_requested_path_is_not_renormalized_to_valid_subset(controls):
    from scripts.paired_path_bounds import observed_regret_sum
    case=controls['positive'];paths=[path_case(case,0),path_case(case,1)];paths[1]['endpoint_record']=None
    result=observed_regret_sum(paths)
    assert result['requested_paths']==2 and result['qualified_paths']==1
    assert result['baseline_minus_candidate_experienced_actor_WDL_regret_bounds']is None
    assert result['unqualified'][0]['status']=='MISSING_UNOBSERVED_PATH'


@pytest.mark.parametrize('weight',[0,-1,0.5,True])
def test_weighted_target_requires_explicit_exact_positive_weights(weight,controls):
    from scripts.paired_path_bounds import observed_regret_sum
    with pytest.raises(ValueError,match='weights'):observed_regret_sum([path_case(controls['positive'],0,weight)])


def test_real_timing_ineligible_query_is_still_an_actual_forced_zero_regret_move(controls):
    from scripts.leaper_truth_compatibility import bind_context
    from generic_chess.core.actions import action_to_dict
    from scripts.leaper_truth_compatibility import digest
    item=controls['forced_timing_omission'];context=bind_context(item['rule'],item['record'])
    assert item['query_id']==371 and item['policy']=='short'and item['timing_eligible']is False
    assert item['wall_seconds']>item['requested_seconds']+max(.025,.1*item['requested_seconds'])
    assert context.identity['record_sha256']==item['record_before_sha256']
    from scripts.research_record import record_value
    assert len(context.legal_actions)==1 and record_value(context.session.legal_actions()[0])==item['action']
    # No action WDL label is required: a single ordinary choice has regret0.
    # Record reconstruction must nevertheless retain this real move.


def test_verified_forced_link_relates_values_without_merging_history_or_turn(controls):
    from scripts.paired_path_bounds import verify_forced_link
    from scripts.leaper_truth_compatibility import bind_context
    item=controls['forced_timing_omission']
    result=verify_forced_link(item['rule'],item['record'],item['child_record'])
    assert result['status']=='VERIFIED_FORCED_VALUE_EQUALITY'
    assert result['value_seat']==0 and result['acting_regret']==0
    assert result['states_merged']is False and result['numeric_WDL_labels_created']==0
    a=bind_context(item['rule'],item['record']);b=bind_context(item['rule'],item['child_record'])
    assert a.identity['record_sha256']!=b.identity['record_sha256']
    assert a.identity['history_sha256']!=b.identity['history_sha256']and a.identity['ply']+1==b.identity['ply']
    assert a.identity['side_to_move']!=b.identity['side_to_move']
    assert a.legal_actions[0]not in b.legal_actions
    assert a.identity['position_sha256']!=b.identity['position_sha256']


def test_ordinary_selected_move_with_alternatives_is_not_a_forced_equality(controls):
    from scripts.paired_path_bounds import verify_forced_link
    case=controls['positive'];child=cut(case['ends'][0],len(case['initial']['actions'])+1)
    result=verify_forced_link(case['rule'],case['initial'],child)
    assert result==dict(status='NOT_PROVED',reason='MULTIPLE_ORDINARY_CHOICES')


def test_forced_link_cannot_fill_an_unprovided_edge(controls):
    from scripts.paired_path_bounds import verify_forced_link
    item=controls['forced_timing_omission']
    assert verify_forced_link(item['rule'],item['record'],item['record'])['reason']=='ONE_RECORDED_EDGE_REQUIRED'
    assert verify_forced_link(item['rule'],item['record'],None)['status']=='NOT_PROVED'


def test_forced_value_link_rejects_external_resignation(controls):
    from scripts.paired_path_bounds import verify_forced_link
    item=controls['forced_timing_omission'];child=deepcopy(item['child_record']);child['resigned_by']=0
    result=verify_forced_link(item['rule'],item['record'],child)
    assert result['status']=='NOT_PROVED'
    assert 'external Session'in result['error']


@pytest.mark.parametrize('untrusted',[{'terminal_WDL':1,'status':'TERMINAL'},
    {'score':1000000,'completed_depth':96},
    {'Session_result':{'status':'checkmate','winner':0},'principal_variation':[]}])
def test_extra_search_or_outcome_metadata_cannot_label_an_ongoing_record(untrusted,controls):
    case=controls['positive'];record=deepcopy(case['initial']);record.update(untrusted)
    result=run_case(case,[record,record])
    # The strict GameRecord reader may reject extra source fields or ignore
    # semantically irrelevant metadata. Neither path may invent Core WDL.
    assert result['actual_Core_terminal_games']==0
    assert result['complete_episode_actor_WDL_regret_contrast']is None
    assert result['candidate_planned_mean_game_point_completion_bounds']==['0','1']
    assert all(slot['actual_candidate_game_points']is None for slot in result['slots'])
