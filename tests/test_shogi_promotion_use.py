import hashlib,json
from pathlib import Path
from fractions import Fraction as F
from scripts.audit_shogi_promotion_use import margin,minimizer,selections
from scripts.audit_shogi_promotion_goal_exclusion import projected_own_actions,coordinate_attacked,coordinate_escape
from scripts.research_state_replay import read_game_state
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'docs/research/data'
def test_shared_hand_parameters_cancel_and_minimax_does_not_sample_them():
    assert margin((F(3,4),{'R':1}),(F(1,4),{'R':1}))==(F(1,2),F(1,2))
    assert margin((F(1),{'P':-1}),(F(0),{'R':1}))==(F(-1),F(1))
    key,value=minimizer({'survive':{('board','P'):1,('board','R'):-1},'captured':{('board','R'):-1,('hand','P'):-1}},{'P':F(1,4),'R':F(3,4)})
    assert key=='captured' and value==(F(-3,4),{'P':-1})
def test_actual_full_tree_ties_and_prelabel_order():
    r=json.loads((DATA/'shogi_promotion_use_20261005.json').read_text())
    assert r['complete'] and r['public_transitions']==48 and r['enumerated']==557 and len(r['branches'])==5
    assert sum(len(x['leaves']) for x in r['branches'].values())==43
    for branch in r['branches'].values():assert set(branch['all_enemy_actions'])==set(branch['leaves'])
    choices=r['selections_before_goal']
    assert all(choices[law]['tie_set']==['legacy_029:g21:a7-a8=TP'] for law in ('geometric_half','linear_mixture'))
    assert choices['unit']['tie_set']==['legacy_029:g21:a7-a8','legacy_029:g21:a7-a8=TP'] and len(choices['zero']['tie_set'])==5
    assert r['goal_over_budget'] and not r['goal_width_exhausted'] and r['full_ply3_public_events_lower_bound']==135
    assert hashlib.sha256((DATA/'shogi_promotion_use_20261005.selections.json').read_bytes()).hexdigest()==r['prelabel_sha256']
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
def test_full_drop_superset_escape_certificate_and_unknown_eventual_goal():
    r=json.loads((DATA/'shogi_promotion_goal_exclusion_20261005.json').read_text());raw=json.loads((DATA/'shogi_promotion_use_20261005.json').read_text())
    assert r['complete'] and len(r['rows'])==12 and len(r['quiet_counterreplies'])==3
    assert r['projected_actions']==r['virtual_escape_positions']==r['compiled_attack_checks']==1023
    assert r['conservative_enumeration_charge']==1580 and r['new_public_transitions']==0 and r['cumulative_seconds']<15
    assert set(r['window_values'].values())=={0} and all(x==[-1,1] for x in r['eventual_goal_intervals'].values())
    for row in r['rows']:
        state=read_game_state(raw['branches'][row['root_action']]['leaves'][row['enemy_reply']]['state'])
        projections=list(projected_own_actions(state.position.board));assert len(projections)==len(row['witnesses'])
        assert sum(a['family']=='drop' for a,b in projections)==78
        for (action,board),witness in zip(projections,row['witnesses']):
            assert action==witness['action'];dest,escaped=coordinate_escape(board)
            assert dest==witness['king_escape'] and not coordinate_attacked(escaped,dest)
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin

def test_advisor_forced_pawn_result_and_native_drop_custody():
    raw=json.loads((DATA/'shogi_promotion_use_20261005.json').read_text())
    cert=json.loads((DATA/'shogi_promotion_goal_exclusion_20261005.json').read_text())
    forced=0;drops=0
    for row in cert['rows']:
        state=read_game_state(raw['branches'][row['root_action']]['leaves'][row['enemy_reply']]['state'])
        for action,board in projected_own_actions(state.position.board):
            piece=board[action['target']]
            if action['family']=='drop':
                assert (piece.owner,piece.base_type_id,piece.current_type_id,piece.promoted)==(0,'R','R',False)
                drops+=1
            if action['source']==63 and action['target']==72 and not row['root_action'].endswith('=TP'):
                assert action['result']=='TP'
                assert (piece.owner,piece.base_type_id,piece.current_type_id,piece.promoted)==(0,'P','TP',True)
                forced+=1
    assert forced==7 and drops==936
