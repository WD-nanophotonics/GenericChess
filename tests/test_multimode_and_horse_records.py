import hashlib
import json
from pathlib import Path
from fractions import Fraction as F
import pytest
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'docs/research/data'


@pytest.mark.parametrize('name', ['chess_multimode_response', 'chess_multimode_source_replay',
                                 'horse_target_graph', 'horse_zero_obstruction', 'shared_parameter_order',
                                 'chess_multimode_static2', 'chess_retention_information',
                                 'diagnostic_duration_order', 'diagnostic_duration_tail',
                                 'population_duration_scope'])
def test_complete_frozen_reports_and_all_input_hashes(name):
    r = json.loads((DATA/f'{name}_20261006.json').read_text())
    assert r['complete'] and r['source_hashes_unchanged']
    for path, digest in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest, path


def test_prelabel_frozen_before_complete_response_labels_and_full_ties():
    r = json.loads((DATA/'chess_multimode_response_20261006.json').read_text())
    pre = DATA/'chess_multimode_response_20261006.selections.json'
    assert hashlib.sha256(pre.read_bytes()).hexdigest() == r['prelabel_sha256']
    p = json.loads(pre.read_text())
    assert not p['goal_intervals'] and 'replies' not in p
    assert set(r['all_root_actions']) == set(r['children']) == set(r['goal_intervals'])
    assert sum(len(v['rows']) for v in r['replies'].values()) == 87
    for reply in r['replies'].values():
        assert sorted(row['action'] for row in reply['rows']) == sorted(reply['all_actions'])
    assert r['public_transitions'] == 90 and r['enumerated'] == 2764
    assert all(v['window'] == [0, 0] and v['eventual'] == [-1, 1] for v in r['goal_intervals'].values())
    assert len(r['selections_before_labels']['unit']['tie_set']) == 2
    assert len(r['selections_before_labels']['zero']['tie_set']) == 3
    for row in r['comparisons'].values():
        assert row['window']['canonical_margin'] == ['0', '0']
        assert row['window']['tie_margin'] == ['0', '0']
        assert row['eventual']['verdict'] == 'inconclusive'


def test_independent_source_scope_exact_and_no_extra_core_expansion():
    r = json.loads((DATA/'chess_multimode_source_replay_20261006.json').read_text())
    assert r['author_pushes'] == 90 and r['state_checks'] == 91 and r['parent_choice_checks'] == 4
    assert r['public_transitions'] == r['source_table_queries'] == 0
    assert len(r['records']) == 87 and all(x['window'] == 0 and x['independent_terminal'] is None for x in r['records'])


def test_horse_two_step_parity_and_independent_zero_lower_not_full_reachability():
    r = json.loads((DATA/'horse_target_graph_20261006.json').read_text())
    z = json.loads((DATA/'horse_zero_obstruction_20261006.json').read_text())
    assert sum(row['worlds'] for row in r['rows']) == 840
    assert r['forward_nodes'] == 1579 and r['motifs'] == 3216
    assert all(x['exact'] == 0 and x['target_free'] == 5 for x in r['controls'])
    a = r['full_analytic_prefix']
    assert a['second'] == 668*88+332*87+708*85 == 147848
    assert a['direct'] == 508*87
    assert z['known_zero_lower'] == 352+48 == 400
    assert not z['complement_reachability_proved']
    assert z['cumulative_terms'] == 3732 < 5000
    for old, new in zip(r['moments'], z['moments']):
        assert new['horse_interval'][0] == old['horse_interval'][0]
        assert F(new['horse_interval'][1]) < F(old['horse_interval'][1])
        assert all(old['above'][x] for x in ('C', 'S', 'E', 'A'))


def test_cutoff_consumer_keeps_goal_and_production_scope_unproved():
    r = json.loads((DATA/'shared_parameter_order_20261006.json').read_text())
    assert len(r['rows']) == 4 and r['vertices'] == 224
    assert all(row['value_cutoff_proved'] and row['canonical_action_prune_proved'] for row in r['rows'])
    assert all(F(row['denominator_range'][0]) > 0 for row in r['rows'])
    assert r['public_transitions'] == r['runtime_pushes'] == 0
    assert 'production' in r['not_proved'] and 'goal' in r['not_proved']


def test_static_depth_two_preserves_all_actions_and_does_not_create_goal_gain():
    r = json.loads((DATA/'chess_multimode_static2_20261006.json').read_text())
    original = json.loads((DATA/'chess_multimode_response_20261006.json').read_text())
    assert r['leaf_rows'] == 87 and r['vertices'] == 160
    assert r['public_transitions'] == r['runtime_pushes'] == r['source_queries'] == 0
    assert r['window_gain_unchanged']
    for key, branch in r['branches'].items():
        assert set(branch['action_to_row']) == set(original['replies'][key]['all_actions'])
        assert all(0 <= i < len(branch['unique_rows']) for i in branch['action_to_row'].values())
    for law, score in [('geometric_half', F(-3117,1395248)),
                       ('linear_mixture', F(-126257,30523220))]:
        assert r['endpoints'][law]['tie_set'] == [r['candidate']]
        assert F(r['endpoints'][law]['score']) == score
    assert len(r['endpoints']['unit']['tie_set']) == 2
    assert F(r['endpoints']['unit']['score']) == F(-1,31)
    assert len(r['endpoints']['zero']['tie_set']) == 3
    assert all(F(p['normalized_lower']) > 0 for p in r['proofs'])


def test_retention_uses_real_joint_replies_and_keeps_tie_and_goal_limits():
    r = json.loads((DATA/'chess_retention_information_20261006.json').read_text())
    raw = json.loads((DATA/'chess_multimode_response_20261006.json').read_text())
    assert r['rows'] == 87 and r['window_gain_unchanged']
    assert r['public_transitions'] == r['source_queries'] == 0
    for key,b in r['branches'].items():
        assert set(b['action_vectors']) == set(raw['replies'][key]['all_actions'])
        assert F(b['hidden']) == F(1,2)
        assert b['marginal_vector_is_actual'] == (b['marginal_minimum'] in b['action_vectors'].values())
    for law in ('geometric_half','linear_mixture'):
        assert r['comparisons'][law]['hidden']['tie_margin'] == ['0','0']
        assert r['comparisons'][law]['revealed']['tie_margin'] == ['0','1/2']


def test_first_quiet_failed_admission_is_not_a_successful_labelled_run():
    r = json.loads((DATA/'chess_first_quiet_pilot_20261006.json').read_text())
    assert not r['complete'] and r['source_hashes_unchanged']
    assert r['proposals'] == 128 and r['public_transitions'] == r['source_queries'] == 0
    assert sum(r['rejection_counts'].values()) == 128
    assert not r['nodes'] and not r['leaves'] and not r['outcomes']
    assert not (DATA/'chess_first_quiet_pilot_20261006.selections.json').exists()
    for path,pin in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == pin


def test_universal_duration_order_keeps_partial_horse_and_actual_crossings():
    r = json.loads((DATA/'diagnostic_duration_order_20261006.json').read_text())
    c = r['cumulative']
    assert r['comparisons'] == 270 and r['histogram_terms'] == 31
    assert r['rook_all_duration_normalizer']
    assert c['H']['3'] == [192044,704480] == c['H']['infinity']
    assert r['pairs']['H/R']['reverse_min_gap'] == 400
    assert not r['pairs']['H/S']['forward_proved']
    assert r['pairs']['C/E']['definitely_a_below'] == ['1']
    assert r['pairs']['C/S']['definitely_a_above'] == ['2','3','4']
    assert c['S']['1'][0] > c['C']['1'][0]
    assert c['C']['2'][0] > c['S']['2'][0]
    assert c['S']['5'][0] > c['C']['5'][0]
    for mode, table in c.items():
        if mode == 'R':continue
        # Every extreme duration atom satisfies the asserted linear-law bound.
        delta = min(c['R'][n][0]-interval[1] for n,interval in table.items())
        assert delta > 0
        for n,interval in table.items():
            assert c['R'][n][0]-interval[1] >= delta


def test_tail_gates_against_independent_duration_atoms_and_unknown_horse_tail():
    r = json.loads((DATA/'diagnostic_duration_tail_20261006.json').read_text())
    c = json.loads((DATA/'diagnostic_duration_order_20261006.json').read_text())['cumulative']
    assert r['terms'] == 34
    hs = r['horse_soldier'];ce = r['cannon_elephant']
    assert F(hs['strict_m8_over_m1_below']) == F(7911,52529)
    # All extreme atoms validate the grouped bound, including the possible
    # interval-model H lower distribution, rather than the unqualified full H.
    for n in range(1,18):
        actual_hs=c['H'][str(n)][0]-c['S'][str(n)][1]
        assert actual_hs >= (hs['early_minimum'] if n<=7 else -hs['tail_adverse'])
        actual_ce=c['C'][str(n)][0]-c['E'][str(n)][1]
        assert actual_ce >= (-ce['first_adverse'] if n==1 else ce['later_minimum'])
    # Boundary distribution on horizon7/infinity exactly cancels the *bound*.
    q=F(7911,52529);p=1-q
    assert p*hs['early_minimum']-q*hs['tail_adverse'] == 0
    x=F(5348,6215)
    assert -x*ce['first_adverse']+(1-x)*ce['later_minimum'] == 0
    for control in r['controls'].values():
        assert F(control['hs_lower'])>0 and F(control['ce_lower'])>0


def test_population_scope_does_not_generalize_uniform_cdf_to_correlated_duration():
    r = json.loads((DATA/'population_duration_scope_20261006.json').read_text())
    assert r['world_queries'] == 2 and r['arithmetic_terms'] == 92
    counter = r['counterexample']
    assert counter['distances'] == {'A':1,'R':2}
    assert not counter['compiled_per_world_reproduced'] and not counter['official_goal_claim']
    assert F(counter['uniform_dependent_duration']['A']) > F(counter['uniform_dependent_duration']['R'])
    assert F(r['universal_tv_gates']['H']['strict_epsilon_below']) == F(5,17622)
    assert all(x['not_necessary'] for x in r['universal_tv_gates'].values())
