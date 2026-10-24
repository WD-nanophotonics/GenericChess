"""Guard the named proof, complete-rule admission and the failed history claim."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import gzip,json
import pytest
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import qualify,verify_measurements,theorem_scope
from scripts.leaper_history_structural_witness import assess,qualify_loss_prediction,verify

DATA=Path(__file__).resolve().parents[2]/'docs/research/data/leaper_delayed_capture_20261024'

def load(name):
    return json.loads(gzip.decompress((DATA/name).read_bytes()))


def test_shared_ongoing_move_revalues_and_clock_hides_it():
    r=qualify(load('delayed.json.gz'))
    assert r['candidate_shared_action_WDL_black']==[1,0]
    assert r['both_shared_children_ongoing']
    assert {(x['mask'],x['H']):x['white_WDL'] for x in r['clocks']}=={(6,1):0,(6,2):-1,(22,1):0,(22,2):0}
    assert r['scoring']['payoff_changes']==[]
    assert r['scoring']['root_WDL'].startswith('UNKNOWN')


def test_no_mate_draw_argument_rejects_unproved_rule_policies():
    m=load('delayed.json.gz')
    r=L.ruleset_from_dict(m['candidate'][1]['rule'])
    assert theorem_scope(r,22)
    assert not theorem_scope(replace(r,pass_enabled=True),22)
    assert not theorem_scope(replace(r,capture_disposition='capture_to_hand'),22)
    bad=deepcopy(m)
    bad['candidate'][1]['rule']=L.ruleset_to_dict(replace(r,pass_enabled=True),include_metadata=True)
    with pytest.raises(AssertionError,match='outside proved rule scope'):
        qualify(bad)


def test_full_record_reader_rejects_retained_state_without_actual_prefix():
    m=load('delayed.json.gz')
    bad=deepcopy(m)
    bad['candidate'][0]['shared_king']['child']['record']['actions']=[]
    with pytest.raises(AssertionError,match='literal stored'):
        verify_measurements(bad)


def test_actual_repetition_refutes_the_fresh_loss_certificate_transplant():
    m=load('history.json.gz')
    # Original preregistered loss claim still FAILS; no fit-to-output rewrite.
    with pytest.raises(StopIteration):
        qualify_loss_prediction(m)
    r=assess(m)
    assert r['prediction_status']=='REFUTED'
    assert r['predicted_white_WDL']==[0,-1]
    assert r['proven_white_WDL']==[0,0]
    assert r['different_target_terminal_status']==['repetition','ongoing']
    assert verify(m)['unique_full_records']==18

def test_remnant_proof_rejects_an_extra_live_attacking_piece():
    m=load('delayed.json.gz')
    r=L.ruleset_from_dict(m['candidate'][1]['rule'])
    board=[list(row)for row in r.initial_position]
    board[2][2]=L.Piece(1,'A','A')
    extra=replace(r,initial_position=tuple(tuple(row)for row in board))
    assert not theorem_scope(extra,22)


def test_no_entry_proof_requires_every_royal_and_ordinary_inverse_atom():
    from scripts.leaper_mate_entry_witness import qualify as qualify_entry
    m=load('mate-entry.json.gz')
    del m['n3_mate_rows'][0]['inverse_candidates'][-1]
    with pytest.raises(AssertionError,match='inverse'):
        qualify_entry(m)


def test_corpus_rule_admission_rejects_new_effects_and_wrong_defender():
    from scripts.verify_leaper_delayed_capture import compile_scoped
    raw=load('corner-law.json.gz')['fresh_witnesses'][1]['rule']
    r=L.ruleset_from_dict(raw)
    compile_scoped(raw,5,22,5)
    with pytest.raises(AssertionError,match='complete rule scope'):
        compile_scoped(L.ruleset_to_dict(replace(r,pass_enabled=True)),5,22,5)
    with pytest.raises(AssertionError,match='complete rule scope'):
        compile_scoped(raw,5,22,27)


def test_public_reader_binds_all_proofs_without_executing_source_capsules():
    from scripts.verify_leaper_delayed_capture import qualify as public_qualify
    q=public_qualify(DATA)
    assert q['source_capsule_executions']==q['new_Player_queries']==q['new_graph_or_solver_calls']==0
    assert q['entry']['n3_admissible_last_move_predecessors']==0
    assert q['corner']['added_static_capacity_B_masks']==[5,7,21,23]
    assert [r['mu_count']for r in q['mu']['summary']]==[360,12500,130316]

def test_channel_summary_cannot_omit_a_measured_mating_action():
    from scripts.leaper_entry_channels import qualify as qualify_channels
    m=load('entry-channels.json.gz')
    named={(5,8,3,0),(2,7,0,3)}
    row=next(r for r in m['rows']if tuple(r['placement'])not in named and r['immediate_mating_actions'])
    row['immediate_mating_actions'].pop()
    with pytest.raises(AssertionError,match='complete'):
        qualify_channels(m)


def test_new_illegal_old_action_never_receives_an_old_game_record():
    from scripts.leaper_entry_channels import qualify as qualify_channels
    m=load('entry-channels.json.gz')
    row=next(r for r in m['rows']if tuple(r['placement'])==(2,7,0,3))
    w=next(w for w in row['immediate_mating_actions']if w['category']=='new_entry_into_old_static_mate')
    w['old_shared_child']=row['pair'][1]['branches'][0]['child']
    with pytest.raises(AssertionError,match='illegal'):
        qualify_channels(m)


def test_named_mu_counts_default_once_and_rejects_old_fingerprint_record():
    from scripts.leaper_named_mu_bridge import qualify as qualify_named
    from generic_chess.session.session import SessionRecordError
    reg=load('named-mu-registration.json.gz');m=load('named-mu-bridge.json.gz');parent=load('entry-channels.json.gz')
    q=qualify_named(reg,m,parent)
    assert q['mu_size']==152 and q['named_setup_options_per_rule']==151
    assert q['actual_repetition_cycle_records']==4
    c=L.compile_rule(L.ruleset_from_dict(reg['fixed_rules']['22']))
    old_record=parent['rows'][0]['pair'][0]['root']['record']
    with pytest.raises(SessionRecordError,match='fingerprint'):
        L.GameSession.replay(c,L.deserialize_game_record(json.dumps(old_record)))
    bad=deepcopy(reg);bad['mu']['keys'][1]=None
    with pytest.raises(AssertionError):qualify_named(bad,m,parent)


def test_geometric_orbits_are_not_independent_replicates_or_player_equivalence():
    from scripts.leaper_entry_channels import symmetry_analysis
    m=load('entry-channels.json.gz');q=symmetry_analysis(m)
    assert q['geometric_D4_orbits']==19 and q['immediate_mate_orbits']==14
    assert q['child_board_terminal_transform_checks']==11072
    bad=deepcopy(m);bad['rows'][0]['pair'][1]['branches'][0]['child']['result']['winner']=1
    with pytest.raises(AssertionError):symmetry_analysis(bad)


def test_capture_certificate_is_bound_to_the_actual_white_prefix():
    from scripts.leaper_entry_channels import qualify_obstruction
    m=load('negative-obstruction.json.gz');parent=load('entry-channels.json.gz');named=load('named-mu-bridge.json.gz')
    q=qualify_obstruction(m,parent,named)
    assert q['certified_NOT_White_WIN']==24 and q['unresolved_roots']==16
    assert q['complete_mu_WIN_count_interval']==[112,128]
    captures=[c for r in m['roots']for c in r['clauses']if c['kind']=='verified_captureA']
    captures[0]['capture_after']=deepcopy(captures[-1]['capture_after'])
    with pytest.raises(AssertionError,match='prefix'):
        qualify_obstruction(m,parent,named)


def test_local_not_win_proof_cannot_drop_a_white_choice():
    from scripts.leaper_entry_channels import qualify_obstruction
    m=load('negative-obstruction.json.gz');m['roots'][0]['clauses'].pop()
    with pytest.raises(AssertionError):
        qualify_obstruction(m,load('entry-channels.json.gz'),load('named-mu-bridge.json.gz'))
