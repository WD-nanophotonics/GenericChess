import json,hashlib
from pathlib import Path
import pytest
from fractions import Fraction as F
from scripts.native_chess_contact_intervals import native_contact_intervals
from scripts.third_native_contact_intervals import third_native_contact_intervals,third_contact_choice
from scripts.research_state_replay import read_game_state
from scripts.public_goal_intervals import PublicGame
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'docs/research/data'

@pytest.mark.parametrize('law',['geometric_half','linear_mixture'])
def test_only_pawn_changes_and_bounds_remain_nested(law):
    old=native_contact_intervals(law);new=third_native_contact_intervals(law)
    assert set(old)==set(new)
    assert all(old[k]==new[k] for k in old if k!=('board','P'))
    assert old['board','P'][0]<new['board','P'][0]<new['board','P'][1]<old['board','P'][1]

def test_label_free_gain_and_old_certificates_never_reverse():
    r=json.loads((DATA/'pawn_third_certificate_gain_20261005.json').read_text())
    assert r['complete'] and len(r['rows'])==452 and r['table_evaluations']==1808
    assert (r['old_union_certified'],r['new_union_certified'],r['union_gain'])==(424,430,6)
    assert r['unchanged_exposed_mate_risk'] and r['physical_events']==r['goal_queries']==0
    for row in r['rows']:
        for choice in row['by_law'].values():assert choice['old'] is None or choice['old']==choice['new']
    for name,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==pin

def test_full_saved_child_contract_and_exposed_failure_are_preserved():
    pre=json.loads((DATA/'chess_knight_interposition_20261005.selections.json').read_text())
    children={k:read_game_state(v) for k,v in pre['children'].items()};game=PublicGame(compile_ruleset_for_execution(build_western_chess_ruleset()))
    assert not third_contact_choice(children,game,owner=0,duration='both')['complete']
    r=third_contact_choice(children,game,owner=0,duration='both',complete=True)
    assert r['selected']==pre['selections_before_labels']['contact']['selected']
    with pytest.raises(ValueError):third_native_contact_intervals('both')
