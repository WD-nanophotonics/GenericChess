import hashlib, json
from fractions import Fraction as F
from pathlib import Path
from scripts.research_state_replay import read_game_state
from scripts.research_record import record_value
from scripts.material_leaf_choice import inventory_features
from scripts.public_goal_intervals import PublicGame
from scripts.resource_mode_context import resource_ledger
from scripts.shogi_board_hand_gap import board_hand_gap
from scripts.shogi_complete_board_intervals import coupled_gap,board_intervals
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/research/data'
def load(name):return json.loads((DATA/f'{name}_20261005.json').read_text())
def delta(before,after):
    a=inventory_features(before.position,{'K'});b=inventory_features(after.position,{'K'})
    return {k:b.get(k,0)-a.get(k,0) for k in a.keys()|b.keys() if b.get(k,0)!=a.get(k,0)}

def test_exact_custody_demotion_drop_deltas_and_preserved_histories():
    r=load('shogi_capture_drop_resume');failed=load('shogi_capture_drop_coupling')
    assert not failed['complete'] and failed['public_transitions']==0 and failed['enumerated']==4
    assert r['complete'] and r['public_transitions']==12 and r['enumerated']==4792
    c=compile_ruleset_for_execution(build_standard_shogi_ruleset());g=PublicGame(c)
    for row in r['rows']:
        state=read_game_state(row['root']);sign=-1 if row['victim_owner']==0 else 1
        expected=({('board',row['victim_current']):sign,('hand','P'):sign},{},{('board','P'):sign,('hand','P'):-sign})
        for i,step in enumerate(row['steps']):
            after=read_game_state(step['state']);d=delta(state,after)
            assert d==expected[i] and record_value(d)==step['delta']
            assert step['action'] in step['all_actions']
            assert after.ply_count==i+1 and len(after.history)==i+2
            assert after.history[:-1]==state.history
            assert not g.terminal(after).is_terminal
            resource_ledger(c,after.position,'shogi')
            assert all(key[1]!='TP' for key in inventory_features(after.position,{'K'}) if key[0]=='hand')
            state=after
    for owner in (0,1):
        rows=[row for row in r['rows'] if row['victim_owner']==owner]
        for i in range(3):
            a,b=(read_game_state(row['steps'][i]['state']) for row in rows)
            assert a.position==b.position and a.history!=b.history

def test_constraints_keep_current_base_split_and_both_laws_without_prices():
    r=load('shogi_capture_drop_resume')
    for law in ('geometric_half','linear_mixture'):
        native=board_hand_gap(law,normalized=True)['P']['lower']
        assert F(r['drop_gap'][law])==native>0
        scale=board_intervals(law,third=True)['TR'][0]
        promoted_extra=coupled_gap(law,'TP','P')/scale
        assert promoted_extra>0 and native+promoted_extra>native

def test_frozen_admission_and_custody_reports_preserve_inputs_without_replay():
    for name in ('contact_depth2_source_admission','shogi_capture_drop_coupling','shogi_capture_drop_resume'):
        r=load(name)
        assert r['source_queries']==0 and r['source_hashes_unchanged']
        for name,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==pin
    r=load('contact_depth2_source_admission')
    assert r['complete'] and r['public_transitions']==0
    assert [row['board_tokens'] for row in r['rows']]==[6,6,7,6]
    assert not any(row['encoding_admitted'] or row['installed_material_domain'] for row in r['rows'])
