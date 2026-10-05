import hashlib,json
from pathlib import Path
from scripts.research_state_replay import read_game_state
from scripts.research_record import record_value
from scripts.public_goal_intervals import PublicGame
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'docs/research/data'

def test_saved_partial_continuation_and_mate_countertrees():
    old=json.loads((DATA/'chess_pinned_queen_mate_20261005.json').read_text())
    new=json.loads((DATA/'chess_pinned_queen_continuation_20261005.json').read_text())
    prepath=DATA/'chess_pinned_queen_mate_20261005.selections.json';pre=json.loads(prepath.read_text())
    assert not old['complete'] and old['public_transitions']==22
    assert new['complete'] and new['public_transitions']==12
    assert old['enumerated']+new['enumerated']==622
    assert hashlib.sha256(prepath.read_bytes()).hexdigest()==old['prelabel_sha256']
    assert len(pre['children'])==len(pre['all_root_actions'])==21
    assert old['candidate_all_replies']==['sem_00_k_quiet:g11:d8-c7']
    assert new['candidate_mate']['action'] in old['candidate_replies'][0]['all_own_replies']
    game=PublicGame(compile_ruleset_for_execution(build_western_chess_ruleset()))
    mate=read_game_state(new['candidate_mate']['state'])
    assert mate.ply_count==3 and len(mate.history)==4
    assert game.terminal(mate).status.value=='checkmate' and game.terminal(mate).winner==0
    for branch in new['baseline_counterbranches'].values():
        assert set(branch['all_own_replies'])=={row['action'] for row in branch['own_rows']}
        for row in branch['own_rows']:
            state=read_game_state(row['state']);assert state.ply_count==3 and len(state.history)==4
            t=game.terminal(state);assert not (t.status.value=='checkmate' and t.winner==0)
            assert record_value(state)==row['state']

def test_unit_and_zero_ties_include_the_winning_candidate():
    r=json.loads((DATA/'chess_pinned_queen_mate_20261005.selections.json').read_text())
    picks=r['selections_before_labels'];candidate=picks['contact']['selected']
    from fractions import Fraction as F
    for name in ('unit','zero'):
        scores={k:F(v) for k,v in picks[name]['scores'].items()}
        assert scores[candidate]==max(scores.values())
        assert picks[name]['selected']!=candidate

def test_frozen_phases_preserve_sources():
    for name in ('chess_pinned_queen_mate','chess_pinned_queen_continuation'):
        r=json.loads((DATA/f'{name}_20261005.json').read_text())
        assert r['source_queries']==0
        for name,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==pin
