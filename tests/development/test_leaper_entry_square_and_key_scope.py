"""Guard typed entry-square, range/quantity and actual-key proof scope."""
from pathlib import Path
from copy import deepcopy
import pytest
from scripts.verify_leaper_delayed_capture import load
from scripts.leaper_entry_square import qualify as square_qualify
from scripts.leaper_support_quantity_boundary import qualify as quantity_qualify
from scripts.leaper_history_order_key import qualify as key_qualify

BASE=Path(__file__).resolve().parents[2]/'docs/research/data'
DATA=BASE/'leaper_support_and_delayed_win_20261024'
OLD=BASE/'leaper_delayed_capture_20261024'


def test_duplicate_range_control_does_not_cover_the_rejected_ray_case():
    m=load(DATA/'support-general.json.gz');m['Core_controls'][-1]=deepcopy(m['Core_controls'][1])
    with pytest.raises(AssertionError):quantity_qualify(m)


def test_two_actor_quantity_census_cannot_be_relabelled_three():
    m=load(DATA/'support-general.json.gz');m['quantity']['WhiteAs']=3
    with pytest.raises(AssertionError):quantity_qualify(m)


def test_square_planned_move_counter_cannot_be_replaced_by_zero():
    reg=load(DATA/'entry-square-registration.json');m=load(DATA/'entry-square.json.gz');m['new_Core_child_applications']=0
    with pytest.raises(AssertionError):square_qualify(reg,m)


def test_square_common_root_complete_frontier_and_distinct_observables():
    reg=load(DATA/'entry-square-registration.json');m=load(DATA/'entry-square.json.gz');q=square_qualify(reg,m)
    assert q['root_branches']==[8,10,9,11]and q['immediate_mating_action_counts']==[0,1,2,5]
    assert q['full_root_WDL']==['UNKNOWN','WIN','WIN','WIN']


def test_square_cannot_drop_a_nonwinning_white_choice():
    reg=load(DATA/'entry-square-registration.json');m=load(DATA/'entry-square.json.gz');m['rows'][0]['children'].pop()
    with pytest.raises(AssertionError,match='complete White'):square_qualify(reg,m)


def test_actual_runtime_order_context_differs_when_counts_are_equal():
    reg=load(DATA/'history-order-key-registration.json.gz');m=load(DATA/'history-order-key.json.gz');q=key_qualify(reg,m,OLD)
    obs=q['actual_observations'];assert obs['fallback_equal']and obs['repetition_snapshot_equal']
    assert not obs['runtime_keys_equal']and not obs['ordered_history_context_equal']
    assert obs['history_witness_misses']==[0,0]and obs['TT_probes_performed']==0


def test_runtime_observation_cannot_be_changed_to_a_key_equality_claim():
    reg=load(DATA/'history-order-key-registration.json.gz');m=load(DATA/'history-order-key.json.gz');m['observations']['runtime_keys_equal']=True
    with pytest.raises(AssertionError):key_qualify(reg,m,OLD)
