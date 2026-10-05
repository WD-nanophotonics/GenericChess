import hashlib,json
from fractions import Fraction as F
from pathlib import Path
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.public_goal_intervals import PublicGame
from scripts.shogi_checked_ongoing_contact import checked_ongoing_choice,SCOPE
from scripts.shogi_exact_twenty_family import exact_twenty_intervals
ROOT=Path(__file__).resolve().parents[1]
def test_explicit_saved_complete_table_preserves_all_ties_and_strict_scope():
    r=json.loads((ROOT/'docs/research/data/shogi_checked_ongoing_approximation_20261005.json').read_text())
    assert r['complete'] and not r['old_strict']['complete'] and not r['unrequested']['complete']
    for law,row in r['explicit_approximate']['by_law'].items():
        assert row['complete'] and row['selected'].endswith('P@a1')
        assert len(row['features'])==69 and len(row['checked_ongoing_choices'])==1
        assert row['common_denominator']==39 and len(row['margins'])==68
        assert sum(m==['0','0'] for m in row['margins'].values())==62
        weights=exact_twenty_intervals(law)
        # Returned margins are raw; the stated common denominator is applied by a consumer.
        gap=weights['board','P'][0]-weights['hand','P'][0]
        assert gap>0 and all(F(m[0])==gap for m in row['margins'].values() if m!=['0','0'])
    assert r['public_transitions']==r['source_queries']==r['enumerated']==0
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin

def test_cached_terminal_cannot_override_fresh_history_qualification():
    r=json.loads((ROOT/'docs/research/data/shogi_checked_ongoing_approximation_20261005.json').read_text())
    assert not r['stale_control']['complete']
    assert all('stale cached terminal' in x['reason'] for x in r['stale_control']['by_law'].values())

def test_opt_in_and_complete_game_state_are_mandatory():
    game=PublicGame(compile_ruleset_for_execution(build_standard_shogi_ruleset()))
    assert not checked_ongoing_choice({'x':object()},game,owner=0,duration='geometric_half',complete=True)['complete']
    result=checked_ongoing_choice({'x':object()},game,owner=0,duration='geometric_half',complete=True,approximation_scope=SCOPE)
    assert not result['complete'] and 'full public GameState' in result['reason']
