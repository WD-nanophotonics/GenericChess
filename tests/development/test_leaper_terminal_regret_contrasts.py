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

def test_wdl_policy_sums_game_points_and_regret_units_are_distinct(actual_premises):
    units=contrast(actual_premises)['payoff_units']
    all_rows=units['all_source']
    means=all_rows.pop('experienced_mean_regret')
    assert means['short_minus_long_mean_WDL_regret_outer_bounds']==['94/466095','1/483']
    assert all_rows==dict(games=24,color_pairs=12,
        long_terminal_WDL_sum=2,short_terminal_WDL_sum=-2,
        long_minus_short_terminal_WDL_sums=4,
        long_game_points='13',short_game_points='11',
        long_minus_short_game_points='2',
        short_minus_long_total_actor_WDL_regret=2,
        short_minus_long_total_actor_gamepoint_regret='1')
    eligible=units['timing_eligible_pairs']
    assert (eligible['games'],eligible['color_pairs'])==(22,11)
    assert (eligible['long_game_points'],eligible['short_game_points'])==('12','10')
    assert eligible['short_minus_long_total_actor_gamepoint_regret']=='1'


def test_policy_renaming_reverses_regret_sign_without_changing_source_outcomes(actual_premises):
    data=deepcopy(actual_premises)
    for game in data['games']:game['long_seat']=1-game['long_seat']
    for q in data['qualified_queries']:q['policy']='long'if q['policy']=='short'else'short'
    result=contrast(data)
    assert result['short_minus_long_total_actor_regret']==-2
    positives=[r for r in result['rows']if r['absolute_outcome_difference']]
    assert all(r['excess_regret_policy']=='long'for r in positives)
    assert sorted(r['candidate_count']for r in positives)==[52,67]
    units=result['payoff_units']['all_source']
    assert (units['long_game_points'],units['short_game_points'])==('11','13')
    assert units['short_minus_long_total_actor_gamepoint_regret']=='-1'


def test_each_reported_candidate_survives_observed_edge_only_regret_constraints():
    # A potential completion is NOT a minimax solution of the real RuleSet.
    # It tests the exact weakness of endpoint + observed-edge + forced-choice
    # reasoning. Unobserved defenses can invalidate any such completion.
    path=Path('docs/research/data/aux_saved_decisions_20261026/game-exposure.json.gz')
    source=json.loads(gzip.decompress(path.read_bytes()))
    queries=source['queries']
    positive=[r for r in source['terminal_outcome_contrasts']['rows']
              if r['short_minus_long_total_actor_regret']>0]
    checked=0
    for row in positive:
        by_game={gid:sorted((q for q in queries if q['game_id']==gid),key=lambda q:q['ply'])
                 for gid in row['game_ids']}
        game_a,game_b=row['game_ids']
        assert row['terminal_values_fixed_seat0']==[0,-1]
        candidates=set(row['excess_policy_nonforced_suffix_candidates'])
        for candidate in candidates:
            candidate_query=next(q for q in queries if q['query_id']==candidate)
            # Error in drawn A: start at -1, short(seat1) raises it to0.
            # Error in decisive B: start at0, short(seat0) lowers it to-1.
            start=-1 if candidate_query['game_id']==game_a else 0
            regrets={'short':0,'long':0};errors=[];state_potentials={}
            for gid,expected in ((game_a,0),(game_b,-1)):
                value=start
                for query in by_game[gid]:
                    key=(query['rule_fingerprint'],query['state_sha256'])
                    assert state_potentials.setdefault(key,value)==value
                    following=value
                    if query['query_id']==candidate:
                        assert query['policy']=='short'and not query['forced_action']
                        following+=1 if query['actor']==1 else -1
                    regret=(value-following)if query['actor']==0 else(following-value)
                    assert 0<=regret<=2 and following in (-1,0,1)
                    assert not query['forced_action']or regret==0
                    regrets[query['policy']]+=regret
                    if regret:errors.append(query['query_id'])
                    value=following
                assert value==expected
            assert errors==[candidate] and regrets=={'short':1,'long':0}
            checked+=1
    assert checked==119
    assert all(q['minimax_value']=='UNLABELLED'for q in queries)


def test_positive_total_regret_gap_alone_does_not_order_per_decision_means():
    from fractions import Fraction
    from scripts.audit_published_leaper_exposure import _experienced_regret_mean_bounds
    # Algebraic control only: these are not new games or a new RuleSet.
    result=_experienced_regret_mean_bounds(4,1,4,1,1)
    lo,hi=map(Fraction,result['short_minus_long_mean_WDL_regret_outer_bounds'])
    assert (lo,hi)==(Fraction(-5,4),Fraction(1,4))
    # Independently enumerate feasible integer TOTALS, not game-tree values.
    actual=[Fraction(s,4)-l for s in range(9)for l in range(3)if s-l==1]
    assert (min(actual),max(actual))==(lo,hi)


def test_source_mean_bounds_preserve_all_moves_and_reverse_under_policy_renaming(actual_premises):
    from fractions import Fraction
    result=contrast(actual_premises)['payoff_units']['all_source']['experienced_mean_regret']
    assert (result['short_observed_moves'],result['long_observed_moves'])==(966,965)
    assert (result['short_nonforced_moves'],result['long_nonforced_moves'])==(872,912)
    assert result['feasible_long_total_regret_outer_bounds']==[0,1742]
    assert Fraction(result['short_minus_long_mean_WDL_regret_outer_bounds'][0])>0
    data=deepcopy(actual_premises)
    for game in data['games']:game['long_seat']=1-game['long_seat']
    for q in data['qualified_queries']:q['policy']='long'if q['policy']=='short'else'short'
    reverse=contrast(data)['payoff_units']['all_source']['experienced_mean_regret']
    lo,hi=map(Fraction,result['short_minus_long_mean_WDL_regret_outer_bounds'])
    assert list(map(Fraction,reverse['short_minus_long_mean_WDL_regret_outer_bounds']))==[-hi,-lo]


def test_mean_regret_outer_bounds_against_all_small_aggregate_completions():
    from fractions import Fraction
    from scripts.audit_published_leaper_exposure import _experienced_regret_mean_bounds
    # Exhaust finite integer TOTALS independently, not any game or WDL tree.
    for ns in range(1,5):
        for nl in range(1,5):
            for fs in range(ns+1):
                for fl in range(nl+1):
                    for margin in range(-2*nl,2*ns+1):
                        possible=[Fraction(s,ns)-Fraction(l,nl)
                                  for s in range(2*fs+1)for l in range(2*fl+1)if s-l==margin]
                        if not possible:
                            with pytest.raises(ValueError,match='capacity'):
                                _experienced_regret_mean_bounds(ns,nl,fs,fl,margin)
                        else:
                            result=_experienced_regret_mean_bounds(ns,nl,fs,fl,margin)
                            assert list(map(Fraction,result['short_minus_long_mean_WDL_regret_outer_bounds']))==[min(possible),max(possible)]
