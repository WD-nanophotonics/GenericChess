"""Guard actual history contrast and complete paired capture conformance."""
from pathlib import Path
from copy import deepcopy
import pytest
from generic_chess.session.session import SessionRecordError
from scripts.verify_leaper_delayed_capture import load
from scripts.leaper_history_value_witness import qualify as history_qualify
from scripts.leaper_capture_epoch_conformance import qualify as epoch_qualify

BASE=Path(__file__).resolve().parents[2]/'docs/research/data'
DATA=BASE/'leaper_support_and_delayed_win_20261024'
OLD=BASE/'leaper_delayed_capture_20261024'


def history_packet():return load(DATA/'history-positive-registration.json.gz'),load(DATA/'history-positive.json.gz')
def epoch_packet():return load(DATA/'capture-epoch-registration.json.gz'),load(DATA/'capture-epoch.json.gz')


def test_same_position_clock_actual_history_changes_value_in_one_fixed_rule():
    reg,m=history_packet();q=history_qualify(reg,m,OLD)
    assert q['White_WDL']==[0,1]and q['same_ply']==4 and q['mate_ply']==7
    assert q['terminal_status']==['repetition','ongoing']


def test_history_win_is_not_just_one_unchallenged_principal_variation():
    reg,m=history_packet();m['all_defenses']=[]
    with pytest.raises(AssertionError,match='complete defense'):history_qualify(reg,m,OLD)


def test_same_position_does_not_allow_transplanting_another_prefix():
    reg,m=history_packet();m['rows'][1]['trace'][-1]['record']['actions']=deepcopy(m['rows'][0]['trace'][-1]['record']['actions'])
    with pytest.raises(SessionRecordError,match='illegal action'):history_qualify(reg,m,OLD)


def test_capture_epoch_retains_all_actual_history_and_matches_complete_future():
    reg,m=epoch_packet();q=epoch_qualify(reg,m,OLD)
    assert q['pair_nodes']==28 and q['pair_edges']==27
    assert q['terminal_pair_counts']=={'checkmate':4,'stalemate':4,'max_ply':9}
    assert q['initial_full_history_tables_differ']and q['projected_current_inventory_tables_equal']


def test_one_missing_paired_successor_is_not_full_conformance():
    reg,m=epoch_packet();m['tape'][0]['children']=[]
    with pytest.raises(AssertionError,match='complete paired frontier'):epoch_qualify(reg,m,OLD)


def test_capture_to_hand_cannot_enter_the_remove_only_scope():
    reg,m=epoch_packet();reg['rule']['capture_disposition']='capture_to_hand'
    with pytest.raises(AssertionError,match='capture-epoch scope'):epoch_qualify(reg,m,OLD)


def test_projected_context_never_overwrites_core_repetition_counts():
    reg,m=epoch_packet();node=m['tape'][0]['pair'][0]
    current=node['state']['history'][-1]['position_key']
    node['state']['repetition_counts']=[x for x in node['state']['repetition_counts']if x[0]==current]
    with pytest.raises(AssertionError):epoch_qualify(reg,m,OLD)
