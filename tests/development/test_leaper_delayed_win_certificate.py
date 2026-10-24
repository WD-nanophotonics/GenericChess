"""Guard an all-defense delayed-WIN proof, not just a principal variation."""
from copy import deepcopy
from pathlib import Path
import pytest
from generic_chess.session.session import SessionRecordError
from scripts.verify_leaper_delayed_capture import load
from scripts.leaper_delayed_win_certificate import qualify

BASE=Path(__file__).resolve().parents[2]/'docs/research/data'
DATA=BASE/'leaper_support_and_delayed_win_20261024'
OLD=BASE/'leaper_delayed_capture_20261024'


def packet():
    return load(DATA/'existence-registration.json.gz'),load(DATA/'existence-completed.json.gz')


def test_delayed_win_has_no_immediate_mate_and_covers_every_black_reply():
    reg,m=packet();q=qualify(reg,m,OLD)
    assert not q['root_has_immediate_win']
    assert [(r['H'],r['White_WDL'])for r in q['finite_strategy_WDL']]==[(6,1),(1,0),(2,0),(3,1)]
    assert q['newly_labeled_H6_roots']==1 and q['unique_full_records']==33


def test_a_missing_defense_cannot_make_the_certificate_vacuously_true():
    reg,m=packet();m['rows'][0]['all_black_defenses']=[]
    with pytest.raises(AssertionError,match='complete Black'):
        qualify(reg,m,OLD)


def test_non_immediate_claim_requires_all_white_first_choices():
    reg,m=packet();m['rows'][0]['all_white_first'].pop()
    with pytest.raises(AssertionError,match='complete White'):
        qualify(reg,m,OLD)


def test_clock_fingerprint_and_actual_prefix_cannot_be_transplanted():
    reg,m=packet();m['rows'][0]['all_black_defenses'][0]['finish']=deepcopy(m['rows'][3]['all_black_defenses'][0]['finish'])
    with pytest.raises(SessionRecordError,match='fingerprint'):
        qualify(reg,m,OLD)


def test_actual_partial_enum_failure_stays_invalid():
    reg=load(DATA/'existence-registration.json.gz');m=load(DATA/'existence-partial-original.json.gz')
    with pytest.raises(AssertionError,match='finish prefix'):
        qualify(reg,m,OLD)


def test_new_rule_policies_do_not_enter_through_a_clock_control():
    reg,m=packet();reg['complete_rules']['3']['pass_enabled']=True
    with pytest.raises(AssertionError,match='complete rule/clock'):
        qualify(reg,m,OLD)
