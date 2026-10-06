"""Verify saved complete forests, not rerun or improve their sampled roots."""
import hashlib
import json
from pathlib import Path
from fractions import Fraction as F
from scripts.audit_chess_adjudicated_exchange import nominal_risk

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'docs/research/data'


def record():
    return json.loads((DATA/'chess_adjudicated_exchange_20261006.json').read_text())


def test_frozen_inputs_including_failed_old_sample():
    r = record()
    assert r['complete'] and r['source_hashes_unchanged']
    for path, digest in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest
    old = json.loads((DATA/'chess_first_quiet_pilot_20261006.json').read_text())
    assert not old['complete'] and old['proposals'] == 128 and old['public_transitions'] == 0


def test_prelabel_contains_all_root_children_but_no_defender_labels():
    r = record(); path = DATA/'chess_adjudicated_exchange_20261006.selections.json'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == r['prelabel_sha256']
    pre = json.loads(path.read_text())
    assert pre['public_transitions'] == pre['author_pushes'] == 6
    assert pre['leaves'] == pre['replies'] == pre['outcomes'] == {}
    assert pre['policies'] == r['policies']
    assert set(pre['children']) == set(r['all_root_actions'])
    assert all(g is None for g in pre['root_source_goals'].values())


def test_complete_source_and_public_event_counts_and_caps():
    r = record()
    assert r['proposals'] == 5 and r['proposal_index'] == 4
    assert r['public_transitions'] == r['author_pushes'] == 29
    assert r['state_checks'] == 30 and r['parent_choice_checks'] == 3
    assert r['enumerated'] == 348 and r['author_legal_entries'] == 29
    assert r['seconds'] < 30 and r['source_table_queries'] == 0
    assert r['nominal_checks'] == 10 and r['nominal_scanned'] == 1
    assert len(r['leaves']) == 27
    for key, reply in r['replies'].items():
        assert len(reply['all_actions']) == len(reply['rows'])
        assert sorted(x['action'] for x in reply['rows']) == sorted(reply['all_actions'])
        assert all(x['path'] == key+'/'+x['action'] and x['path'] in r['leaves'] for x in reply['rows'])
    assert sum(len(x['rows']) for x in r['replies'].values()) == 23


def test_true_automatic_draws_remain_distinct_from_quiet_vectors():
    r = record(); terminals = [x for x in r['leaves'].values() if x['kind'] == 'source_terminal']
    assert len(terminals) == 2
    for leaf in terminals:
        assert leaf['source_terminal']['termination'] == 'INSUFFICIENT_MATERIAL'
        assert leaf['source_terminal']['winner'] is None
        assert leaf['source_terminal']['value'] == 0
        assert leaf['local_terminal'] == {'status': 'ongoing', 'winner': None}
        assert leaf['state']['terminal_status'] == leaf['local_terminal']
        assert leaf['state']['ply_count'] == 2 and len(leaf['state']['history']) == 3
        assert 'vector' not in leaf
    quiet = [x for x in r['leaves'].values() if x['kind'] == 'quiet']
    assert len(quiet) == 25 and all(len(x['vector']) == 5 for x in quiet)
    assert all(row == {'unknown': 'mixed terminal classes'} for row in r['comparisons'].values())


def test_all_ties_and_actual_path_incidence_preserved():
    r = record()
    assert r['policies']['geometric_half']['selected'].endswith('e4-e3')
    assert r['policies']['linear_mixture']['selected'].endswith('e4-e3')
    assert len(r['policies']['unit']['tie_set']) == 2
    assert len(r['policies']['zero']['tie_set']) == 6
    for law, policy in r['policies'].items():
        scores = {k: F(v) for k, v in policy['scores'].items()}
        assert policy['tie_set'] == sorted(k for k, v in scores.items() if v == max(scores.values()))
        assert policy['selected'] == policy['tie_set'][0]
        for kind, keys in [('canonical', [policy['selected']]), ('all_ties', policy['tie_set'])]:
            o = r['outcomes'][law][kind]
            expected = {p for p in r['leaves'] if p.split('/')[0] in keys}
            assert set(o['paths']) == expected == set(o['vectors']) | set(o['terminals'])
            assert not set(o['vectors']) & set(o['terminals'])


def test_nominal_geometry_knight_and_blocked_bishop_controls():
    entries = [(18, 0, 'K'), (27, 1, 'N'), (11, 1, 'B'), (63, 1, 'K'), (37, 0, 'R')]
    assert nominal_risk(entries)[0][1]['nominal_attack']  # d4->f5
    entries[-1] = (38, 0, 'R')
    assert not nominal_risk(entries)[0][1]['nominal_attack']  # d4->g5
    # Bishop d2->h6 is blocked by the nominal K arriving on f4.
    blocked = [(18, 0, 'K'), (29, 1, 'N'), (11, 1, 'B'), (63, 1, 'K'), (47, 0, 'R')]
    assert not nominal_risk(blocked)[0][0]['nominal_attack']
    blocked[1] = (28, 1, 'N')
    assert nominal_risk(blocked)[0][0]['nominal_attack']
