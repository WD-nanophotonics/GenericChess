"""Replay frozen choices and goal certificates; no new public transitions."""
import hashlib
import json
from fractions import Fraction as F
from pathlib import Path
from types import SimpleNamespace as NS

from generic_chess.core.pieces import Piece
from generic_chess.core.position import Position, Hands
from generic_chess.core.terminal import TerminalResult, TerminalStatus as T
from scripts.native_chess_contact_intervals import contact_interval_choice
from scripts.material_leaf_choice import one_ply_choice, material_score

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'docs/research/data/cutoff_safety_use_20261005.json'


def report():
    return json.loads(RAW.read_text(encoding='utf-8'))


def child(packet):
    p = packet['position']; t = packet['terminal_status']
    position = Position(
        tuple(Piece(**x) if x else None for x in p['board']),
        tuple(Hands(tuple(tuple(x) for x in h['counts'])) for h in p['hands']),
        p['side_to_move'], p['ruleset_fingerprint'],
        tuple((tuple(k), tuple(v) if isinstance(v, list) else v)
              for k, v in p['aux_state']), p['board_width'], p['board_height'])
    return NS(position=position, result=TerminalResult(T[t['status'].split('.')[1]], t['winner']))


def test_frozen_prelabel_snapshot_and_sources():
    r = report(); freeze = RAW.with_suffix('.selections.json')
    assert r['complete'] and 'error' not in r
    assert r['all_selections_frozen_before_goal_expansion']
    assert hashlib.sha256(freeze.read_bytes()).hexdigest() == r['prelabel_freeze_sha256']
    before = json.loads(freeze.read_text(encoding='utf-8'))
    assert set(before) == {'root_state', 'all_children', 'selections_before_labels', 'source_premises'}
    assert all(before[k] == r[k] for k in before)
    assert r['source_hashes_unchanged']
    for path, digest in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest


def test_source_scope_and_global_cost():
    r = report()
    assert len(r['source_premises']) == 7 and all(r['source_premises'].values())
    assert (r['public_transitions'], r['enumerated'], r['complete_choice_count']) == (40, 40, 8)
    assert r['seconds'] < 15 and r['external_source_calls'] == 0
    root = r['root_state']
    assert root['ply_count'] == 998 and len(root['history']) == 1
    assert max(x[1] for x in root['repetition_counts']) == 1
    assert 998 + 2 + 1 < 100000  # Any consistent complete prefix, not this compressed one alone.
    assert all(c['ply_count'] == 999 for c in r['all_children'].values())
    assert r['root_weight'] == '1'


def test_replay_all_complete_choices_without_goal_queries():
    r = report(); children = {k: child(v) for k, v in r['all_children'].items()}
    game = NS(terminal=lambda c: c.result)
    for model in ('geometric_half', 'linear_mixture', 'both'):
        replay = contact_interval_choice(children, game, owner=0, duration=model, complete=True)
        assert replay['complete'] and replay['selected'] == r['selections_before_labels'][model]['selected']
    weights = {('board', t): F(1) for t in ('P', 'N', 'B', 'R', 'Q')}
    unit = one_ply_choice(children, game, lambda c: material_score(c.position, weights, {'K'}, 30), owner=0, complete=True)
    zero = one_ply_choice(children, game, lambda c: F(0), owner=0, complete=True)
    assert unit['selected'] == r['selections_before_labels']['unit']['selected']
    assert zero['selected'] == r['selections_before_labels']['zero']['selected']
    assert unit['selected'] != zero['selected']


def test_saved_complete_goal_values_and_no_strict_improvement():
    r = report(); selected = {v['selected'] for v in r['selections_before_labels'].values()}
    assert set(r['selected_goal_evidence']) == selected
    assert sorted(len(row['replies']) for row in r['selected_goal_evidence'].values()) == [8, 24]
    for row in r['selected_goal_evidence'].values():
        assert row['complete_replies'] and row['child_ply'] == 999
        assert len({v['action_id'] for v in row['replies']}) == len(row['replies'])
        values = []
        for reply in row['replies']:
            leaf = reply['state']; t = leaf['terminal_status']
            assert leaf['ply_count'] == 1000 and t['status'] == 'TerminalStatus.MAX_PLY'
            assert t['winner'] is None and reply['value'] == 0
            values.append(reply['value'])
        assert row['interval'] == [min(values), min(values)] == [0, 0]
    for margins in r['paired_margins'].values():
        assert margins == {'unit': [0, 0], 'zero': [0, 0]}
        assert all(F(v[1]) < F(1, 10) for v in margins.values())
