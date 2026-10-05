import hashlib,json
from pathlib import Path
from generic_chess.core.terminal import TerminalStatus as T
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.public_goal_intervals import PublicGame
from scripts.research_state_replay import read_game_state
from scripts.research_record import record_value
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'docs/research/data'

def test_prelabel_order_complete_reply_evidence_and_history_replay():
    p=DATA/'chess_knight_interposition_20261005.selections.json'
    pre=json.loads(p.read_text());r=json.loads((DATA/'chess_knight_interposition_20261005.json').read_text())
    assert hashlib.sha256(p.read_bytes()).hexdigest()==r['prelabel_sha256']
    assert pre['public_transitions']==5 and 'reply_tables' not in pre
    assert len(pre['all_root_actions'])==len(pre['children'])==5
    assert r['complete'] and r['public_transitions']==77 and r['enumerated']==2696
    assert r['selected_exposure']==dict(contact=True,unit=False,zero=False)
    game=PublicGame(compile_ruleset_for_execution(build_western_chess_ruleset()))
    for table in r['reply_tables'].values():
        assert set(table['all_actions'])=={row['action'] for row in table['rows']}
        for row in table['rows']:
            state=read_game_state(row['state'])
            assert state.ply_count==2 and len(state.history)==3
            assert record_value(state)==row['state']
            assert game.terminal(state).status.value==row['terminal']['status']

def test_four_capture_erasure_witnesses_and_worst_floor_optimum():
    r=json.loads((DATA/'chess_promotion_erasure_20261005.json').read_text())
    assert r['complete'] and r['public_transitions']==3 and r['enumerated']==222
    assert {row['mode'] for row in r['rows']}=={'B','N','R'}
    assert all(row['terminal']==dict(status='checkmate',winner=1) for row in r['rows'])
    for value in (-1,0,1):
        branches={k:(value if k==r['weakly_optimal'] else -1) for k in r['full_root_branch_intervals']}
        optimum=max(branches.values());assert optimum==branches[r['weakly_optimal']]
        assert 0<=optimum+1<=2
    assert r['decision_regret']==dict(contact=[0,2],unit=[0,0],zero=[0,0])

def test_frozen_inputs_and_failed_premise_not_recast_as_observation():
    for name in ('chess_promotion_imported_children','chess_knight_interposition','chess_promotion_erasure'):
        r=json.loads((DATA/f'{name}_20261005.json').read_text())
        for name,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==pin
        assert r['source_queries']==0
    failed=json.loads((DATA/'chess_promotion_imported_children_20261005.json').read_text())
    assert not failed['complete'] and failed['public_transitions']==failed['enumerated']==0
    assert 'unsafe' in failed['error']
    assert not (DATA/'chess_promotion_mate_falsifier_20261005.selections.json').exists()
